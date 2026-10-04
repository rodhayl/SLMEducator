"""Canonical curriculum and connected role journeys use actual synthetic APIs."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from src.core.models import (
    Assessment,
    AssessmentSubmission,
    Content,
    ContentType,
    LearningSession,
    Question,
    QuestionType,
    StudentStudyPlan,
    SubmissionStatus,
    User,
    UserRole,
)
from src.core.services.learning_context import source_context
from src.core.services.content_schema import normalize_content
from src.core.services.portability_service import export_course
from src.api.policies import teacher_student_ids
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def add_admin(db):
    admin = User(
        username="journey_admin",
        email="journey@example.invalid",
        first_name="Synthetic",
        last_name="Admin",
        password_hash="unused",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    return admin


def test_admin_enrollment_is_explicit_and_does_not_reclaim_from_legacy_assignment(
    scenario,
):
    client, db, users, selected, plan, _, _ = scenario
    admin = add_admin(db)
    selected[0] = users["teacher_b"]
    assert (
        client.put(
            f'/api/students/{users["learner_a"].id}/teacher',
            json={"teacher_id": selected[0].id},
        ).status_code
        == 403
    )
    selected[0] = admin
    assert plan.id in [item["id"] for item in client.get("/api/study-plans/").json()]
    for teacher_id in (users["teacher_b"].id, None):
        response = client.put(
            f'/api/students/{users["learner_a"].id}/teacher',
            json={"teacher_id": teacher_id},
        )
        assert response.status_code == 200, response.text
        assert response.json()["teacher_id"] == teacher_id
    assert users["learner_a"].id not in teacher_student_ids(db, users["teacher_a"].id)
    assert users["learner_a"].id not in teacher_student_ids(db, users["teacher_b"].id)
    assert len(users["learner_a"].settings["enrollment_history"]) == 2
    assert (
        db.query(StudentStudyPlan).filter_by(student_id=users["learner_a"].id).count()
        == 1
    )


def test_saved_draft_edits_invalidate_review_assigned_plan_requires_copy(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    selected[0] = users["teacher_a"]
    payload = {
        "title": "Edited",
        "description": "Draft correction",
        "phases": [{"name": "One", "content_ids": [lesson.id for lesson in lessons]}],
    }
    assert client.put(f"/api/study-plans/{plan.id}", json=payload).status_code == 409
    response = client.post(
        f"/api/study-plans/{plan.id}/copy", json={"reason": "revision"}
    )
    assert response.status_code == 200, response.text
    copied_id = response.json()["id"]
    assert response.json()["derived_from"]["plan_id"] == plan.id
    assert (
        client.get(f"/api/study-plans/{copied_id}/workflow").json()["status"] == "draft"
    )
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
        ).status_code
        == 200
    )
    assert client.put(f"/api/study-plans/{plan.id}", json=payload).status_code == 200
    assert (
        client.get(f"/api/study-plans/{plan.id}/workflow").json()["status"] == "draft"
    )


def test_explicit_attempt_close_preserves_work_consumes_attempt_and_releases_policy(
    scenario,
):
    client, db, users, selected, plan, _, _ = scenario
    assessment = Assessment(
        title="One reserved attempt",
        created_by_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        is_published=True,
        max_attempts=1,
    )
    db.add(assessment)
    db.flush()
    question = Question(
        assessment_id=assessment.id,
        question_text="Explain",
        question_type=QuestionType.SHORT_ANSWER,
        points=10,
    )
    db.add(question)
    db.commit()
    selected[0] = users["learner_a"]
    attempt = client.post(f"/api/assessments/{assessment.id}/start").json()
    assert client.get("/api/ai/assistance-policy").json()["mode"] == "hints_only"
    xp = users["learner_a"].xp
    response = client.post(
        f'/api/assessments/submissions/{attempt["id"]}/close',
        json={
            "reason": "abandoned",
            "answers": [
                {
                    "question_id": question.id,
                    "response_text": "Preserved unfinished thought",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "abandoned" and response.json()["score"] is None
    assert not response.json()["needs_review"]
    assert client.get("/api/ai/assistance-policy").json()["mode"] == "explanations"
    assert client.post(f"/api/assessments/{assessment.id}/start").status_code == 409
    assert (
        client.post(
            f'/api/assessments/submissions/{attempt["id"]}/close', json={}
        ).status_code
        == 200
    )
    detail = client.get(f'/api/assessments/submissions/{attempt["id"]}').json()
    assert detail["answers"][0]["given_answer"] == "Preserved unfinished thought"
    assert users["learner_a"].xp == xp
    selected[0] = users["teacher_a"]
    assert (
        client.post(
            f'/api/assessments/submissions/{attempt["id"]}/grade', json={"score": 0}
        ).status_code
        == 409
    )


def test_canonical_lesson_retains_distinct_body_and_sections_for_all_consumers(
    scenario,
):
    client, db, users, selected, plan, lessons, _ = scenario
    lesson = lessons[0]
    lesson.set_encrypted_content_data(
        {
            "content": "VISIBLE_BODY",
            "sections": [{"title": "Details", "content": "DETAILED_SECTION"}],
            "correct_answer": "HIDDEN_KEY",
        }
    )
    db.commit()
    selected[0] = users["learner_a"]
    visible = client.get(f"/api/content/{lesson.id}").json()["content_data"]
    source = source_context(lesson)
    handout = export_course(db, selected[0], plan, "learner")["contents"][0][
        "content_data"
    ]
    assert visible["sections"] == handout["sections"]
    assert visible["content"] == "VISIBLE_BODY\n\nDETAILED_SECTION"
    assert (
        "VISIBLE_BODY" in source.content_data
        and "DETAILED_SECTION" in source.content_data
    )
    assert "HIDDEN_KEY" not in source.content_data
    assert normalize_content("lesson", visible) == normalize_content(
        "lesson", normalize_content("lesson", visible)
    )


def test_tutor_rejects_mixed_course_context_and_includes_late_course_lesson(scenario):
    client, db, users, selected, plan, lessons, prompts = scenario
    selected[0] = users["learner_a"]
    from src.core.models import StudyPlan

    other = StudyPlan(title="Other", creator_id=users["teacher_a"].id, is_public=True)
    db.add(other)
    db.commit()
    assert (
        client.post(
            "/api/ai/chat",
            json={
                "message": "Explain",
                "content_id": lessons[0].id,
                "study_plan_id": other.id,
            },
        ).status_code
        == 409
    )
    assert prompts == []
    response = client.post(
        "/api/ai/chat", json={"message": "Explain SOURCE_2", "study_plan_id": plan.id}
    )
    assert response.status_code == 200, response.text
    assert "SOURCE_2" in prompts[-1] and response.json()["source"] is not None


def test_late_section_selection_is_bounded_and_source_version_is_portable():
    value = {"content": "early " * 3000 + "PEDAGOGICAL_MARKER_END numerator definition"}
    one = SimpleNamespace(
        id=1,
        title="Long",
        content_type=ContentType.LESSON,
        content_data="present",
        decrypted_content_data=value,
    )
    two = SimpleNamespace(
        id=999,
        title="Long",
        content_type=ContentType.LESSON,
        content_data="present",
        decrypted_content_data=value,
    )
    source = source_context(one, query="PEDAGOGICAL_MARKER_END")
    assert "PEDAGOGICAL_MARKER_END" in source.content_data
    assert len(source.content_data) <= 6000 and source.truncated
    assert source.source_version == source_context(two).source_version
    chosen = source_context(one, section_ids=[source.references[0]])
    assert (
        chosen.selection == "explicit_sections"
        and "PEDAGOGICAL_MARKER_END" in chosen.content_data
    )
    with pytest.raises(ValueError):
        source_context(one, section_ids=["content:2/section-1"])


def test_public_session_resumes_captured_revision_after_republication(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    plan.is_public = True
    db.commit()
    selected[0] = users["learner_a"]
    first = client.post(
        "/api/learning/start",
        json={"content_id": lessons[0].id, "study_plan_id": plan.id},
    )
    assert first.status_code == 200, first.text
    first = first.json()
    selected[0] = users["teacher_a"]
    assert (
        client.put(
            f"/api/content/{lessons[0].id}",
            json={"content_data": {"content": "REVISED TEXT"}},
        ).status_code
        == 200
    )
    for action in ("review", "publish"):
        assert (
            client.post(
                f"/api/study-plans/{plan.id}/workflow",
                json={"action": action, "is_public": True},
            ).status_code
            == 200
        )
    selected[0] = users["learner_a"]
    resumed = client.post(
        "/api/learning/start",
        json={"content_id": lessons[0].id, "study_plan_id": plan.id},
    ).json()
    assert resumed["id"] == first["id"]
    assert resumed["content_snapshot"] == first["content_snapshot"]
    assert "SOURCE_0" in resumed["content_snapshot"]["content_data"]["content"]
    assert "SOURCE_0" not in db.get(LearningSession, first["id"]).content_snapshot
    context = client.get("/api/ai/context", params={"session_id": first["id"]})
    assert context.status_code == 200, context.text
    assert "SOURCE_0" in context.json()["source"]["content_data"]
    assert "REVISED TEXT" not in context.json()["source"]["content_data"]
    answer = client.post(
        "/api/ai/chat",
        json={
            "message": "Explain",
            "session_id": first["id"],
            "source_version": context.json()["source"]["source_version"],
        },
    )
    assert answer.status_code == 200, answer.text
    assert "SOURCE_0" in answer.json()["source"]["content_data"]
    plan.is_public = False
    db.commit()
    assert (
        client.get("/api/ai/context", params={"session_id": first["id"]}).status_code
        == 403
    )
