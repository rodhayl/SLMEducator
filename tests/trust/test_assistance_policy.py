"""Teacher assistance policy is enforced server-side for open learner attempts."""

from unittest.mock import MagicMock
import pytest
from tests.trust.test_resource_contracts import scenario, synthetic_credentials
from src.core.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    QuestionType,
    SubmissionStatus,
)
from src.core.services.assistance_policy import set_assessment_policy


def assessment_fixture(db, users, plan):
    assessment = Assessment(
        title="Policy practice",
        created_by_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        is_published=True,
        total_points=10,
    )
    db.add(assessment)
    db.flush()
    question = AssessmentQuestion(
        assessment_id=assessment.id,
        question_text="Explain fractions",
        question_type=QuestionType.SHORT_ANSWER,
        points=10,
    )
    db.add(question)
    db.commit()
    return assessment


def test_policy_owner_default_and_preserves_other_settings(scenario):
    client, db, users, selected, plan, _, _ = scenario
    assessment = assessment_fixture(db, users, plan)
    selected[0] = users["teacher_a"]
    users["teacher_a"].settings = {
        "timezone": "Europe/Madrid",
        "other_setting": "preserved",
    }
    db.commit()
    assert (
        client.get(f"/api/assessments/{assessment.id}/assistance-policy").json()["mode"]
        == "hints_only"
    )
    response = client.put(
        f"/api/assessments/{assessment.id}/assistance-policy", json={"mode": "disabled"}
    )
    assert response.status_code == 200, response.text
    assert users["teacher_a"].settings["other_setting"] == "preserved"
    selected[0] = users["teacher_b"]
    assert (
        client.put(
            f"/api/assessments/{assessment.id}/assistance-policy",
            json={"mode": "explanations"},
        ).status_code
        == 403
    )
    selected[0] = users["learner_a"]
    assert (
        client.get(f"/api/assessments/{assessment.id}/assistance-policy").json()["mode"]
        == "disabled"
    )
    assert (
        client.put(
            f"/api/assessments/{assessment.id}/assistance-policy",
            json={"mode": "explanations"},
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "endpoint,body",
    [
        ("/api/ai/chat", {"message": "Give the answer", "assistance": "explanation"}),
        ("/api/ai/answer-question", {"question": "Give the answer"}),
    ],
)
def test_disabled_attempt_policy_cannot_be_bypassed_by_omitting_context(
    scenario, endpoint, body
):
    client, db, users, selected, plan, _, captured = scenario
    assessment = assessment_fixture(db, users, plan)
    set_assessment_policy(db, assessment, "disabled")
    db.commit()
    selected[0] = users["learner_a"]
    attempt = client.post(f"/api/assessments/{assessment.id}/start")
    assert attempt.status_code == 200, attempt.text
    policy = client.get("/api/ai/assistance-policy").json()
    assert policy["mode"] == "disabled" and policy["active_assessment_ids"] == [
        assessment.id
    ]
    assert client.post(endpoint, json=body).status_code == 403
    assert captured == []
    # No other learner's open attempt or restriction leaks into this account.
    selected[0] = users["learner_b"]
    assert client.get("/api/ai/assistance-policy").json()["mode"] == "explanations"


def test_hints_enforced_then_submission_releases_active_attempt_scope(scenario):
    client, db, users, selected, plan, lessons, captured = scenario
    assessment = assessment_fixture(db, users, plan)
    selected[0] = users["learner_a"]
    attempt = client.post(f"/api/assessments/{assessment.id}/start").json()
    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Solve it",
            "assistance": "explanation",
            "content_id": lessons[0].id,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["assistance_policy"]["mode"] == "hints_only"
    assert response.json()["effective_assistance"] == "hint"
    assert "Assistance mode: hint" in captured[0]
    submission = db.get(AssessmentSubmission, attempt["id"])
    submission.status = SubmissionStatus.SUBMITTED
    db.commit()
    assert client.get("/api/ai/assistance-policy").json()["mode"] == "explanations"


def test_teacher_disabling_during_provider_work_blocks_delivery(scenario, monkeypatch):
    from src.api.routes import ai

    client, db, users, selected, plan, _, _ = scenario
    assessment = assessment_fixture(db, users, plan)
    selected[0] = users["learner_a"]
    assert client.post(f"/api/assessments/{assessment.id}/start").status_code == 200
    service = MagicMock()

    def finish(**kwargs):
        from sqlalchemy.orm import Session

        with Session(db.get_bind()) as teacher_db:
            current = teacher_db.get(Assessment, assessment.id)
            set_assessment_policy(teacher_db, current, "disabled")
            teacher_db.commit()
        return {"explanation": "Must not be delivered after the policy changed."}

    service.provide_tutoring.side_effect = finish
    monkeypatch.setattr(ai, "get_ai_service_dependency", lambda *args: service)
    response = client.post("/api/ai/chat", json={"message": "Explain"})
    assert response.status_code == 403 and "Must not be delivered" not in response.text
    service.close.assert_called_once()


@pytest.mark.parametrize("failure", ["empty_answer", "provider_error", "setup_error"])
def test_question_fallback_preserves_enforced_hint_policy(
    scenario, monkeypatch, failure
):
    from src.api.routes import ai

    client, db, users, selected, plan, _, _ = scenario
    assessment = assessment_fixture(db, users, plan)
    selected[0] = users["learner_a"]
    assert client.post(f"/api/assessments/{assessment.id}/start").status_code == 200
    service = MagicMock()
    service.provide_tutoring.return_value = {"explanation": "   "}
    if failure == "provider_error":
        service.provide_tutoring.side_effect = RuntimeError("Synthetic provider failure")
    dependency = MagicMock(return_value=service)
    if failure == "setup_error":
        dependency.side_effect = RuntimeError("Synthetic configuration failure")
    monkeypatch.setattr(ai, "get_ai_service_dependency", dependency)

    response = client.post(
        "/api/ai/answer-question",
        json={"question": "Solve this assessment", "assistance": "explanation"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["assistance_policy"]["mode"] == "hints_only"
    assert body["assistance_policy"]["active_assessment_ids"] == [assessment.id]
    assert body["effective_assistance"] == "hint"
    if failure == "setup_error":
        service.provide_tutoring.assert_not_called()
        service.close.assert_not_called()
    else:
        assert "Assistance mode: hint" in service.provide_tutoring.call_args.kwargs["context"]
        service.close.assert_called_once()


def test_teacher_package_preserves_assistance_policy_as_new_owner_setting(scenario):
    from src.core.services.portability_service import export_course, import_course
    from src.core.services.assistance_policy import assessment_policy

    _, db, users, _, plan, _, _ = scenario
    assessment = assessment_fixture(db, users, plan)
    set_assessment_policy(db, assessment, "disabled")
    db.commit()
    package = export_course(db, users["teacher_a"], plan, "teacher")
    assert package["assessments"][0]["assistance_policy"] == "disabled"
    imported = import_course(db, users["teacher_b"], package)
    db.commit()
    copy = db.query(Assessment).filter_by(study_plan_id=imported.id).one()
    assert copy.created_by_id == users["teacher_b"].id
    assert assessment_policy(db, copy) == "disabled" and not copy.is_published
