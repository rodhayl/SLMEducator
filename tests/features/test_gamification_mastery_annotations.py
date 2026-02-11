"""
Comprehensive API Tests for Gamification, Annotations, and Mastery Features

Tests the backend API functionality for:
- Phase 1: Mastery/Spaced Repetition
- Phase 2: Annotations
- Phase 3: Gamification (XP, Badges, Streaks, Daily Goals, Leaderboard)

These tests use pytest fixtures from conftest.py for database management.
"""

import pytest
from datetime import datetime, date

from src.core.models import (
    User,
    Content,
    ContentType,
    UserRole,
    MasteryNode,
    Annotation,
    HelpRequest,
    Badge,
    UserBadge,
    DailyGoal,
    LeaderboardEntry,
)


class TestGamificationModels:
    """Test Phase 3: Gamification models and database operations"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Setup test database using fixture"""
        self.db = db_service
        yield

    def _create_test_user(self, username="test_user", role=UserRole.STUDENT) -> User:
        """Create and return a test user"""
        user = User(
            username=username,
            email=f"{username}@test.com",
            role=role,
            first_name="Test",
            last_name="User",
            password_hash="hash",
            xp=0,
            level=1,
            current_streak=0,
            longest_streak=0,
        )
        self.db.session.add(user)
        self.db.session.commit()
        self.db.session.refresh(user)
        return user

    def test_user_xp_and_level(self):
        """Test XP and level tracking on User model"""
        user = self._create_test_user(username="xp_test_user")

        assert user.xp == 0
        assert user.level == 1

        # Simulate XP award
        db_user = self.db.session.query(User).filter_by(id=user.id).first()
        db_user.xp = 150
        db_user.level = 2
        self.db.session.commit()

        # Verify update
        self.db.session.refresh(db_user)
        assert db_user.xp == 150
        assert db_user.level == 2

    def test_user_streaks(self):
        """Test streak tracking on User model"""
        user = self._create_test_user(username="streak_test_user")

        assert user.current_streak == 0
        assert user.longest_streak == 0

        # Simulate streak update
        db_user = self.db.session.query(User).filter_by(id=user.id).first()
        db_user.current_streak = 5
        db_user.longest_streak = 10
        self.db.session.commit()

        # Verify update
        self.db.session.refresh(db_user)
        assert db_user.current_streak == 5
        assert db_user.longest_streak == 10

    def test_badge_creation(self):
        """Test Badge model creation"""
        import uuid

        unique_name = f"First Steps {uuid.uuid4().hex[:8]}"
        badge = Badge(
            name=unique_name,
            description="Complete your first lesson",
            icon_path="/icons/first_steps.svg",
            xp_value=10,
            criteria_type="content_complete",
            criteria_value={"lessons_completed": 1},
            is_active=True,
        )
        self.db.session.add(badge)
        self.db.session.commit()
        self.db.session.refresh(badge)

        assert badge.id is not None
        assert badge.name == unique_name
        assert badge.xp_value == 10

    def test_user_badge_award(self):
        """Test awarding badges to users"""
        user = self._create_test_user(username="badge_test_user")

        # Create badge with unique name
        import uuid

        unique_badge_name = f"Streak Master {uuid.uuid4().hex[:8]}"
        badge = Badge(
            name=unique_badge_name,
            description="Maintain a 7-day streak",
            icon_path="/icons/streak.svg",
            xp_value=50,
            criteria_type="streak",
            criteria_value={"min_streak": 7},
        )
        self.db.session.add(badge)
        self.db.session.commit()
        self.db.session.refresh(badge)

        # Award badge to user
        user_badge = UserBadge(
            user_id=user.id, badge_id=badge.id, earned_at=datetime.now(), progress=100
        )
        self.db.session.add(user_badge)
        self.db.session.commit()

        # Verify
        earned = (
            self.db.session.query(UserBadge)
            .filter_by(user_id=user.id, badge_id=badge.id)
            .first()
        )

        assert earned is not None
        assert earned.earned_at is not None
        assert earned.progress == 100

    def test_daily_goal_creation(self):
        """Test DailyGoal model creation"""
        user = self._create_test_user(username="goal_test_user")

        goal = DailyGoal(
            user_id=user.id,
            goal_date=date.today(),
            goal_type="lessons",
            target_value=5,
            current_value=2,
        )
        self.db.session.add(goal)
        self.db.session.commit()
        self.db.session.refresh(goal)

        assert goal.id is not None
        assert goal.goal_type == "lessons"
        assert goal.target_value == 5
        assert goal.current_value == 2

    def test_leaderboard_entry(self):
        """Test LeaderboardEntry model"""
        user = self._create_test_user(username="leaderboard_test_user")

        entry = LeaderboardEntry(user_id=user.id, xp=500, period="weekly", rank=1)
        self.db.session.add(entry)
        self.db.session.commit()
        self.db.session.refresh(entry)

        assert entry.id is not None
        assert entry.rank == 1
        assert entry.period == "weekly"


