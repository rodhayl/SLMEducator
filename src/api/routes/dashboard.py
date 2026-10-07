"""
Dashboard API Routes

Provides real-time statistics and activity feed for the dashboard.
"""

from src.core.services.temporal_service import utc_now, known_instant, known_after, known_timestamp_clause, last_activity_day

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    User,
    LearningSession,
    SessionStatus,
    Content,
    Assessment,
    AssessmentSubmission,
    SubmissionStatus,
)
from src.core.roles import is_teacher

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for the current user.

    Teachers see: active students, assessments created, average score.
    Students see: completed lessons, current streak, XP points.
    """
    teacher_view = is_teacher(current_user)

    completed_sessions = db.query(LearningSession).filter(
        LearningSession.student_id == current_user.id,
        LearningSession.status == SessionStatus.COMPLETED,
    )
    completed_lessons = completed_sessions.count()
    total_study_time_minutes = (
        completed_sessions.filter(
            known_timestamp_clause(LearningSession.start_time),
            known_timestamp_clause(LearningSession.end_time),
        ).with_entities(
            func.coalesce(func.sum(LearningSession.duration_minutes), 0)
        ).scalar()
        or 0
    )
    total_study_time_minutes = int(total_study_time_minutes)
    unknown_duration_sessions = completed_sessions.filter(
        (~known_timestamp_clause(LearningSession.start_time))
        | (~known_timestamp_clause(LearningSession.end_time))
        | LearningSession.end_time.is_(None)
    ).count()
    total_content = (
        db.query(Content).filter(Content.creator_id == current_user.id).count()
    )

    if teacher_view:
        # Count students assigned to this teacher
        active_students = (
            db.query(User)
            .filter(User.teacher_id == current_user.id, User.active == True)
            .count()
        )

        # Count assessments created by this teacher
        assessments_created = (
            db.query(Assessment)
            .filter(Assessment.created_by_id == current_user.id)
            .count()
        )

        # Calculate average score from submissions for teacher's assessments
        avg_result = (
            db.query(
                func.avg(
                    100.0
                    * AssessmentSubmission.score
                    / func.nullif(AssessmentSubmission.total_points, 0)
                )
            )
            .join(Assessment, Assessment.id == AssessmentSubmission.assessment_id)
            .filter(
                Assessment.created_by_id == current_user.id,
                AssessmentSubmission.score.isnot(None),
                AssessmentSubmission.status == SubmissionStatus.GRADED,
            )
            .scalar()
        )
        average_score = round(avg_result) if avg_result is not None else None

        return {
            "active_students": active_students,
            "assessments_created": assessments_created,
            "average_score": average_score,
            "total_content": total_content,
            "completed_lessons": completed_lessons,
            "total_study_time_minutes": total_study_time_minutes,
            "unknown_duration_sessions": unknown_duration_sessions,
        }
    else:
        # Student stats
        # Get streak and XP from user profile (gamification fields)
        current_streak = current_user.current_streak or 0
        points = current_user.xp or 0

        return {
            "total_content": total_content,
            "completed_lessons": completed_lessons,
            "total_study_time_minutes": total_study_time_minutes,
            "unknown_duration_sessions": unknown_duration_sessions,
            "current_streak": current_streak,
            "streak_provenance": "recorded" if last_activity_day(current_user) else "legacy_unknown",
            "points": points,
        }


@router.get("/activity")
async def get_recent_activity(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get recent activity for the current user.

    Returns learning sessions and assessment completions from the last 7 days.
    """
    seven_days_ago = utc_now() - timedelta(days=7)
    activities = []

    # Get recent learning sessions
    sessions = (
        db.query(LearningSession)
        .filter(
            LearningSession.student_id == current_user.id,
            LearningSession.status == SessionStatus.COMPLETED,
            known_after(LearningSession.end_time, seven_days_ago, inclusive=True),
        )
        .order_by(func.julianday(LearningSession.end_time).desc())
        .limit(5)
        .all()
    )

    for session in sessions:
        # Get content title if available
        content_title = "Unknown Content"
        if session.content:
            content_title = session.content.title

        time_str = _format_relative_time(session.end_time)
        activities.append(
            {"id": session.id, "text": f"Completed '{content_title}'", "time": time_str, "_instant": session.end_time}
        )

    # Get recent assessment submissions
    submissions = (
        db.query(AssessmentSubmission)
        .filter(
            AssessmentSubmission.student_id == current_user.id,
            AssessmentSubmission.submitted_at.isnot(None),
            known_after(AssessmentSubmission.submitted_at, seven_days_ago, inclusive=True),
        )
        .order_by(func.julianday(AssessmentSubmission.submitted_at).desc())
        .limit(5)
        .all()
    )

    for sub in submissions:
        assessment_title = "Unknown Assessment"
        if sub.assessment:
            assessment_title = sub.assessment.title

        score_text = "Submitted"
        if sub.score is not None and sub.status == SubmissionStatus.GRADED:
            if sub.total_points:
                percent = round((sub.score / sub.total_points) * 100)
                score_text = f"Scored {sub.score}/{sub.total_points} ({percent}%)"
            else:
                score_text = f"Scored {sub.score} pts"
        time_str = _format_relative_time(sub.submitted_at)
        activities.append(
            {
                "id": sub.id + 10000,  # Offset to avoid ID collision
                "text": f"{score_text} on '{assessment_title}'",
                "time": time_str,
                "_instant": sub.submitted_at,
            }
        )

    # Sort by recency and limit to 10
    activities.sort(key=lambda x: x["_instant"], reverse=True)
    for activity in activities:
        activity.pop("_instant")
    return (
        activities[:10]
        if activities
        else [{"id": 0, "text": "No recent activity", "time": "Start learning!"}]
    )


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string."""
    if not known_instant(dt):
        return "Unknown timezone"

    now = utc_now()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"

    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"

    return "Just now"
