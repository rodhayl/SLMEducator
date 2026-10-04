from fastapi import APIRouter, Depends, HTTPException
from src.core.services.temporal_service import (
    utc_now,
    known_instant,
    timestamp_provenance,
    local_date,
    record_goal_day,
)

from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.api.policies import require_content, require_plan
from src.core.services.content_schema import normalize_content, learner_content
from src.core.services.learning_context import content_revision
from src.core.services.course_workflow import workflow
from src.api.routes.gamification import award_activity_xp
from src.core.models import (
    User,
    LearningSession,
    SessionStatus,
    Content,
    DailyGoal,
    ContentType,
    StudyPlanContent,
)

router = APIRouter(prefix="/api/learning", tags=["learning"])

# --- Pydantic Models ---


class SessionStart(BaseModel):
    content_id: int
    study_plan_id: Optional[int] = None


class SessionUpdate(BaseModel):
    notes: Optional[str] = None
    # Legacy field name: self-rated confidence, 1=very low through 5=very high.
    difficulty_rating: Optional[int] = Field(default=None, ge=1, le=5)


class NotesUpdate(BaseModel):
    """Update notes during an active session"""

    notes: str


class SessionResponse(BaseModel):
    id: int
    content_id: int
    start_time: datetime
    status: str
    duration_minutes: Optional[int]
    notes: Optional[str]
    timestamp_provenance: str = "legacy_unknown"
    duration_known: bool = False
    content_snapshot: Optional[dict] = None
    context_revision: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---


