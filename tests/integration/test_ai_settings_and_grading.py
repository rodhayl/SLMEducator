import os
import sys
import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import assessment as assessment_routes

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

client = TestClient(app)


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register_user(username: str, role: str):
    """Provision synthetic approved fixtures; registration policy has dedicated tests."""
    from src.core.models import User, UserRole
    from src.core.services.auth import AuthService
    from src.core.services.database import get_db_service
    teacher_id = None
    if role == "student":
        with get_db_service().get_session() as db:
            teacher = db.query(User).filter(User.role == UserRole.TEACHER).one_or_none()
            teacher_id = teacher.id if teacher else None
    return AuthService().register_user(username, f"{username}@example.com", "Password123!", "Test", "User", UserRole(role), teacher_id=teacher_id)


def _login_user(username: str, password: str = "Password123!") -> str:
    resp = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_ai_config_preserves_api_key_when_omitted():
    username = _unique_username("settings")
    _register_user(username, "teacher")
    token = _login_user(username)

    initial = client.post(
        "/api/settings/ai",
        json={
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-test-key",
            "temperature": 0.7,
            "max_tokens": 800,
        },
        headers=_auth_headers(token),
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["api_key"] is None
    assert initial.json()["has_api_key"] is True

    update = client.post(
        "/api/settings/ai",
        json={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.6,
            "max_tokens": 600,
        },
        headers=_auth_headers(token),
    )
    assert update.status_code == 200, update.text
    assert update.json()["api_key"] is None
    assert update.json()["has_api_key"] is True


def test_unsaved_ai_settings_match_actual_transport(monkeypatch):
    from src.api import dependencies

    username = _unique_username("defaults")
    _register_user(username, "teacher")
    headers = _auth_headers(_login_user(username))
    defaults = {("ai", "default_provider"): "lm_studio",
                ("ai", "default_model"): "synthetic-instruct",
                ("ai", "lm_studio.url"): "http://127.0.0.1:1234"}
    settings = Mock()
    settings.get.side_effect = lambda section, key, default=None: defaults.get((section, key), default)
    monkeypatch.setattr(dependencies, "get_settings_service", lambda: settings)
    receipt = client.get("/api/settings/ai", headers=headers)
    assert receipt.status_code == 200
    captured = []
    monkeypatch.setattr(dependencies, "AIService", lambda runtime, logger: captured.append(runtime))
    from src.core.services.database import get_db_service
    from src.core.models import User
    with get_db_service().get_session() as db:
        user = db.query(User).filter(User.username == username).one()
        dependencies.get_ai_service_dependency(user, db)
    runtime = captured[0]
    for field in ("provider", "model", "endpoint", "temperature", "max_tokens"):
        assert receipt.json()[field] == getattr(runtime, field)


def test_ai_assisted_submission_creates_ai_graded(monkeypatch):
    teacher_username = _unique_username("teacher")
    student_username = _unique_username("student")
    _register_user(teacher_username, "teacher")
    _register_user(student_username, "student")

    teacher_token = _login_user(teacher_username)
    student_token = _login_user(student_username)

    assessment_resp = client.post(
        "/api/assessments/",
        json={
            "title": "AI Assisted Quiz",
            "description": "Subjective grading test",
            "passing_score": 70,
            "grading_mode": "ai_assisted",
            "questions": [
                {
                    "question_text": "Explain the water cycle.",
                    "question_type": "short_answer",
                    "points": 10,
                }
            ],
        },
        headers=_auth_headers(teacher_token),
    )
    assert assessment_resp.status_code == 200, assessment_resp.text
    assessment_id = assessment_resp.json()["id"]

    published = client.post(f"/api/assessments/{assessment_id}/publish", headers=_auth_headers(teacher_token))
    assert published.status_code == 200, published.text

    assessment_detail = client.get(
        f"/api/assessments/{assessment_id}",
        headers=_auth_headers(student_token),
    )
    assert assessment_detail.status_code == 200, assessment_detail.text
    question_id = assessment_detail.json()["questions"][0]["id"]

    mock_ai = Mock()
    mock_ai.grade_answer.return_value = {
        "points_earned": 7,
        "max_points": 10,
        "percentage": 70,
        "feedback": "Good coverage of key steps.",
    }
    mock_ai.close = Mock()

    monkeypatch.setattr(
        assessment_routes,
        "get_ai_service_dependency",
        lambda user, db: mock_ai,
    )

    submit_resp = client.post(
        f"/api/assessments/{assessment_id}/submit",
        json={
            "answers": [
                {"question_id": question_id, "response_text": "Evaporation and rain."}
            ]
        },
        headers=_auth_headers(student_token),
    )
    assert submit_resp.status_code == 200, submit_resp.text
    submit_data = submit_resp.json()
    assert submit_data["status"] == "ai_graded"
    assert submit_data["ai_graded_questions"] == 1

    list_resp = client.get(
        "/api/assessments/submissions?status=ai_graded",
        headers=_auth_headers(teacher_token),
    )
    assert list_resp.status_code == 200, list_resp.text
    submissions = list_resp.json()
    assert submissions, "Expected at least one AI graded submission"

    submission_id = submissions[0]["id"]
    detail_resp = client.get(
        f"/api/assessments/submissions/{submission_id}",
        headers=_auth_headers(teacher_token),
    )
    assert detail_resp.status_code == 200, detail_resp.text
    details = detail_resp.json()
    assert details["answers"][0]["ai_suggested_score"] == 7
    assert (
        details["answers"][0]["ai_suggested_feedback"] == "Good coverage of key steps."
    )

    mock_ai.close.assert_called_once()
