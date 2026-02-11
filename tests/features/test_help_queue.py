"""
Comprehensive Tests for Help Queue API

Tests all help queue enhancement features:
- Creating help requests with learning context
- Getting help requests (teacher sees all, student sees own)
- Resolving help requests (teacher only)
- Context capture (content, study plan, question)
- Response schema with full context information
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


from core.models import User, HelpRequest, Content, ContentType, StudyPlan


class TestHelpQueueAPI:
    """Test suite for help queue endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_teacher: User, test_student: User):
        """Set up test data for each test."""
        self.db = db_session
        self.teacher = test_teacher
        self.student = test_student

        # Create test content for context testing
        self.test_content = Content(
            title="Test Math Lesson",
            content_type=ContentType.LESSON,
            content_data='{"body": "This is a test lesson about mathematics."}',
            difficulty=2,
            creator_id=self.teacher.id,
        )
        self.db.add(self.test_content)
        self.db.commit()
        self.db.refresh(self.test_content)

        # Create test study plan for context testing
        self.test_study_plan = StudyPlan(
            title="Math Basics Study Plan",
            description="A beginner's guide to math",
            creator_id=self.teacher.id,
        )
        self.db.add(self.test_study_plan)
        self.db.commit()
        self.db.refresh(self.test_study_plan)

        # Create a basic help request
        self.basic_request = HelpRequest(
            student_id=self.student.id,
            request_text="Test Subject: I need help with this topic",
            priority=2,
            status="open",
            created_at=datetime.now(),
        )
        self.db.add(self.basic_request)
        self.db.commit()
        self.db.refresh(self.basic_request)

        # Create a help request with full context
        self.context_request = HelpRequest(
            student_id=self.student.id,
            request_text="Context Subject: I don't understand this part",
            priority=3,
            status="open",
            content_id=self.test_content.id,
            study_plan_id=self.test_study_plan.id,
            created_at=datetime.now(),
        )
        self.db.add(self.context_request)
        self.db.commit()
        self.db.refresh(self.context_request)

    # --- CREATE HELP REQUEST TESTS ---

    def test_create_help_request_basic(self, client: TestClient, student_token: str):
        """Test creating a basic help request without context."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Need Help",
                "description": "I'm stuck on this problem",
                "urgency": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["student_id"] == self.student.id
        assert "Need Help" in data["request_text"]
        assert data["status"] in ["open", "pending"]
        assert "created_at" in data
        assert data["student_name"] is not None

    def test_create_help_request_with_content_context(
        self, client: TestClient, student_token: str
    ):
        """Test creating a help request with content context."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Help with Lesson",
                "description": "I don't understand step 3",
                "urgency": 2,
                "content_id": self.test_content.id,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["content_id"] == self.test_content.id
        assert data["content_title"] == "Test Math Lesson"
        assert data["content_type"] in ["lesson", "Lesson", "LESSON"]

    def test_create_help_request_with_study_plan_context(
        self, client: TestClient, student_token: str
    ):
        """Test creating a help request with study plan context."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Study Plan Question",
                "description": "Which section should I do next?",
                "urgency": 1,
                "study_plan_id": self.test_study_plan.id,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["study_plan_id"] == self.test_study_plan.id
        assert data["study_plan_title"] == "Math Basics Study Plan"

    def test_create_help_request_with_full_context(
        self, client: TestClient, student_token: str
    ):
        """Test creating a help request with all context fields."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Comprehensive Help",
                "description": "I need detailed assistance",
                "urgency": 3,
                "content_id": self.test_content.id,
                "study_plan_id": self.test_study_plan.id,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all context is captured
        assert data["content_id"] == self.test_content.id
        assert data["content_title"] == "Test Math Lesson"
        assert data["study_plan_id"] == self.test_study_plan.id
        assert data["study_plan_title"] == "Math Basics Study Plan"
        assert data["priority"] == 3

    def test_create_help_request_invalid_content_id(
        self, client: TestClient, student_token: str
    ):
        """Test creating a help request with non-existent content ID."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Help",
                "description": "Test",
                "urgency": 1,
                "content_id": 99999,  # Non-existent
            },
        )
        # Should still succeed but content_title will be None
        assert response.status_code == 200
        data = response.json()
        assert data["content_title"] is None

    # --- GET HELP REQUESTS TESTS ---

    def test_teacher_sees_all_requests(self, client: TestClient, teacher_token: str):
        """Test that teacher sees all help requests."""
        response = client.get(
            "/api/classroom/help", headers={"Authorization": f"Bearer {teacher_token}"}
        )
        assert response.status_code == 200
        requests = response.json()

        # Teacher should see both test requests
        assert len(requests) >= 2

        # Verify context is included in response
        ids = [r["id"] for r in requests]
        assert self.context_request.id in ids

        context_req = next(r for r in requests if r["id"] == self.context_request.id)
        assert context_req["content_title"] == "Test Math Lesson"
        assert context_req["study_plan_title"] == "Math Basics Study Plan"

    def test_student_sees_only_own_requests(
        self, client: TestClient, student_token: str
    ):
        """Test that student only sees their own requests."""
        response = client.get(
            "/api/classroom/help", headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        requests = response.json()

        # Student should only see their own requests
        for req in requests:
            assert req["student_id"] == self.student.id

    def test_help_request_response_includes_student_name(
        self, client: TestClient, teacher_token: str
    ):
        """Test that response includes student name for teacher view."""
        response = client.get(
            "/api/classroom/help", headers={"Authorization": f"Bearer {teacher_token}"}
        )
        assert response.status_code == 200
        requests = response.json()

        assert len(requests) > 0
        for req in requests:
            assert "student_name" in req
            assert req["student_name"] is not None

    def test_help_request_response_includes_subject(
        self, client: TestClient, teacher_token: str
    ):
        """Test that subject is parsed from request_text."""
        response = client.get(
            "/api/classroom/help", headers={"Authorization": f"Bearer {teacher_token}"}
        )
        assert response.status_code == 200
        requests = response.json()

        # Find our basic request
        basic_req = next(
            (r for r in requests if r["id"] == self.basic_request.id), None
        )
        if basic_req:
            assert "subject" in basic_req
            # Subject should be extracted from "Test Subject: I need help..."
            assert basic_req["subject"] == "Test Subject"

    # --- RESOLVE HELP REQUEST TESTS ---

    def test_teacher_can_resolve_request(self, client: TestClient, teacher_token: str):
        """Test that teacher can resolve a help request."""
        # Note: resolve endpoint accepts notes as query param, not JSON body
        response = client.post(
            f"/api/classroom/help/{self.basic_request.id}/resolve?notes=Issue%20resolved%20via%20direct%20message",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "resolved"
        assert "resolved_at" in data

        # Verify in database
        self.db.refresh(self.basic_request)
        assert self.basic_request.status == "resolved"
        assert self.basic_request.resolved_by_id == self.teacher.id
        assert (
            self.basic_request.resolution_notes == "Issue resolved via direct message"
        )

    def test_student_cannot_resolve_request(
        self, client: TestClient, student_token: str
    ):
        """Test that student cannot resolve help requests."""
        response = client.post(
            f"/api/classroom/help/{self.basic_request.id}/resolve",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 403

    def test_resolve_nonexistent_request(self, client: TestClient, teacher_token: str):
        """Test resolving a request that doesn't exist."""
        response = client.post(
            "/api/classroom/help/99999/resolve",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 404

    def test_resolve_without_notes(self, client: TestClient, teacher_token: str):
        """Test resolving a request without notes."""
        response = client.post(
            f"/api/classroom/help/{self.context_request.id}/resolve",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code in [
            200,
            422,
        ]  # 422 if notes required, 200 if optional

    # --- AUTHORIZATION TESTS ---

    def test_unauthenticated_cannot_access(self, client: TestClient):
        """Test that unauthenticated users cannot access help queue."""
        response = client.get("/api/classroom/help")
        assert response.status_code == 401

    def test_unauthenticated_cannot_create(self, client: TestClient):
        """Test that unauthenticated users cannot create requests."""
        response = client.post(
            "/api/classroom/help",
            json={"subject": "Test", "description": "Test", "urgency": 1},
        )
        assert response.status_code == 401


class TestHelpQueueContextCapture:
    """Tests specifically for learning context capture functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_teacher: User, test_student: User):
        """Set up test data."""
        self.db = db_session
        self.teacher = test_teacher
        self.student = test_student

        # Create content types for testing
        self.lesson = Content(
            title="Algebra Basics",
            content_type=ContentType.LESSON,
            content_data='{"body": "Introduction to algebra"}',
            difficulty=1,
            creator_id=self.teacher.id,
        )
        self.exercise = Content(
            title="Practice Problems",
            content_type=ContentType.EXERCISE,
            content_data='{"exercises": []}',
            difficulty=2,
            creator_id=self.teacher.id,
        )
        self.assessment = Content(
            title="Chapter Test",
            content_type=ContentType.ASSESSMENT,
            content_data='{"questions": []}',
            difficulty=3,
            creator_id=self.teacher.id,
        )
        self.db.add_all([self.lesson, self.exercise, self.assessment])
        self.db.commit()
        self.db.refresh(self.lesson)
        self.db.refresh(self.exercise)
        self.db.refresh(self.assessment)

    def test_context_captures_lesson_type(self, client: TestClient, student_token: str):
        """Test that lesson content type is captured correctly."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Lesson Help",
                "description": "Need help with lesson",
                "urgency": 1,
                "content_id": self.lesson.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"].lower() == "lesson"

    def test_context_captures_exercise_type(
        self, client: TestClient, student_token: str
    ):
        """Test that exercise content type is captured correctly."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Exercise Help",
                "description": "Stuck on exercise",
                "urgency": 2,
                "content_id": self.exercise.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"].lower() == "exercise"

    def test_context_captures_assessment_type(
        self, client: TestClient, student_token: str
    ):
        """Test that assessment content type is captured correctly."""
        response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Assessment Help",
                "description": "Question about test",
                "urgency": 3,
                "content_id": self.assessment.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"].lower() == "assessment"

    def test_context_returned_in_get(
        self, client: TestClient, student_token: str, teacher_token: str
    ):
        """Test that context is returned when getting help requests."""
        # Create request with context
        create_response = client.post(
            "/api/classroom/help",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject": "Get Test",
                "description": "Testing get",
                "urgency": 1,
                "content_id": self.lesson.id,
            },
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        # Get as teacher
        get_response = client.get(
            "/api/classroom/help", headers={"Authorization": f"Bearer {teacher_token}"}
        )
        assert get_response.status_code == 200
        requests = get_response.json()

        # Find our request
        our_request = next((r for r in requests if r["id"] == created_id), None)
        assert our_request is not None
        assert our_request["content_id"] == self.lesson.id
        assert our_request["content_title"] == "Algebra Basics"
        assert our_request["content_type"].lower() == "lesson"
