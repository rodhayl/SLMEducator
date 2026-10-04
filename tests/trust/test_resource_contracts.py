"""Synthetic two-teacher/two-learner reproductions of the product-trust review."""

import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    Content,
    ContentType,
    StudyPlan,
    StudyPlanContent,
    StudentStudyPlan,
    User,
    UserRole,
)
from src.core.services.ai_service import AIService, AIResponse, AIProvider
from src.core.services.auth import AuthService


@pytest.fixture(autouse=True)
def synthetic_credentials(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "synthetic-only-regression-signing-secret-123456")


@pytest.fixture
def scenario(db_service, monkeypatch):
    db = db_service.get_session()
    users = {}
    for name, role in [
        ("teacher_a", UserRole.TEACHER),
        ("teacher_b", UserRole.TEACHER),
        ("learner_a", UserRole.STUDENT),
        ("learner_b", UserRole.STUDENT),
    ]:
        user = User(
            username=name,
            email=f"{name}@example.test",
            password_hash="unused-synthetic",
            first_name="Synthetic",
            last_name=name,
            role=role,
        )
        db.add(user)
        db.flush()
        users[name] = user
    users["learner_a"].teacher_id = users["teacher_a"].id
    users["learner_b"].teacher_id = users["teacher_b"].id
    plan = StudyPlan(
        title="Synthetic fractions course",
        creator_id=users["teacher_a"].id,
        phases=[],
        is_public=False,
    )
    db.add(plan)
    db.flush()
    lessons = []
    for index, title in enumerate(
        ["Equal parts", "Compare fractions", "Independent practice"]
    ):
        lesson = Content(
            title=title,
            creator_id=users["teacher_a"].id,
            study_plan_id=plan.id,
            content_type=ContentType.LESSON,
        )
        lesson.set_encrypted_content_data(
            {
                "content": f"SOURCE_{index}: Compare numerators when denominators are equal.",
                "correct_answer": "HIDDEN_KEY_NEVER_TUTOR",
            }
        )
        db.add(lesson)
        db.flush()
        lessons.append(lesson)
        db.add(
            StudyPlanContent(
                study_plan_id=plan.id,
                content_id=lesson.id,
                phase_index=index,
                order_index=0,
            )
        )
    db.add(
        StudentStudyPlan(
            student_id=users["learner_a"].id, study_plan_id=plan.id, progress={}
        )
    )
    db.commit()
    selected = [users["learner_b"]]
    captured = []
    monkeypatch.setattr(
        AIService, "_setup_client", lambda self: setattr(self, "_client", MagicMock())
    )

    def fake_call(self, prompt, *args, **kwargs):
        captured.append(prompt)
        return AIResponse(
            content='{"explanation": "Try comparing the numerators."}',
            tokens_used=0,
            model="synthetic",
            provider=AIProvider.OLLAMA,
            response_time=0,
            timestamp=datetime.now(),
        )

    monkeypatch.setattr(AIService, "_call_ai", fake_call)
    app.dependency_overrides[get_current_user] = lambda: selected[0]
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db, users, selected, plan, lessons, captured
    app.dependency_overrides.clear()
    db.close()


@pytest.mark.parametrize(
    "path,payload",
    [
        (
            "/api/ai/chat",
            lambda p, c: {
                "message": "Explain",
                "content_id": c.id,
                "study_plan_id": p.id,
            },
        ),
        ("/api/learning/start", lambda p, c: {"content_id": c.id}),
        (
            "/api/annotations/",
            lambda p, c: {"content_id": c.id, "annotation_text": "private"},
        ),
        (
            "/api/classroom/help",
            lambda p, c: {
                "subject": "Help",
                "description": "Explain",
                "content_id": c.id,
            },
        ),
    ],
)
def test_unassigned_resources_denied_before_ai(scenario, path, payload):
    client, db, users, selected, plan, lessons, captured = scenario
    response = client.post(path, json=payload(plan, lessons[0]))
    assert response.status_code == 403, response.text
    assert captured == []


def test_private_relink_and_foreign_plan_writes_denied(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    selected[0] = users["teacher_b"]
    assert (
        client.post(
            "/api/study-plans/",
            json={
                "title": "Relink",
                "phases": [{"name": "Stolen", "content_ids": [lessons[0].id]}],
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/content/",
            json={
                "title": "Injected",
                "study_plan_id": plan.id,
                "content_data": {"content": "test"},
            },
        ).status_code
        == 403
    )
    # Already-existing bad links must not keep granting access.
    other = StudyPlan(
        title="Legacy unsafe association",
        creator_id=users["teacher_b"].id,
        phases=[],
        is_public=False,
    )
    db.add(other)
    db.flush()
    db.add(StudyPlanContent(study_plan_id=other.id, content_id=lessons[0].id))
    db.add(StudentStudyPlan(student_id=users["learner_b"].id, study_plan_id=other.id))
    db.commit()
    selected[0] = users["learner_b"]
    assert client.get(f"/api/content/{lessons[0].id}").status_code == 403
    assert all(
        item["id"] != lessons[0].id for item in client.get("/api/content/").json()
    )


def test_authorized_lesson_body_and_coverage_reach_tutor(scenario):
    client, db, users, selected, plan, lessons, captured = scenario
    selected[0] = users["learner_a"]
    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Explain",
            "content_id": lessons[1].id,
            "study_plan_id": plan.id,
        },
    )
    assert response.status_code == 200, response.text
    assert "SOURCE_1" in captured[0]
    assert "HIDDEN_KEY_NEVER_TUTOR" not in captured[0]
    assert response.json()["source"]["truncated"] is False
    assert response.json()["source_verified"] is False
    assert response.json()["source"]["references"]


