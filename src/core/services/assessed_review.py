"""Feed review scheduling from final observed attempts, separately from confidence."""

from sqlalchemy.orm import Session

from src.core.models import (
    Assessment,
    AssessmentSubmission,
    MasteryNode,
    SubmissionStatus,
    User,
)
from src.core.services.temporal_service import utc_now

from .spaced_repetition_service import get_spaced_repetition_service


def record_assessed_mastery(db: Session, submission: AssessmentSubmission) -> None:
    """Recompute a linked topic from final attempts; replay cannot add observations."""
    assessment = submission.assessment
    if not isinstance(assessment, Assessment):
        return
    topic_id = assessment.topic_id
    if (
        not topic_id
        or submission.status != SubmissionStatus.GRADED
        or submission.score is None
        or submission.total_points is None
        or submission.total_points <= 0
    ):
        return
    user = db.get(User, submission.student_id)
    if user is None:
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
    scores = [
        100 * attempt.score / attempt.total_points
        for attempt in attempts
        if attempt.score is not None
        and attempt.total_points is not None
        and attempt.total_points > 0
    ]
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
    node.review_count = len(scores)
    node.last_reviewed = submission.graded_at or utc_now()
    node.next_review_due = get_spaced_repetition_service().calculate_next_review(
        level, len(scores), round(100 * submission.score / submission.total_points)
    )
    settings = dict(user.settings or {})
    observed = set(settings.get("assessed_content_ids", []))
    observed.add(topic_id)
    settings["assessed_content_ids"] = sorted(observed)
    user.settings = settings
