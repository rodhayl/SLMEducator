"""Missing identities must not grant enrollment or create assessed mastery."""

from unittest.mock import MagicMock

from src.api.policies import teacher_student_ids
from src.core.models import Assessment, AssessmentSubmission, SubmissionStatus
from src.core.services.assessed_review import record_assessed_mastery
from tests.trust import test_resource_contracts as fixture_source

# Expose reusable pytest fixtures without importing their test functions.
scenario = fixture_source.scenario
synthetic_credentials = fixture_source.synthetic_credentials


def test_missing_teacher_identity_never_queries_unclaimed_learners():
    db = MagicMock()
    assert teacher_student_ids(db, None) == []
    db.query.assert_not_called()


def test_missing_assessment_does_not_create_mastery():
    db = MagicMock()
    submission = AssessmentSubmission(
        student_id=1, status=SubmissionStatus.GRADED, score=7, total_points=10
    )
    record_assessed_mastery(db, submission)
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_missing_student_does_not_partially_update_mastery():
    db = MagicMock()
    db.get.return_value = None
    submission = AssessmentSubmission(
        student_id=999,
        status=SubmissionStatus.GRADED,
        score=7,
        total_points=10,
        assessment=Assessment(topic_id=3),
    )
    record_assessed_mastery(db, submission)
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_missing_teacher_identity_cannot_read_unclaimed_real_rows(scenario):
    _, db, users, _, _, _, _ = scenario
    users["learner_a"].teacher_id = None
    db.flush()
    assert teacher_student_ids(db, None) == []
    assert users["learner_b"].id in teacher_student_ids(db, users["teacher_b"].id)
