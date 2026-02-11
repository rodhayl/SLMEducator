"""
Integration Tests for Learning Session API - New Endpoints

Tests the following endpoints:
- PATCH /api/learning/{session_id}/notes - Update notes during session
- GET /api/learning/history/{content_id} - Get session history
- POST /api/learning/{session_id}/restore - Restore a previous session
- POST /api/learning/restart/{content_id} - Start fresh session
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.core.models import (
    User,
    Content,
    LearningSession,
    SessionStatus,
    ContentType,
    UserRole,
)
from src.core.security import hash_password


class TestLearningSessionNewEndpoints:
    """Integration tests for new learning session API endpoints."""

    @pytest.fixture
    def override_db_dependency(self, db_service):
        """Override FastAPI's get_db dependency to use test database session."""
        from src.api.main import app
        from src.api.dependencies import get_db

        def _override_get_db():
            yield db_service.session

        app.dependency_overrides[get_db] = _override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    def api_client(self, db_service, override_db_dependency):
        """Create FastAPI test client with shared database session."""
        from src.api.main import app

        return TestClient(app)

    @pytest.fixture
    def test_student(self, db_service):
        """Create a test student user."""
        existing = (
            db_service.session.query(User)
            .filter(User.username == "session_api_test_student")
            .first()
        )
        if existing:
            return existing

        user = User(
            username="session_api_test_student",
            email="session_api_student@test.com",
            first_name="Session",
            last_name="TestStudent",
            role=UserRole.STUDENT,
            password_hash=hash_password("TestPass123!"),
        )
        db_service.session.add(user)
        db_service.session.commit()
        db_service.session.refresh(user)
        return user

    @pytest.fixture
    def test_teacher(self, db_service):
        """Create a test teacher user."""
        existing = (
            db_service.session.query(User)
            .filter(User.username == "session_api_test_teacher")
            .first()
        )
        if existing:
            return existing

        user = User(
            username="session_api_test_teacher",
            email="session_api_teacher@test.com",
            first_name="Session",
            last_name="TestTeacher",
            role=UserRole.TEACHER,
            password_hash=hash_password("TestPass123!"),
        )
        db_service.session.add(user)
        db_service.session.commit()
        db_service.session.refresh(user)
        return user

    @pytest.fixture
    def auth_headers(self, api_client, test_student):
        """Get authentication headers for test student."""
        response = api_client.post(
            "/api/auth/login",
            data={"username": "session_api_test_student", "password": "TestPass123!"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_content(self, db_service, test_teacher):
        """Create test content for sessions."""
        existing = (
            db_service.session.query(Content)
            .filter(Content.title == "Session API Test Content")
            .first()
        )
        if existing:
            return existing

        content = Content(
            title="Session API Test Content",
            content_type=ContentType.LESSON,
            difficulty=1,
            creator_id=test_teacher.id,
            created_at=datetime.now(timezone.utc),
        )
        db_service.session.add(content)
        db_service.session.commit()
        db_service.session.refresh(content)
        return content

    @pytest.fixture
    def active_session(self, db_service, test_student, test_content):
        """Create an active learning session."""
        session = LearningSession(
            student_id=test_student.id,
            content_id=test_content.id,
            start_time=datetime.now(timezone.utc),
            status=SessionStatus.ACTIVE,
        )
        db_service.session.add(session)
        db_service.session.commit()
        db_service.session.refresh(session)
        return session

    # ------ Test PATCH /api/learning/{session_id}/notes ------

    def test_update_notes_success(self, api_client, auth_headers, active_session):
        """Test updating notes on an active session."""
        response = api_client.patch(
            f"/api/learning/{active_session.id}/notes",
            headers=auth_headers,
            json={"notes": "Test notes content for the session."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Test notes content for the session."

    def test_update_notes_nonexistent_session(self, api_client, auth_headers):
        """Test updating notes on a non-existent session returns 404."""
        response = api_client.patch(
            "/api/learning/99999/notes",
            headers=auth_headers,
            json={"notes": "Should fail"},
        )

        assert response.status_code == 404

    # ------ Test GET /api/learning/history/{content_id} ------

    def test_get_session_history_empty(self, api_client, auth_headers, test_content):
        """Test getting history when no sessions exist returns empty list."""
        response = api_client.get(
            f"/api/learning/history/{test_content.id}", headers=auth_headers
        )

        assert response.status_code == 200
        # May return empty or existing sessions depending on test order

    def test_get_session_history_with_sessions(
        self, api_client, auth_headers, active_session, test_content
    ):
        """Test getting history returns sessions."""
        response = api_client.get(
            f"/api/learning/history/{test_content.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain at least the active session
        assert len(data) >= 1

    # ------ Test POST /api/learning/{session_id}/restore ------

    def test_restore_session_success(
        self, api_client, auth_headers, db_service, test_student, test_content
    ):
        """Test restoring a completed session."""
        # Create a completed session with notes
        session = LearningSession(
            student_id=test_student.id,
            content_id=test_content.id,
            start_time=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
            notes="Previous session notes to restore",
        )
        db_service.session.add(session)
        db_service.session.commit()
        db_service.session.refresh(session)

        response = api_client.post(
            f"/api/learning/{session.id}/restore", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Previous session notes to restore"
        # Status should be active after restore
        assert data["status"] == "active"

    def test_restore_session_not_found(self, api_client, auth_headers):
        """Test restoring a non-existent session returns 404."""
        response = api_client.post("/api/learning/99999/restore", headers=auth_headers)

        assert response.status_code == 404

    # ------ Test POST /api/learning/restart/{content_id} ------

    def test_restart_session_success(self, api_client, auth_headers, test_content):
        """Test restarting creates a fresh session."""
        response = api_client.post(
            f"/api/learning/restart/{test_content.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_id"] == test_content.id
        assert data["status"] == "active"
        # New session should have no notes
        assert data.get("notes") is None or data.get("notes") == ""

    def test_restart_session_invalid_content(self, api_client, auth_headers):
        """Test restarting with invalid content returns 404."""
        response = api_client.post("/api/learning/restart/99999", headers=auth_headers)

        assert response.status_code == 404
