from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.api.policies import require_content
from src.api.routes.gamification import award_activity_xp
from src.core.models import (
    User,
    LearningSession,
    SessionStatus,
    Content,
    DailyGoal,
    ContentType,
    MasteryNode,
)

router = APIRouter(prefix="/api/learning", tags=["learning"])

# --- Pydantic Models ---


class SessionStart(BaseModel):
    content_id: int


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

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---


@router.post("/start", response_model=SessionResponse)
async def start_session(
    data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new learning session"""
    require_content(db, current_user, data.content_id)
    _lock_sessions(db, current_user.id)
    existing = _active_for_content(db, current_user.id, data.content_id)
    if existing:
        db.commit()
        return _session_response(existing)

    session = LearningSession(
        student_id=current_user.id,
        content_id=data.content_id,
        status=SessionStatus.ACTIVE,
        start_time=datetime.now(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=0,
        notes=None,
    )


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
    session = db.query(LearningSession).filter_by(id=session_id, student_id=current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    require_content(db, current_user, session.content_id)
    if session.status == SessionStatus.COMPLETED:
        return _session_response(session)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Session is not active")
    now = datetime.now()
    claimed = db.query(LearningSession).filter(
        LearningSession.id == session_id, LearningSession.status == SessionStatus.ACTIVE,
    ).update({LearningSession.status: SessionStatus.COMPLETED, LearningSession.end_time: now}, synchronize_session=False)
    db.refresh(session)
    if not claimed:
        db.rollback()
        return _session_response(session)
    if data.notes is not None:
        session.notes = data.notes
    session.duration_minutes = max(0, session.calculate_duration() or 0)
    first_completion = session.completion_status not in {"rewarded", "previously_completed"}
    if first_completion:
        award_activity_xp(db, current_user.id, 50)
        _update_daily_goal(db, current_user.id, session)
        if data.difficulty_rating is not None:
            _schedule_self_rated_review(db, current_user.id, session.content_id, data.difficulty_rating)
        session.completion_status = "rewarded"
    # This is a self-rating heuristic, never evidence of demonstrated mastery.
    db.commit()
    return _session_response(session)


def _session_response(session: LearningSession) -> SessionResponse:
    """Serialize the server's preserved notes and lifecycle."""
    return SessionResponse(
        id=session.id, content_id=session.content_id, start_time=session.start_time,
        status=session.status.value, duration_minutes=session.duration_minutes or 0,
        notes=session.notes,
    )


def _lock_sessions(db: Session, user_id: int) -> None:
    """Serialize session creation/restoration on all supported SQL backends."""
    db.query(User).filter_by(id=user_id).update({User.xp: User.xp}, synchronize_session=False)


def _active_for_content(db: Session, user_id: int, content_id: int):
    """Return the server-authoritative open session for this learner/content."""
    return db.query(LearningSession).filter_by(
        student_id=user_id, content_id=content_id, status=SessionStatus.ACTIVE,
    ).order_by(LearningSession.id.desc()).first()


def _schedule_self_rated_review(db: Session, user_id: int, content_id: int, rating: int) -> None:
    """Update the legacy review heuristic once per completed learning session."""
    from src.core.services.spaced_repetition_service import SpacedRepetitionService

    performance = (rating - 1) * 25
    node = db.query(MasteryNode).filter_by(student_id=user_id, content_id=content_id).first()
    if node is None:
        node = MasteryNode(student_id=user_id, content_id=content_id, mastery_level=performance, review_count=1)
        db.add(node)
    else:
        node.mastery_level = int(0.7 * performance + 0.3 * (node.mastery_level or 0))
        node.review_count = (node.review_count or 0) + 1
    node.last_reviewed = datetime.now()
    node.next_review_due = SpacedRepetitionService.calculate_next_review(
        None, node.mastery_level, node.review_count, performance
    )


def _update_daily_goal(db: Session, user_id: int, session: LearningSession) -> None:
    """Advance an existing daily goal in the completion transaction."""
    goal = db.query(DailyGoal).filter_by(user_id=user_id, goal_date=date.today()).first()
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
        .order_by(LearningSession.start_time.desc())
        .first()
    )

    if not session:
        return None

    require_content(db, current_user, session.content_id)

    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=session.calculate_duration(),
        notes=session.notes,
    )


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
        raise HTTPException(status_code=409, detail="Restore the session before changing notes")

    session.notes = data.notes
    db.commit()
    db.refresh(session)

    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=session.calculate_duration(),
        notes=session.notes,
    )


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
        .order_by(LearningSession.start_time.desc())
        .limit(limit)
        .all()
    )

    return [
        SessionResponse(
            id=s.id,
            content_id=s.content_id,
            start_time=s.start_time,
            status=s.status.value,
            duration_minutes=s.calculate_duration(),
            notes=s.notes,
        )
        for s in sessions
    ]


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
    existing = _active_for_content(db, current_user.id, session.content_id)
    if existing:
        raise HTTPException(status_code=409, detail="Another session for this content is active")
    if session.status == SessionStatus.COMPLETED and session.completion_status != "rewarded":
        session.completion_status = "previously_completed"
    session.status = SessionStatus.ACTIVE
    session.end_time = None
    db.commit()
    db.refresh(session)

    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=session.calculate_duration(),
        notes=session.notes,
    )


@router.post("/restart/{content_id}", response_model=SessionResponse)
async def restart_session(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a fresh session for content.

    Creates a new session, marking any active sessions for this content as completed.
    Previous session data is preserved in history but not carried over.
    """
    require_content(db, current_user, content_id)
    _lock_sessions(db, current_user.id)
    existing = _active_for_content(db, current_user.id, content_id)
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
        active.status = SessionStatus.COMPLETED
        active.completion_status = "previously_completed"
        active.end_time = datetime.now()
        active.duration_minutes = active.calculate_duration()

    # Create new session
    new_session = LearningSession(
        student_id=current_user.id,
        content_id=content_id,
        status=SessionStatus.ACTIVE,
        completion_status="restarted",
        start_time=datetime.now(),
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return SessionResponse(
        id=new_session.id,
        content_id=new_session.content_id,
        start_time=new_session.start_time,
        status=new_session.status.value,
        duration_minutes=0,
        notes=None,
    )