class TestMasteryModels:
    """Test Phase 1: Mastery/Spaced Repetition models"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Setup test database using fixture"""
        self.db = db_service
        yield

    def _create_test_user(self) -> User:
        """Create and return a test user"""
        user = User(
            username="mastery_test_user",
            email="mastery@test.com",
            role=UserRole.STUDENT,
            first_name="Test",
            last_name="User",
            password_hash="hash",
        )
        self.db.session.add(user)
        self.db.session.commit()
        self.db.session.refresh(user)
        return user

    def _create_test_content(self) -> Content:
        """Create and return test content"""
        content = Content(
            content_type=ContentType.LESSON,
            title="Test Lesson",
            content_data="Test content data",
            difficulty=2,
            estimated_time_min=15,
        )
        self.db.session.add(content)
        self.db.session.commit()
        self.db.session.refresh(content)
        return content

    def test_mastery_node_creation(self):
        """Test MasteryNode model creation for spaced repetition"""
        user = self._create_test_user()
        content = self._create_test_content()

        mastery = MasteryNode(
            student_id=user.id,
            content_id=content.id,
            mastery_level=50,
            review_count=3,
            last_reviewed=datetime.now(),
            next_review_due=datetime.now(),
        )
        self.db.session.add(mastery)
        self.db.session.commit()
        self.db.session.refresh(mastery)

        assert mastery.id is not None
        assert mastery.mastery_level == 50
        assert mastery.review_count == 3

    def test_mastery_level_update(self):
        """Test updating mastery level after review"""
        user = self._create_test_user()
        content = self._create_test_content()

        mastery = MasteryNode(
            student_id=user.id, content_id=content.id, mastery_level=30, review_count=1
        )
        self.db.session.add(mastery)
        self.db.session.commit()

        # Simulate successful review
        mastery.mastery_level = 50
        mastery.review_count = 2
        mastery.last_reviewed = datetime.now()
        self.db.session.commit()
        self.db.session.refresh(mastery)

        assert mastery.mastery_level == 50
        assert mastery.review_count == 2


class TestAnnotationModels:
    """Test Phase 2: Annotation models"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Setup test database using fixture"""
        self.db = db_service
        yield

    def _create_test_user(self) -> User:
        """Create and return a test user"""
        user = User(
            username="annotation_test_user",
            email="annotation@test.com",
            role=UserRole.STUDENT,
            first_name="Test",
            last_name="User",
            password_hash="hash",
        )
        self.db.session.add(user)
        self.db.session.commit()
        self.db.session.refresh(user)
        return user

    def _create_test_content(self) -> Content:
        """Create and return test content"""
        content = Content(
            content_type=ContentType.LESSON,
            title="Test Lesson for Annotations",
            content_data="Test content data",
            difficulty=2,
            estimated_time_min=15,
        )
        self.db.session.add(content)
        self.db.session.commit()
        self.db.session.refresh(content)
        return content

    def test_annotation_creation(self):
        """Test creating an annotation on content"""
        user = self._create_test_user()
        content = self._create_test_content()

        annotation = Annotation(
            content_id=content.id,
            user_id=user.id,
            annotation_text="This is a great explanation!",
            annotation_type="comment",
            is_public=True,
        )
        self.db.session.add(annotation)
        self.db.session.commit()
        self.db.session.refresh(annotation)

        assert annotation.id is not None
        assert annotation.annotation_text == "This is a great explanation!"
        assert annotation.annotation_type == "comment"
        assert annotation.is_public is True

    def test_annotation_types(self):
        """Test different annotation types"""
        user = self._create_test_user()
        content = self._create_test_content()

        annotation_types = ["comment", "question", "highlight"]

        for ann_type in annotation_types:
            annotation = Annotation(
                content_id=content.id,
                user_id=user.id,
                annotation_text=f"Test {ann_type}",
                annotation_type=ann_type,
                is_public=True,
            )
            self.db.session.add(annotation)

        self.db.session.commit()

        # Verify all types were created
        annotations = (
            self.db.session.query(Annotation).filter_by(content_id=content.id).all()
        )

        assert len(annotations) == 3
        types_created = {a.annotation_type for a in annotations}
        assert types_created == set(annotation_types)

    def test_private_annotation(self):
        """Test private annotations are only visible to owner"""
        user = self._create_test_user()
        content = self._create_test_content()

        annotation = Annotation(
            content_id=content.id,
            user_id=user.id,
            annotation_text="Private note to myself",
            annotation_type="note",
            is_public=False,
        )
        self.db.session.add(annotation)
        self.db.session.commit()
        self.db.session.refresh(annotation)

        assert annotation.is_public is False

        # Query for public annotations only
        public_annotations = (
            self.db.session.query(Annotation)
            .filter_by(content_id=content.id, is_public=True)
            .all()
        )

        assert len(public_annotations) == 0


