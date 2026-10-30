"""
Comprehensive settings tests for student and teacher roles.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def settings_client(db_service):
    """Create TestClient with database service."""
    from src.api.main import app
    from src.api.dependencies import get_db

    def _override_get_db():
        yield db_service.session

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


def create_user_and_login(client, role: str, username: str):
    """Register and login a user, return the token."""
    # Register
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )
    # Login
    response = client.post(
        "/api/auth/login", data={"username": username, "password": "Password123!"}
    )
    return response.json()["access_token"]


def test_student_settings_flow(settings_client):
    """Test student settings flow: profile, AI config, app config."""
    token = create_user_and_login(settings_client, "student", "student_settings")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Profile (Scenario 6.1)
    profile_data = {
        "first_name": "StudentUpdated",
        "last_name": "Settings",
        "grade_level": "11",
    }
    resp = settings_client.patch(
        "/api/auth/profile", json=profile_data, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "StudentUpdated"
    assert resp.json()["grade_level"] == "11"

    # 2. AI Config (Scenario 6.2)
    ai_config = {
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.8,
        "max_tokens": 2000,
    }
    resp = settings_client.post("/api/settings/ai", json=ai_config, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["provider"] == "ollama"

    # 3. App Config (Scenario 6.3)
    app_config = {"theme": "dark", "language": "es"}
    resp = settings_client.post("/api/settings/app", json=app_config, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["theme"] == "dark"


def test_teacher_settings_flow(settings_client):
    """Test teacher settings flow: profile, AI config."""
    token = create_user_and_login(settings_client, "teacher", "teacher_settings")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Profile
    profile_data = {"first_name": "TeacherUpdated", "last_name": "Settings"}
    resp = settings_client.patch(
        "/api/auth/profile", json=profile_data, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "TeacherUpdated"

    # 2. AI Config (Shared logic, but ensure teachers can access it too)
    ai_config = {"provider": "openai", "api_key": "sk-test-key", "model": "gpt-4"}
    resp = settings_client.post("/api/settings/ai", json=ai_config, headers=headers)
    assert resp.status_code == 200
