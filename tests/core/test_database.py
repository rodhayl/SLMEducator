"""
Test cases for database operations
"""

import json
import pytest
from core.services.database import DatabaseService
from core.models import User, StudyPlan, Content, UserRole, ContentType
from core.exceptions import DatabaseError


class TestDatabaseService:
    """Test database service operations"""

    @pytest.fixture
    def db_service(self, test_db_path):
        """Create database service with test database"""
        return DatabaseService(str(test_db_path))

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "role": UserRole.STUDENT,
            "first_name": "Test",
            "last_name": "User",
        }

    def test_database_initialization(self, db_service):
        """Test database initialization"""
        assert db_service is not None
        assert db_service.engine is not None
        assert db_service.SessionLocal is not None

    def test_user_creation_and_retrieval(self, db_service, sample_user_data):
        """Test creating and retrieving users"""
        # Create user
        user = User(**sample_user_data)
        created_user = db_service.create_user(user)

        assert created_user is not None
        assert created_user.id is not None
        assert created_user.username == sample_user_data["username"]

        # Retrieve user by ID
        retrieved_user = db_service.get_user_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.username == created_user.username

        # Retrieve user by username
        retrieved_user = db_service.get_user_by_username(sample_user_data["username"])
        assert retrieved_user is not None
        assert retrieved_user.username == created_user.username

    def test_study_plan_creation(self, db_service, sample_user_data):
        """Test creating study plans"""
        # Create a user first (creator)
        creator = User(**sample_user_data)
        creator = db_service.create_user(creator)

        # Create study plan
        study_plan_data = {
            "title": "Test Study Plan",
            "description": "A test study plan",
            "creator_id": creator.id,
            "phases": [
                {
                    "id": 1,
                    "name": "Introduction",
                    "description": "Introduction phase",
                    "topics": [
                        {"id": 1, "name": "Topic 1", "description": "First topic"}
                    ],
                }
            ],
            "is_public": True,
        }

        study_plan = StudyPlan(**study_plan_data)
        created_plan = db_service.create_study_plan(study_plan)

        assert created_plan is not None
        assert created_plan.id is not None
        assert created_plan.title == study_plan_data["title"]
        assert created_plan.creator_id == creator.id

    def test_content_creation(self, db_service, sample_user_data):
        """Test creating content"""
        # Create creator and study plan first
        creator = User(**sample_user_data)
        creator = db_service.create_user(creator)

        study_plan = StudyPlan(
            title="Test Plan",
            description="Test description",
            creator_id=creator.id,
            phases=[],
            is_public=True,
        )
        study_plan = db_service.create_study_plan(study_plan)

        # Create content
        content_data = {
            "title": "Test Content",
            "content_type": ContentType.LESSON,
            "content_data": json.dumps({"text": "This is test content"}),
            "study_plan_id": study_plan.id,
            "difficulty": 5,
            "estimated_time_min": 30,
        }

        content = Content(**content_data)
        created_content = db_service.create_content(content)

        assert created_content is not None
        assert created_content.id is not None
        assert created_content.title == content_data["title"]
        assert created_content.study_plan_id == study_plan.id

    def test_user_study_plan_assignment(self, db_service, sample_user_data):
        """Test assigning study plans to students"""
        # Create teacher and student
        teacher_data = sample_user_data.copy()
        teacher_data["role"] = UserRole.TEACHER
        teacher = User(**teacher_data)
        teacher = db_service.create_user(teacher)

        student_data = sample_user_data.copy()
        student_data["username"] = "student"
        student_data["email"] = "student@example.com"
        student_data["role"] = UserRole.STUDENT
        student = User(**student_data)
        student = db_service.create_user(student)

        # Create study plan
        study_plan = StudyPlan(
            title="Assigned Plan",
            description="Plan for student",
            creator_id=teacher.id,
            phases=[],
            is_public=False,
        )
        study_plan = db_service.create_study_plan(study_plan)

        # Assign study plan to student
        assignment = db_service.assign_study_plan_to_student(student.id, study_plan.id)

        assert assignment is not None
        assert assignment.student_id == student.id
        assert assignment.study_plan_id == study_plan.id

    def test_learning_session_tracking(self, db_service, sample_user_data):
        """Test learning session tracking"""
        # Create student
        student_data = sample_user_data.copy()
        student_data["role"] = UserRole.STUDENT
        student = User(**student_data)
        student = db_service.create_user(student)

        # Create learning session
        from datetime import datetime
        from core.models import SessionStatus

        session_data = {
            "student_id": student.id,
            "start_time": datetime(2024, 1, 1, 10, 0, 0),
            "end_time": datetime(2024, 1, 1, 10, 30, 0),
            "score": 85,
            "status": SessionStatus.COMPLETED,
        }

        session = db_service.create_learning_session(session_data)

        assert session is not None
        assert session.student_id == student.id
        assert session.score == 85

    def test_teacher_student_messaging(self, db_service, sample_user_data):
        """Test teacher-student messaging"""
        # Create teacher and student
        teacher_data = sample_user_data.copy()
        teacher_data["role"] = UserRole.TEACHER
        teacher = User(**teacher_data)
        teacher = db_service.create_user(teacher)

        student_data = sample_user_data.copy()
        student_data["username"] = "student"
        student_data["email"] = "student@example.com"
        student_data["role"] = UserRole.STUDENT
        student = User(**student_data)
        student = db_service.create_user(student)

        # Send message from teacher to student
        message_data = {
            "from_id": teacher.id,
            "to_id": student.id,
            "subject": "Test Message",
            "content": "This is a test message",
        }

        message = db_service.create_teacher_message(message_data)

        assert message is not None
        assert message.from_id == teacher.id
        assert message.to_id == student.id
        assert message.subject == "Test Message"

    def test_audit_logging(self, db_service, sample_user_data):
        """Test audit logging"""
        # Create user
        user = User(**sample_user_data)
        user = db_service.create_user(user)

        # Create audit log entry
        from core.models import EventType

        audit_data = {
            "user_id": user.id,
            "event_type": EventType.AUTH,
            "details": {"description": "User login"},
            "ip_address": "127.0.0.1",
            "user_agent": "Test Browser",
        }

        audit_log = db_service.create_audit_log(audit_data)

        assert audit_log is not None
        assert audit_log.user_id == user.id
        assert audit_log.event_type.value == "auth"
        assert audit_log.details["description"] == "User login"

    def test_data_encryption(self, db_service, sample_user_data):
        """Test data encryption for sensitive fields"""
        # Create study plan with encrypted metadata
        creator = User(**sample_user_data)
        creator = db_service.create_user(creator)

        study_plan = StudyPlan(
            title="Encrypted Plan",
            description="Plan with encrypted metadata",
            creator_id=creator.id,
            phases=[],
            is_public=False,
        )

        # Set encrypted metadata
        metadata = {"sensitive_data": "This should be encrypted"}
        study_plan.set_encrypted_metadata(metadata)

        created_plan = db_service.create_study_plan(study_plan)

        # Retrieve and verify decryption
        retrieved_plan = db_service.get_study_plan_by_id(created_plan.id)
        decrypted_metadata = retrieved_plan.decrypted_metadata

        assert decrypted_metadata is not None
        assert decrypted_metadata["sensitive_data"] == "This should be encrypted"

    def test_error_handling(self, db_service):
        """Test database error handling"""
        # Try to create user with invalid data
        invalid_user = User(
            username=None,  # Required field
            email="invalid-email",
            password_hash="hash",
            role="invalid_role",  # Invalid role
            first_name="",
            last_name="",
        )

        with pytest.raises(DatabaseError):
            db_service.create_user(invalid_user)