class TestHelpRequestModels:
    """Test Phase 2: Help Queue models"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Setup test database using fixture"""
        self.db = db_service
        yield

    def _create_test_users(self):
        """Create student and teacher users"""
        student = User(
            username="help_student",
            email="student@test.com",
            role=UserRole.STUDENT,
            first_name="Test",
            last_name="Student",
            password_hash="hash",
        )
        self.db.session.add(student)
        self.db.session.commit()
        self.db.session.refresh(student)

        teacher = User(
            username="help_teacher",
            email="teacher@test.com",
            role=UserRole.TEACHER,
            first_name="Test",
            last_name="Teacher",
            password_hash="hash",
        )
        self.db.session.add(teacher)
        self.db.session.commit()
        self.db.session.refresh(teacher)

        return student, teacher

    def test_help_request_creation(self):
        """Test creating a help request"""
        student, teacher = self._create_test_users()

        request = HelpRequest(
            student_id=student.id,
            request_text="I need help with this concept",
            priority=2,
            status="pending",
        )
        self.db.session.add(request)
        self.db.session.commit()
        self.db.session.refresh(request)

        assert request.id is not None
        assert request.status == "pending"
        assert request.student_id == student.id

    def test_help_request_resolution(self):
        """Test resolving a help request"""
        student, teacher = self._create_test_users()

        request = HelpRequest(
            student_id=student.id,
            request_text="Help needed",
            priority=4,
            status="pending",
        )
        self.db.session.add(request)
        self.db.session.commit()

        # Teacher resolves the request
        request.status = "resolved"
        request.resolved_by_id = teacher.id
        request.resolution_notes = "Explained the concept in detail"
        request.resolved_at = datetime.now()
        self.db.session.commit()
        self.db.session.refresh(request)

        assert request.status == "resolved"
        assert request.resolved_by_id == teacher.id
        assert request.resolution_notes is not None


class TestIntegration:
    """Integration tests for combined features"""

    @pytest.fixture(autouse=True)
    def setup(self, db_service):
        """Setup test database using fixture"""
        self.db = db_service
        yield

    def test_complete_learning_flow(self):
        """Test a complete learning flow with gamification"""
        # Create student
        student = User(
            username="learning_student",
            email="learner@test.com",
            role=UserRole.STUDENT,
            first_name="Eager",
            last_name="Learner",
            password_hash="hash",
            xp=0,
            level=1,
        )
        self.db.session.add(student)
        self.db.session.commit()
        self.db.session.refresh(student)

        # Create content
        content = Content(
            content_type=ContentType.LESSON,
            title="Introduction to Python",
            content_data="Learn Python basics",
            difficulty=1,
            estimated_time_min=30,
        )
        self.db.session.add(content)
        self.db.session.commit()
        self.db.session.refresh(content)

        # Student starts learning - create mastery node
        mastery = MasteryNode(
            student_id=student.id,
            content_id=content.id,
            mastery_level=0,
            review_count=0,
        )
        self.db.session.add(mastery)
        self.db.session.commit()

        # Student completes lesson - update mastery and award XP
        mastery.mastery_level = 50
        mastery.review_count = 1
        mastery.last_reviewed = datetime.now()

        db_student = self.db.session.query(User).filter_by(id=student.id).first()
        db_student.xp += 10  # Award XP for completion

        self.db.session.commit()

        # Verify final state
        self.db.session.refresh(mastery)
        self.db.session.refresh(db_student)

        assert mastery.mastery_level == 50
        assert db_student.xp == 10

        # Student adds annotation
        annotation = Annotation(
            content_id=content.id,
            user_id=student.id,
            annotation_text="This was really helpful!",
            annotation_type="comment",
            is_public=True,
        )
        self.db.session.add(annotation)
        self.db.session.commit()

        # Verify annotation exists
        annotations = (
            self.db.session.query(Annotation).filter_by(content_id=content.id).all()
        )
        assert len(annotations) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
