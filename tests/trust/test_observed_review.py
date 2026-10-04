"""Checked understanding and self-confidence have separate durable contracts."""

from tests.trust.test_resource_contracts import scenario, synthetic_credentials
from src.core.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    ContentType,
    MasteryNode,
    QuestionType,
    SubmissionStatus,
)
from src.core.services.assessed_review import record_assessed_mastery


def test_confidence_does_not_become_mastery(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    selected[0] = users["learner_a"]
    response = client.post(
        "/api/mastery/review", json={"content_id": lessons[0].id, "rating": 5}
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_assessed_mastery"] is False
    assert db.query(MasteryNode).count() == 0
    assert (
        client.post(
            "/api/mastery/review", json={"content_id": lessons[0].id, "rating": 6}
        ).status_code
        == 422
    )
    selected[0] = users["learner_b"]
    assert (
        client.post(
            "/api/mastery/review", json={"content_id": lessons[0].id, "rating": 5}
        ).status_code
        == 403
    )


def test_final_attempt_updates_review_once_and_correction_recomputes(scenario):
    _, db, users, _, plan, lessons, _ = scenario
    assessment = Assessment(
        title="Synthetic final",
        created_by_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        topic_id=lessons[0].id,
        total_points=10,
        is_published=True,
    )
    db.add(assessment)
    db.flush()
    submission = AssessmentSubmission(
        assessment_id=assessment.id,
        student_id=users["learner_a"].id,
        status=SubmissionStatus.SUBMITTED,
        total_points=10,
        score=None,
    )
    db.add(submission)
    db.flush()
    record_assessed_mastery(db, submission)
    assert db.query(MasteryNode).count() == 0
    submission.status = SubmissionStatus.GRADED
    submission.score = 7
    record_assessed_mastery(db, submission)
    db.commit()
    record_assessed_mastery(db, submission)
    db.commit()
    node = db.query(MasteryNode).one()
    assert (node.mastery_level, node.review_count) == (70, 1)
    submission.score = 9
    record_assessed_mastery(db, submission)
    db.commit()
    assert (node.mastery_level, node.review_count) == (90, 1)
