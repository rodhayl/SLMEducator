"""Feed review scheduling from final observed attempts, separately from confidence."""

from src.core.services.temporal_service import utc_now

from datetime import datetime
from sqlalchemy.orm import Session
from src.core.models import (
    Assessment,
    AssessmentSubmission,
    MasteryNode,
    SubmissionStatus,
    User,
)
from .spaced_repetition_service import get_spaced_repetition_service


def record_assessed_mastery(db: Session, submission: AssessmentSubmission) -> None:
    """Recompute a linked topic from final attempts; replay cannot add observations."""
    topic_id = submission.assessment.topic_id
    if (
        not topic_id
        or submission.status != SubmissionStatus.GRADED
        or submission.score is None
        or not submission.total_points
    ):
        return
    db.flush()
    attempts = (
        db.query(AssessmentSubmission)
        .join(Assessment)
        .filter(
            AssessmentSubmission.student_id == submission.student_id,
            Assessment.topic_id == topic_id,
            AssessmentSubmission.status == SubmissionStatus.GRADED,
            AssessmentSubmission.score.isnot(None),
            AssessmentSubmission.total_points > 0,
        )
        .all()
    )
    scores = [100 * attempt.score / attempt.total_points for attempt in attempts]
    if not scores:
        return
    level = round(sum(scores) / len(scores))
    node = (
        db.query(MasteryNode)
        .filter_by(student_id=submission.student_id, content_id=topic_id)
        .first()
    )
    if node is None:
        node = MasteryNode(student_id=submission.student_id, content_id=topic_id)
        db.add(node)
    node.mastery_level = level
    node.review_count = len(attempts)
    node.last_reviewed = submission.graded_at or utc_now()
    node.next_review_due = get_spaced_repetition_service().calculate_next_review(
        level, len(attempts), round(100 * submission.score / submission.total_points)
    )
    user = db.get(User, submission.student_id)
    settings = dict(user.settings or {})
    observed = set(settings.get("assessed_content_ids", []))
    observed.add(topic_id)
    settings["assessed_content_ids"] = sorted(observed)
    user.settings = settings
