"""
Students API Routes

Provides student management functionality including progress tracking and teacher notes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import logging

from src.api.dependencies import get_db
from src.api.security import require_teacher_or_admin
from src.core.models import (
    User,
    UserRole,
    LearningSession,
    SessionStatus,
    AssessmentSubmission,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("/")
async def list_students(
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """List students accessible to the current user (teachers see their assigned students)."""
    students = (
        db.query(User).filter(User.role == UserRole.STUDENT, User.active == True).all()
    )

    return [
        {
            "id": s.id,
            "username": s.username,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "email": s.email,
            "xp": s.xp or 0,
            "level": s.level or 1,
            "current_streak": s.current_streak or 0,
        }
        for s in students
    ]


@router.get("/{student_id}/progress")
async def get_student_progress(
    student_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Get progress statistics for a specific student."""
    # Verify student exists
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Calculate lessons completed
    lessons_completed = (
        db.query(LearningSession)
        .filter(
            LearningSession.student_id == student_id,
            LearningSession.status == SessionStatus.COMPLETED,
        )
        .count()
    )

    # Calculate assessments taken
    assessments_taken = (
        db.query(AssessmentSubmission)
        .filter(
            AssessmentSubmission.student_id == student_id,
            AssessmentSubmission.submitted_at.isnot(None),
        )
        .count()
    )

    # Calculate average score
    avg_score_result = (
        db.query(func.avg(AssessmentSubmission.score))
        .filter(
            AssessmentSubmission.student_id == student_id,
            AssessmentSubmission.score.isnot(None),
        )
        .scalar()
    )
    avg_score = float(avg_score_result) if avg_score_result else None

    # Calculate total study time
    study_time_minutes = (
        db.query(func.sum(LearningSession.duration_minutes))
        .filter(
            LearningSession.student_id == student_id,
            LearningSession.status == SessionStatus.COMPLETED,
        )
        .scalar()
        or 0
    )
    study_time_hours = float(study_time_minutes) / 60.0

    return {
        "lessons_completed": lessons_completed,
        "assessments_taken": assessments_taken,
        "avg_score": avg_score,
        "study_time_hours": study_time_hours,
    }


class TeacherNoteInput(BaseModel):
    notes: str


# Notes are stored in current user's settings (JSON field) with key 'student_notes_{id}'
@router.get("/{student_id}/notes")
async def get_student_notes(
    student_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Get teacher notes for a specific student (stored in user settings)."""
    # Use the settings field on User if available, or return empty
    # Merge detached user or re-query to ensure fresh settings
    current_user = db.merge(current_user)

    settings = current_user.settings or {}
    notes_key = f"student_notes_{student_id}"
    return {"notes": settings.get(notes_key, "")}


@router.post("/{student_id}/notes")
async def save_student_notes(
    student_id: int,
    note_input: TeacherNoteInput,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Save teacher notes for a specific student (stored in user settings)."""
    try:
        # Re-query user in current session to ensure we are modifying the attached instance
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Store in user settings JSON field
        if user.settings is None:
            user.settings = {}

        # Create a new dict to ensure change detection
        notes_key = f"student_notes_{student_id}"
        new_settings = dict(user.settings)
        new_settings[notes_key] = note_input.notes
        user.settings = new_settings

        # Mark settings as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(user, "settings")

        db.commit()
        return {"success": True, "message": "Notes saved successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save notes: {e}")
        raise HTTPException(status_code=500, detail="Failed to save notes")