def test_teacher_rosters_contacts_and_notes_are_scoped(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    selected[0] = users["teacher_b"]
    assert [row["id"] for row in client.get("/api/students/").json()] == [
        users["learner_b"].id
    ]
    assert (
        client.get(f'/api/students/{users["learner_a"].id}/progress').status_code == 403
    )
    assert client.get(f'/api/students/{users["learner_a"].id}/notes').status_code == 403
    assert (
        client.post(
            f'/api/students/{users["learner_a"].id}/notes', json={"notes": "not mine"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/classroom/messages",
            json={
                "recipient_id": users["learner_a"].id,
                "subject": "Denied",
                "body": "test",
            },
        ).status_code
        == 403
    )


def test_ai_settings_roundtrip_keeps_secret_private(scenario):
    client, _, users, selected, _, _, _ = scenario
    selected[0] = users["teacher_a"]
    response = client.post(
        "/api/settings/ai",
        json={
            "provider": "ollama",
            "model": "synthetic",
            "api_key": "synthetic-fixture-not-a-real-key",
            "temperature": 0.13,
            "max_tokens": 321,
            "enable_preprocessing": True,
            "preprocessing_model": "synthetic-small",
        },
    )
    assert response.status_code == 200, response.text
    data = client.get("/api/settings/ai").json()
    assert data["api_key"] is None and data["has_api_key"] is True
    assert (data["temperature"], data["max_tokens"], data["enable_preprocessing"]) == (
        0.13,
        321,
        True,
    )
    assert client.post(
        "/api/settings/ai",
        json={"provider": "ollama", "model": "synthetic", "api_key": ""},
    ).json()["has_api_key"]
    assert not client.post(
        "/api/settings/ai",
        json={"provider": "ollama", "model": "synthetic", "clear_api_key": True},
    ).json()["has_api_key"]


def test_account_creation_requires_approved_staff(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "unapproved",
            "email": "unapproved@example.com",
            "password": "SyntheticFixture123!",
            "first_name": "Synthetic",
            "last_name": "Only",
            "role": "teacher",
        },
    )
    assert response.status_code == 403


def test_password_rotation_revokes_old_token_and_survives_service_restart(
    client, db_service
):
    service = AuthService()
    user = service.register_user(
        "rotation",
        "rotation@example.test",
        "SyntheticInitial123!",
        "Synthetic",
        "Rotation",
        UserRole.TEACHER,
    )
    old = client.post(
        "/api/auth/login",
        data={"username": "rotation", "password": "SyntheticInitial123!"},
    ).json()["access_token"]
    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {old}"},
        json={
            "current_password": "SyntheticInitial123!",
            "new_password": "SyntheticRotated123!",
        },
    )
    assert response.status_code == 200, response.text
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {old}"}
        ).status_code
        == 401
    )
    assert (
        AuthService().login_user("rotation", "SyntheticRotated123!")["user"]["id"]
        == user["id"]
    )
    assert (
        client.post(
            "/api/auth/login",
            data={"username": "rotation", "password": "SyntheticInitial123!"},
        ).status_code
        == 401
    )


def test_saved_ai_key_stays_bound_to_destination_and_test_uses_runtime_secret(scenario):
    from src.api.routes.settings import _build_ai_service, AIConfigModel

    client, db, users, selected, _, _, _ = scenario
    selected[0] = users["teacher_a"]
    original = {
        "provider": "openai",
        "model": "synthetic",
        "endpoint": "https://provider.example.test/chat",
        "api_key": "synthetic-runtime-key",
    }
    assert client.post("/api/settings/ai", json=original).json()["has_api_key"]
    runtime = _build_ai_service(
        AIConfigModel(
            provider="openai", model="changed-model", endpoint=original["endpoint"]
        ),
        selected[0],
        db,
    )
    assert runtime.config.api_key == original["api_key"]
    runtime.close()
    changed = _build_ai_service(
        AIConfigModel(
            provider="openrouter", model="synthetic", endpoint=original["endpoint"]
        ),
        selected[0],
        db,
    )
    assert changed.config.api_key is None
    changed.close()
    response = client.post(
        "/api/settings/ai",
        json={
            "provider": "openai",
            "model": "synthetic",
            "endpoint": "https://different.example.test/chat",
        },
    )
    assert response.status_code == 200 and not response.json()["has_api_key"]


def test_question_answer_only_contract_is_not_lost_and_client_closes(
    scenario, monkeypatch
):
    from src.api.routes import ai

    client, _, _, _, _, _, _ = scenario
    service = MagicMock()
    service.provide_tutoring.return_value = {"answer": "A usable synthetic answer."}
    monkeypatch.setattr(ai, "get_ai_service_dependency", lambda *args: service)
    response = client.post(
        "/api/ai/answer-question", json={"question": "Explain a fraction"}
    )
    assert (
        response.json()["answer"] == "A usable synthetic answer."
        and response.json()["success"]
    )
    service.close.assert_called_once()
