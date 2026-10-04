"""Small instructor-owned AI assistance settings for open assessment attempts."""

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session
from src.core.models import Assessment, AssessmentSubmission, SubmissionStatus, User
from src.core.roles import is_student

AssistanceMode = Literal["hints_only", "explanations", "disabled"]
MODES = {"explanations": 0, "hints_only": 1, "disabled": 2}
SETTING_KEY = "assessment_assistance_policies"


def assessment_policy(db: Session, assessment: Assessment) -> str:
    """Default to hints for legacy/new assessments without an explicit choice."""
    author = db.get(User, assessment.created_by_id)
    settings = author.settings or {} if author else {}
    entry = settings.get(SETTING_KEY, {}).get(str(assessment.id), {})
    mode = entry.get("mode", "hints_only") if isinstance(entry, dict) else "hints_only"
    return mode if mode in MODES else "hints_only"


def set_assessment_policy(db: Session, assessment: Assessment, mode: str) -> None:
    """Save one policy without replacing unrelated author settings."""
    if mode not in MODES:
        raise ValueError("Unknown assistance policy")
    author = db.get(User, assessment.created_by_id)
    if author is None:
        raise ValueError("Assessment author is unavailable")
    settings = dict(author.settings or {})
    policies = dict(settings.get(SETTING_KEY, {}))
    policies[str(assessment.id)] = {
        "mode": mode,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    settings[SETTING_KEY] = policies
    author.settings = settings


def effective_policy(db: Session, user: User) -> dict:
    """Enforce the strictest open-attempt rule even when no context ID is sent."""
    if not is_student(user):
        return {
            "mode": "explanations",
            "active_assessment_ids": [],
            "scope": "active_attempt",
            "reason": None,
        }
    active = (
        db.query(Assessment)
        .join(AssessmentSubmission)
        .filter(
            AssessmentSubmission.student_id == user.id,
            AssessmentSubmission.status == SubmissionStatus.DRAFT,
        )
        .all()
    )
    mode = max(
        (assessment_policy(db, assessment) for assessment in active),
        key=lambda mode: MODES[mode],
        default="explanations",
    )
    reasons = {
        "hints_only": "Your teacher allows hints while this assessment attempt is open.",
        "disabled": "Your teacher disables AI assistance while this assessment attempt is open.",
        "explanations": None,
    }
    return {
        "mode": mode,
        "active_assessment_ids": sorted({assessment.id for assessment in active}),
        "scope": "active_attempt",
        "reason": reasons[mode],
    }