@router.post("/start", response_model=SessionResponse)
async def start_session(
    data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new learning session"""
    content = require_content(db, current_user, data.content_id)
    plan = (
        require_plan(db, current_user, data.study_plan_id)
        if data.study_plan_id
        else None
    )
    if (
        plan
        and content.study_plan_id != plan.id
        and not db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan.id, content_id=content.id)
        .first()
    ):
        raise HTTPException(
            status_code=409,
            detail="The selected content does not belong to this course",
        )
    _lock_sessions(db, current_user.id)
    existing = _active_for_content(
        db, current_user.id, data.content_id, data.study_plan_id
    )
    if existing:
        db.commit()
        return _session_response(existing)

    session = LearningSession(
        student_id=current_user.id,
        content_id=data.content_id,
        status=SessionStatus.ACTIVE,
        start_time=utc_now(),
    )
    _capture_revision(db, session, content, plan)
    db.add(session)
    db.commit()
    db.refresh(session)

    return _session_response(session)


def _capture_revision(db, session, content, plan) -> None:
    """Capture one canonical instructional revision for every new session path."""
    try:
        visible = learner_content(
            content.content_type.value,
            normalize_content(
                content.content_type.value, content.decrypted_content_data or {}
            ),
        )
        session.set_content_snapshot(
            {
                "id": content.id,
                "title": content.title,
                "content_type": content.content_type.value,
                "content_data": visible,
            }
        )
        session.context_revision = {
            "content_digest": content_revision(content),
            "study_plan_id": plan.id if plan else None,
            "course_version": workflow(plan).get("version") if plan else None,
            "plan_context": (
                {
                    "id": plan.id,
                    "title": plan.title,
                    "description": (plan.description or "")[:500],
                }
                if plan
                else None
            ),
            "captured_at": utc_now().isoformat(),
            "provenance": "captured_at_start",
        }
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{session_id}/heartbeat")
async def session_heartbeat(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update active session timestamp (keep-alive)"""
    session = (
        db.query(LearningSession)
        .filter(
            LearningSession.id == session_id,
            LearningSession.student_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    require_content(db, current_user, session.content_id)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    # In a real app, we might update a 'last_active' field.
    # Here, we just acknowledge.
    return {"status": "alive"}


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: int,
    data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete and reward an activity atomically, returning persisted retries."""
    session = (
        db.query(LearningSession)
        .filter_by(id=session_id, student_id=current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    require_content(db, current_user, session.content_id)
    if session.status == SessionStatus.COMPLETED:
        return _session_response(session)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Session is not active")
    now = utc_now()
    claimed = (
        db.query(LearningSession)
        .filter(
            LearningSession.id == session_id,
            LearningSession.status == SessionStatus.ACTIVE,
        )
        .update(
            {
                LearningSession.status: SessionStatus.COMPLETED,
                LearningSession.end_time: now,
            },
            synchronize_session=False,
        )
    )
    db.refresh(session)
    if not claimed:
        db.rollback()
        return _session_response(session)
    if data.notes is not None:
        session.notes = data.notes
    session.duration_minutes = session.calculate_duration()
    first_completion = session.completion_status not in {
        "rewarded",
        "previously_completed",
    }
    if first_completion:
        award_activity_xp(db, current_user.id, 50)
        _update_daily_goal(db, current_user.id, session)
        if data.difficulty_rating is not None:
            _record_self_confidence(
                db, current_user.id, session.content_id, data.difficulty_rating
            )
        session.completion_status = "rewarded"
    # Self-confidence is stored separately from assessed mastery.
    db.commit()
    return _session_response(session)


def _session_response(session: LearningSession) -> SessionResponse:
    """Serialize preserved history with explicit timestamp provenance."""
    known = known_instant(session.start_time)
    captured = session.decrypted_content_snapshot
    if session.content_snapshot and captured is None:
        raise HTTPException(
            status_code=409,
            detail="Captured session content cannot be decrypted; restore this revision instead of substituting current content",
        )
    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=(
            session.calculate_duration() if session.end_time else (0 if known else None)
        ),
        notes=session.notes,
        timestamp_provenance=timestamp_provenance(session.start_time),
        duration_known=known
        and (session.end_time is None or known_instant(session.end_time)),
        content_snapshot=captured,
        context_revision=session.context_revision or {"provenance": "legacy_unpinned"},
    )


def _lock_sessions(db: Session, user_id: int) -> None:
    """Serialize session creation/restoration on all supported SQL backends."""
    db.query(User).filter_by(id=user_id).update(
        {User.xp: User.xp}, synchronize_session=False
    )


def _active_for_content(
    db: Session, user_id: int, content_id: int, study_plan_id: Optional[int] = None
):
    """Return the server-authoritative open session for this learner/content."""
    candidates = (
        db.query(LearningSession)
        .filter_by(
            student_id=user_id,
            content_id=content_id,
            status=SessionStatus.ACTIVE,
        )
        .order_by(LearningSession.id.desc())
        .all()
    )
    return next(
        (
            session
            for session in candidates
            if (session.context_revision or {}).get("study_plan_id") == study_plan_id
        ),
        None,
    )


def _record_self_confidence(
    db: Session, user_id: int, content_id: int, rating: int
) -> None:
    """Keep self-report separate from mastery based on checked answers."""
    user = db.get(User, user_id)
    settings = dict(user.settings or {})
    confidence = dict(settings.get("self_confidence", {}))
    confidence[str(content_id)] = {
        "rating": rating,
        "recorded_at": utc_now().isoformat(),
    }
    settings["self_confidence"] = confidence
    user.settings = settings


def _update_daily_goal(db: Session, user_id: int, session: LearningSession) -> None:
    """Advance an existing daily goal in the completion transaction."""
    goal = (
        db.query(DailyGoal)
        .filter_by(user_id=user_id, goal_date=local_date(db.get(User, user_id)))
        .first()
    )
    if not goal or goal.completed:
        return
    content = db.get(Content, session.content_id)
    increment = 0
    if goal.goal_type == "lessons" and content.content_type == ContentType.LESSON:
        increment = 1
    elif goal.goal_type == "exercises" and content.content_type == ContentType.EXERCISE:
        increment = 1
    elif goal.goal_type == "time":
        increment = session.duration_minutes or 0
    if increment:
        record_goal_day(db.get(User, user_id), goal)
    goal.current_value += increment
    goal.completed = goal.current_value >= goal.target_value


@router.get("/active", response_model=Optional[SessionResponse])
async def get_active_session(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current active session if any"""
    session = (
        db.query(LearningSession)
        .filter(
            LearningSession.student_id == current_user.id,
            LearningSession.status == SessionStatus.ACTIVE,
        )
        .order_by(LearningSession.id.desc())
        .first()
    )

    if not session:
        return None

    require_content(db, current_user, session.content_id)

    return _session_response(session)


@router.patch("/{session_id}/notes", response_model=SessionResponse)
async def update_session_notes(
    session_id: int,
    data: NotesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update notes during an active session.

    Allows real-time sync of notes to server (in addition to localStorage).
    """
    session = (
        db.query(LearningSession)
        .filter(
            LearningSession.id == session_id,
            LearningSession.student_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    require_content(db, current_user, session.content_id)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=409, detail="Restore the session before changing notes"
        )

    session.notes = data.notes
    db.commit()
    db.refresh(session)

    return _session_response(session)


@router.get("/history/{content_id}", response_model=List[SessionResponse])
async def get_session_history(
    content_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get session history for a specific content item.

    Returns past sessions for this user and content, ordered by most recent.
    """
    require_content(db, current_user, content_id)
    sessions = (
        db.query(LearningSession)
        .filter(
            LearningSession.content_id == content_id,
            LearningSession.student_id == current_user.id,
        )
        .order_by(LearningSession.id.desc())
        .limit(limit)
        .all()
    )

    return [_session_response(session) for session in sessions]


@router.post("/{session_id}/restore", response_model=SessionResponse)
async def restore_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restore a previous session.

    Reactivates a completed/paused session, allowing the user to continue
    with their previous notes preserved.
    """
    session = (
        db.query(LearningSession)
        .filter(
            LearningSession.id == session_id,
            LearningSession.student_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    require_content(db, current_user, session.content_id)
    _lock_sessions(db, current_user.id)
    db.refresh(session)
    if session.status == SessionStatus.ACTIVE:
        db.commit()
        return _session_response(session)
    existing = _active_for_content(
        db,
        current_user.id,
        session.content_id,
        (session.context_revision or {}).get("study_plan_id"),
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Another session for this content is active"
        )
    if (
        session.status == SessionStatus.COMPLETED
        and session.completion_status != "rewarded"
    ):
        session.completion_status = "previously_completed"
    session.status = SessionStatus.ACTIVE
    session.end_time = None
    db.commit()
    db.refresh(session)

    return _session_response(session)


@router.post("/restart/{content_id}", response_model=SessionResponse)
async def restart_session(
    content_id: int,
    study_plan_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a fresh session for content.

    Creates a new session, marking any active sessions for this content as completed.
    Previous session data is preserved in history but not carried over.
    """
    content = require_content(db, current_user, content_id)
    plan = require_plan(db, current_user, study_plan_id) if study_plan_id else None
    if (
        plan
        and content.study_plan_id != plan.id
        and not db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan.id, content_id=content.id)
        .first()
    ):
        raise HTTPException(
            status_code=409,
            detail="The selected content does not belong to this course",
        )
    _lock_sessions(db, current_user.id)
    existing = _active_for_content(db, current_user.id, content_id, study_plan_id)
    if existing and not existing.notes and existing.completion_status == "restarted":
        db.commit()
        return _session_response(existing)

    # End any active sessions for this content
    active_sessions = (
        db.query(LearningSession)
        .filter(
            LearningSession.content_id == content_id,
            LearningSession.student_id == current_user.id,
            LearningSession.status == SessionStatus.ACTIVE,
        )
        .all()
    )

    for active in active_sessions:
        if (active.context_revision or {}).get("study_plan_id") != study_plan_id:
            continue
        active.status = SessionStatus.CLOSED
        active.end_time = utc_now()
        active.duration_minutes = active.calculate_duration()

    # Create new session
    new_session = LearningSession(
        student_id=current_user.id,
        content_id=content_id,
        status=SessionStatus.ACTIVE,
        completion_status="restarted",
        start_time=utc_now(),
    )
    _capture_revision(db, new_session, content, plan)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return _session_response(new_session)
