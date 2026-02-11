from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    User,
    LearningSession,
    SessionStatus,
    Content,
    DailyGoal,
    ContentType,
)

router = APIRouter(prefix="/api/learning", tags=["learning"])

# --- Pydantic Models ---


class SessionStart(BaseModel):
    content_id: int


class SessionUpdate(BaseModel):
    notes: Optional[str] = None
    difficulty_rating: Optional[int] = None  # 1-5, used for Spaced Repetition later


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
    content = db.query(Content).filter(Content.id == data.content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Check for existing active session? Optional.
    # For simplicity, we allow starting new one.

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
    """End a learning session and award XP/mastery"""
    from src.core.services.progress_tracking_service import (
        get_progress_tracking_service,
    )
    from src.core.services.spaced_repetition_service import (
        get_spaced_repetition_service,
    )

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

    session.end_time = datetime.now()
    session.status = SessionStatus.COMPLETED
    session.notes = data.notes

    # Calculate duration
    session.duration_minutes = session.calculate_duration()

    db.commit()
    db.refresh(session)

    # Award XP and update mastery (after commit to avoid transaction issues)
    try:
        pts = get_progress_tracking_service()
        sr = get_spaced_repetition_service()

        # Award base XP for completing a session (50 XP)
        pts.award_xp(current_user.id, 50)

        # Update streak
        pts.update_streak(current_user.id)

        # Update mastery based on difficulty rating if provided
        if session.content_id:
            performance = (data.difficulty_rating or 3) * 20  # Convert 1-5 to 20-100
            sr.update_review_outcome(current_user.id, session.content_id, performance)

        # Check for any new badges
        pts.check_and_award_badges(current_user.id)

        # Update Daily Goal
        today = date.today()
        daily_goal = (
            db.query(DailyGoal)
            .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
            .first()
        )

        if daily_goal and not daily_goal.completed:
            content = db.query(Content).filter(Content.id == session.content_id).first()
            should_increment = False
            increment_value = 1

            if daily_goal.goal_type == "lessons":
                # Increment for lessons or any content (lesson is the primary use case)
                if content and content.content_type == ContentType.LESSON:
                    should_increment = True
            elif daily_goal.goal_type == "exercises":
                if content and content.content_type == ContentType.EXERCISE:
                    should_increment = True
            elif daily_goal.goal_type == "time":
                # Increment by duration in minutes
                should_increment = True
                increment_value = session.duration_minutes or 1

            if should_increment:
                daily_goal.current_value += increment_value
                if daily_goal.current_value >= daily_goal.target_value:
                    daily_goal.completed = True
                db.commit()
    except Exception:
        pass  # Gamification and goal updates are non-critical

    return SessionResponse(
        id=session.id,
        content_id=session.content_id,
        start_time=session.start_time,
        status=session.status.value,
        duration_minutes=session.duration_minutes,
        notes=session.notes,
    )


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

    if session.status == SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is already active")

    # Reactivate the session
    session.status = SessionStatus.ACTIVE
    session.end_time = None  # Clear end time
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
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

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
        active.end_time = datetime.now()
        active.duration_minutes = active.calculate_duration()

    # Create new session
    new_session = LearningSession(
        student_id=current_user.id,
        content_id=content_id,
        status=SessionStatus.ACTIVE,
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
