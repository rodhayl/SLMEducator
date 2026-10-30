"""
Tests for Guided Learning Path feature.
Tests the progress tracking API endpoints and related functionality.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

# Import models
from core.models import (
    User,
    StudyPlan,
    Content,
    StudyPlanContent,
    ContentType,
    UserRole,
)
from core.security import hash_password


class TestProgressAPIIntegration:
    """Integration tests for study plan progress tracking API."""

    @pytest.fixture
    def override_db_dependency(self, db_service):
        """
        Override FastAPI's get_db dependency to use our test database session.
        This ensures the test fixtures and API share the same database.
        """
        from src.api.main import app
        from src.api.dependencies import get_db

        def _override_get_db():
            yield db_service.session

        app.dependency_overrides[get_db] = _override_get_db
        yield
        # Cleanup
        app.dependency_overrides.clear()

    @pytest.fixture
    def api_client(self, db_service, override_db_dependency):
        """Create FastAPI test client with shared database session."""
        from src.api.main import app

        return TestClient(app)

    @pytest.fixture
    def test_teacher(self, db_service):
        """Create a test teacher user."""
        # Check if user already exists (for re-runs)
        existing = (
            db_service.session.query(User)
            .filter(User.username == "progress_test_teacher")
            .first()
        )
        if existing:
            return existing

        user = User(
            username="progress_test_teacher",
            email="progress_teacher@test.com",
            first_name="Progress",
            last_name="Teacher",
            role=UserRole.TEACHER,
            password_hash=hash_password("TestPass123!"),
        )
        db_service.session.add(user)
        db_service.session.commit()
        db_service.session.refresh(user)
        return user

    @pytest.fixture
    def test_student(self, db_service):
        """Create a test student user."""
        # Check if user already exists
        existing = (
            db_service.session.query(User)
            .filter(User.username == "progress_test_student")
            .first()
        )
        if existing:
            return existing

        user = User(
            username="progress_test_student",
            email="progress_student@test.com",
            first_name="Progress",
            last_name="Student",
            role=UserRole.STUDENT,
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
            data={"username": "progress_test_student", "password": "TestPass123!"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_study_plan(self, db_service, test_teacher):
        """Create a test study plan with content items."""
        # Create study plan
        plan = StudyPlan(
            title="Progress Test Plan",
            description="Plan for testing progress tracking",
            creator_id=test_teacher.id,
            is_public=True,  # Public so student can access
            phases=[{"name": "Phase 1", "content_ids": []}],
            created_at=datetime.now(),
        )
        db_service.session.add(plan)
        db_service.session.flush()

        # Create content items
        contents = []
        for i in range(3):
            content = Content(
                title=f"Progress Test Content {i + 1}",
                content_type=ContentType.LESSON,
                difficulty=1,
                creator_id=test_teacher.id,
                study_plan_id=plan.id,
                created_at=datetime.now(),
            )
            db_service.session.add(content)
            db_service.session.flush()
            contents.append(content)

            # Create association
            assoc = StudyPlanContent(
                study_plan_id=plan.id,
                content_id=content.id,
                phase_index=0,
                order_index=i,
            )
            db_service.session.add(assoc)

        db_service.session.commit()

        # Re-query to ensure objects are in session
        plan = (
            db_service.session.query(StudyPlan).filter(StudyPlan.id == plan.id).first()
        )
        contents = (
            db_service.session.query(Content)
            .filter(Content.study_plan_id == plan.id)
            .order_by(Content.id)
            .all()
        )

        return {"plan": plan, "contents": contents}

    def test_get_my_progress_no_existing_progress(
        self, api_client, auth_headers, test_study_plan
    ):
        """Test GET /my-progress returns defaults when no progress exists."""
        plan = test_study_plan["plan"]

        response = api_client.get(
            f"/api/study-plans/{plan.id}/my-progress", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["study_plan_id"] == plan.id
        assert data["completed_content_ids"] == []
        assert data["last_content_id"] is None
        assert data["last_phase_index"] == 0
        assert data["last_order_index"] == 0
        assert data["total_contents"] == 3
        assert data["completion_percentage"] == 0.0

    def test_update_progress_first_content(
        self, api_client, auth_headers, test_study_plan
    ):
        """Test POST /progress marks content as completed."""
        plan = test_study_plan["plan"]
        content = test_study_plan["contents"][0]

        response = api_client.post(
            f"/api/study-plans/{plan.id}/progress",
            headers=auth_headers,
            json={"completed_content_id": content.id},
        )

        assert response.status_code == 200
        data = response.json()

        assert content.id in data["completed_content_ids"]
        assert data["last_content_id"] == content.id
        assert len(data["completed_content_ids"]) == 1
        # 1/3 = 33.3%
        assert 30 <= data["completion_percentage"] <= 40

    def test_update_progress_persists(self, api_client, auth_headers, test_study_plan):
        """Test that progress persists across sessions (GET returns saved data)."""
        plan = test_study_plan["plan"]
        content = test_study_plan["contents"][0]

        # First, update progress
        api_client.post(
            f"/api/study-plans/{plan.id}/progress",
            headers=auth_headers,
            json={"completed_content_id": content.id},
        )

        # Now fetch and verify it was saved
        response = api_client.get(
            f"/api/study-plans/{plan.id}/my-progress", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert content.id in data["completed_content_ids"]
        assert data["last_content_id"] == content.id

    def test_update_progress_multiple_contents(
        self, api_client, auth_headers, test_study_plan
    ):
        """Test marking multiple contents as completed."""
        plan = test_study_plan["plan"]
        contents = test_study_plan["contents"]

        # Complete first two items
        for content in contents[:2]:
            api_client.post(
                f"/api/study-plans/{plan.id}/progress",
                headers=auth_headers,
                json={"completed_content_id": content.id},
            )

        # Verify progress
        response = api_client.get(
            f"/api/study-plans/{plan.id}/my-progress", headers=auth_headers
        )

        data = response.json()

        assert len(data["completed_content_ids"]) == 2
        # 2/3 = 66.7%
        assert 60 <= data["completion_percentage"] <= 70

    def test_update_progress_duplicate_ignored(
        self, api_client, auth_headers, test_study_plan
    ):
        """Test that completing same content twice doesn't duplicate."""
        plan = test_study_plan["plan"]
        content = test_study_plan["contents"][0]

        # Complete same content twice
        api_client.post(
            f"/api/study-plans/{plan.id}/progress",
            headers=auth_headers,
            json={"completed_content_id": content.id},
        )
        api_client.post(
            f"/api/study-plans/{plan.id}/progress",
            headers=auth_headers,
            json={"completed_content_id": content.id},
        )

        response = api_client.get(
            f"/api/study-plans/{plan.id}/my-progress", headers=auth_headers
        )

        data = response.json()

        # Should only count once
        assert len(data["completed_content_ids"]) == 1

    def test_update_progress_invalid_plan_404(self, api_client, auth_headers):
        """Test POST /progress returns 404 for non-existent plan."""
        response = api_client.post(
            "/api/study-plans/99999/progress",
            headers=auth_headers,
            json={"completed_content_id": 1},
        )

        assert response.status_code == 404

    def test_update_progress_invalid_content_404(
        self, api_client, auth_headers, test_study_plan
    ):
        """Test POST /progress returns 404 for content not in plan."""
        plan = test_study_plan["plan"]

        response = api_client.post(
            f"/api/study-plans/{plan.id}/progress",
            headers=auth_headers,
            json={"completed_content_id": 99999},  # Non-existent content
        )

        assert response.status_code == 404
