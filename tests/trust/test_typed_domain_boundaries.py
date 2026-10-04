"""Typed domain boundaries preserve real validation and unknown-time semantics."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.core.models import Assessment, Question, QuestionType, Rubric, RubricCriterion, StudyPlan
from src.core.services import course_workflow
from src.core.services.assessment_contract import definition_digest, validate_definition
from src.core.services.generation_workflow import _draft_assessment
from src.core.services.progress_tracking_service import ProgressTrackingService
from src.core.services.temporal_service import utc_now


def test_review_requires_a_persisted_course(db_service):
    with pytest.raises(ValueError, match="Save the course"):
        course_workflow.course_snapshot(db_service.session, StudyPlan(title="Unsaved"))


@pytest.mark.parametrize("phase,order", [(None, 0), (0, None), (-1, 0), (0, 1001)])
def test_review_rejects_missing_or_invalid_graph_positions(
    db_service, test_teacher, monkeypatch, phase, order
):
    plan = StudyPlan(title="Synthetic", creator_id=test_teacher.id)
    db_service.session.add(plan)
    db_service.session.commit()
    monkeypatch.setattr(
        course_workflow,
        "course_items",
        lambda *args: [SimpleNamespace(phase_index=phase, order_index=order)],
    )
    with pytest.raises(ValueError, match="bounded, unique"):
        course_workflow.course_snapshot(db_service.session, plan)


def test_definition_digest_handles_unflushed_draft_without_inventing_rules():
    assessment = Assessment(title="Draft")
    assessment.questions = [
        Question(question_text="Explain", question_type=QuestionType.SHORT_ANSWER, points=4)
    ]
    rubric = Rubric(name="Reasoning")
    rubric.criteria = [RubricCriterion(name="Method", max_points=4)]
    assessment.rubrics = [rubric]
    first = definition_digest(assessment)
    assert definition_digest(assessment) == first
    assert assessment.grading_mode is None and assessment.questions[0].id is None
    assessment.questions[0].question_text = "Explain with another example"
    assert definition_digest(assessment) != first


def test_definition_validation_rejects_unset_question_points():
    assessment = Assessment(title="Incomplete")
    assessment.questions = [
        Question(question_text="Explain", question_type=QuestionType.SHORT_ANSWER)
    ]
    with pytest.raises(ValueError, match="positive-point"):
        validate_definition(assessment)


def test_generated_assessment_total_is_sum_of_validated_questions(db_service, test_teacher):
    result = _draft_assessment(
        db_service.session,
        test_teacher,
        SimpleNamespace(topic_name="Fractions", study_plan_id=None),
        {
            "questions": [{"question": "First", "points": 3}, {"question": "Second", "points": 4}],
        },
    )
    db_service.session.commit()
    assert result.total_points == 7
    assert [q.points for q in result.questions] == [3, 4]


@pytest.mark.parametrize("age,expected", [(None, 0), (0, 5), (1, 5), (2, 0), (-1, 0)])
def test_streak_services_agree_on_known_and_unknown_activity(
    db_service, test_student, age, expected
):
    user = test_student
    user.current_streak, user.longest_streak = 5, 8
    user.last_activity_date = utc_now().date()  # This date alone has no zone provenance.
    user.settings = {"timezone": "UTC"}
    if age is not None:
        user.settings = {
            **user.settings,
            "activity_clock": {"last_at": (utc_now() - timedelta(days=age)).isoformat()},
        }
    db_service.session.commit()
    progress = ProgressTrackingService().get_streak(user.id)
    assert progress == {"current_streak": expected, "longest_streak": 8}
    assert db_service.get_study_stats(user.id)["streak_days"] == expected


def test_missing_account_has_no_streak(db_service):
    assert ProgressTrackingService().get_streak(999999) == {
        "current_streak": 0,
        "longest_streak": 0,
    }
    assert db_service.get_study_stats(999999)["streak_days"] == 0
