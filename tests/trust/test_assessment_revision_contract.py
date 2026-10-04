"""Draft/save timer regressions using disposable synthetic assessment rows."""
import pytest

from tests.integration.test_trustworthy_scoring_sessions import create_quiz, world
from src.core.models import Assessment, StudentStudyPlan, Submission


@pytest.mark.parametrize("changes", [
    {"title": "Revised title"},
    {"description": "Revised directions"},
    {"passing_score": 80},
    {"time_limit_minutes": None},
    {"max_attempts": 2},
    {"is_published": True, "title": "Stale publication flag"},
])
def test_revised_published_assessment_is_draft_until_explicit_publish(world, changes):
    """Saving any material/policy revision before attempts hides it from learners."""
    assessment_id, _ = create_quiz(world, time_limit_minutes=45)
    world.user = world.owner
    saved = world.client.put(f"/api/assessments/{assessment_id}", json=changes)
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_published"] is False
    world.user = world.learner
    assert world.client.get(f"/api/assessments/{assessment_id}").status_code == 403
    assert world.client.post(f"/api/assessments/{assessment_id}/start").status_code == 403
    world.user = world.owner
    assert world.client.post(f"/api/assessments/{assessment_id}/publish").status_code == 200
    world.user = world.learner
    assert world.client.get(f"/api/assessments/{assessment_id}").status_code == 200


def test_timer_null_clears_but_omission_preserves_value(world):
    """An explicit unlimited timer survives save/GET; omission is not a reset."""
    assessment_id, _ = create_quiz(world, time_limit_minutes=45)
    world.user = world.owner
    assert world.client.put(f"/api/assessments/{assessment_id}", json={"title": "Changed"}).status_code == 200
    assert world.client.get(f"/api/assessments/{assessment_id}").json()["time_limit_minutes"] == 45
    assert world.client.put(f"/api/assessments/{assessment_id}", json={"time_limit_minutes": None}).status_code == 200
    assert world.client.get(f"/api/assessments/{assessment_id}").json()["time_limit_minutes"] is None


def test_clearing_timer_after_attempt_remains_rejected_and_unchanged(world):
    """A started attempt's timing/version cannot be rewritten by draft save."""
    assessment_id, _ = create_quiz(world, time_limit_minutes=45)
    assert world.client.post(f"/api/assessments/{assessment_id}/start").status_code == 200
    world.user = world.owner
    saved = world.client.put(f"/api/assessments/{assessment_id}", json={"time_limit_minutes": None, "is_published": False})
    assert saved.status_code == 409
    persisted = world.db.get(Assessment, assessment_id)
    world.db.refresh(persisted)
    assert persisted.time_limit_minutes == 45
    assert persisted.is_published is True


@pytest.mark.parametrize("changes", [
    {"questions": [{"question_text": "Changed", "question_type": "short_answer", "points": 5}]},
    {"rubric": {"name": "Changed rubric", "criteria": [{"name": "Reasoning", "max_points": 10}]}},
    {"rubric": None},
    {"time_limit_minutes": None},
    {"grading_mode": "manual"},
    {"passing_score": 80},
    {"max_attempts": 3},
    {"title": "Changed title"},
    {"description": "Changed directions"},
    {"is_published": False},
    {"is_published": False, "time_limit_minutes": None},
])
def test_assigned_published_definition_frozen_before_first_attempt(world, changes):
    plan_id = world.content.study_plan_id
    assessment_id, _ = create_quiz(world, study_plan_id=plan_id, time_limit_minutes=45)
    world.db.add(StudentStudyPlan(student_id=world.learner.id, study_plan_id=plan_id))
    world.db.commit()
    world.user = world.owner
    before = world.client.get(f"/api/assessments/{assessment_id}").json()
    assert world.db.query(Submission).count() == 0

    saved = world.client.put(f"/api/assessments/{assessment_id}", json=changes)

    assert saved.status_code == 409, saved.text
    assert "Copy it to a new draft" in saved.json()["detail"]
    assert world.client.get(f"/api/assessments/{assessment_id}").json() == before
    assert world.db.query(Submission).count() == 0


def test_new_assigned_course_draft_remains_editable_until_published(world):
    plan_id = world.content.study_plan_id
    world.db.add(StudentStudyPlan(student_id=world.learner.id, study_plan_id=plan_id))
    world.db.commit()
    world.user = world.owner
    created = world.client.post("/api/assessments/", json={
        "title": "New unpublished definition", "study_plan_id": plan_id,
        "questions": [{"question_text": "Reasoning", "question_type": "short_answer", "points": 10}],
    })
    assert created.status_code == 200, created.text
    assessment_id = created.json()["id"]
    saved = world.client.put(f"/api/assessments/{assessment_id}", json={
        "title": "Reviewed new draft", "time_limit_minutes": 20,
        "rubric": {"name": "Evidence", "criteria": [{"name": "Reasoning", "max_points": 10}]},
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_published"] is False
    assert world.client.post(f"/api/assessments/{assessment_id}/publish").status_code == 200
    assert world.client.put(f"/api/assessments/{assessment_id}", json={"time_limit_minutes": None}).status_code == 409
    assert world.client.get(f"/api/assessments/{assessment_id}").json()["time_limit_minutes"] == 20


def test_published_unassigned_plan_assessment_can_return_to_draft(world):
    assessment_id, _ = create_quiz(world, study_plan_id=world.content.study_plan_id)
    world.user = world.owner
    saved = world.client.put(f"/api/assessments/{assessment_id}", json={"time_limit_minutes": 20})
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_published"] is False
