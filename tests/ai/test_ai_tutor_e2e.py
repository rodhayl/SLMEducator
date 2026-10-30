"""
End-to-End tests for AI Tutor with Study Plan, Topic, and Content selection.

These tests use EXACTLY the same code path as the GUI without opening any GUI.
They test the complete flow:
1. Creating study plans with phases/topics
2. Adding content to specific phases
3. Selecting study plan, topic, and content
4. Sending messages to AI with full context
5. Receiving AI responses

Uses configurable AI provider from env-test.properties (LM Studio by default).
"""

import pytest
import os
import sys
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.services.database import DatabaseService
from core.services.ai_service import AIService
from core.models import (
    User,
    StudyPlan,
    Content,
    ContentType,
    UserRole,
    AIModelConfiguration,
    StudentStudyPlan,
)
from core.security import hash_password

# Import AI configuration utilities from the test package conftest.
# NOTE: Explicit import avoids accidentally resolving to tests/e2e/conftest.py.
from tests.conftest import (
    is_configured_ai_available,
    get_configured_ai_model,
    get_configured_ai_provider,
    get_settings_service,
)


class TestAITutorE2EWithOllama:
    """
    End-to-end tests for AI Tutor using the same code path as the GUI.

    These tests verify:
    - Study plan selection with phases/topics
    - Topic (phase) selection within a study plan
    - Content selection within a topic
    - AI tutoring with full context (plan + topic + content)
    """

    @pytest.fixture(scope="class")
    def db_service(self):
        """Create test database"""
        os.environ["SLM_TEST_MODE"] = "1"
        db = DatabaseService(":memory:")
        yield db
        db.close()

    @pytest.fixture
    def test_teacher(self, db_service):
        """Create a test teacher user"""
        user = User(
            username=f"test_teacher_{datetime.now().timestamp()}",
            password_hash=hash_password("testpass123"),
            email=f"teacher_{datetime.now().timestamp()}@test.com",
            role=UserRole.TEACHER,
            first_name="Test",
            last_name="Teacher",
        )
        return db_service.create_user(user)

    @pytest.fixture
    def test_student(self, db_service):
        """Create a test student user"""
        user = User(
            username=f"test_student_{datetime.now().timestamp()}",
            password_hash=hash_password("testpass123"),
            email=f"student_{datetime.now().timestamp()}@test.com",
            role=UserRole.STUDENT,
            first_name="Test",
            last_name="Student",
            grade_level="10",
        )
        return db_service.create_user(user)

    @pytest.fixture
    def test_study_plan_with_content(self, db_service, test_teacher, test_student):
        """Create a comprehensive study plan with phases and content"""
        # Create study plan with multiple phases (topics)
        plan = StudyPlan(
            title="Python Programming Fundamentals",
            description="A comprehensive course to learn Python programming from scratch",
            creator_id=test_teacher.id,
            phases=[
                {
                    "name": "Introduction to Python",
                    "title": "Introduction to Python",  # Support both keys
                    "objectives": [
                        "Understand what Python is and its applications",
                        "Set up Python development environment",
                        "Write and run your first Python program",
                        "Learn basic syntax and comments",
                    ],
                },
                {
                    "name": "Variables and Data Types",
                    "title": "Variables and Data Types",
                    "objectives": [
                        "Understand variables and naming conventions",
                        "Learn about integers, floats, and strings",
                        "Work with lists and dictionaries",
                        "Perform type conversions",
                    ],
                },
                {
                    "name": "Control Flow",
                    "title": "Control Flow",
                    "objectives": [
                        "Master if/else/elif statements",
                        "Understand while loops",
                        "Use for loops effectively",
                        "Learn break, continue, and pass",
                    ],
                },
            ],
        )
        created_plan = db_service.create_study_plan(plan)

        # Create content for Phase 0 (Introduction)
        intro_lesson = Content(
            creator_id=test_teacher.id,
            content_type=ContentType.LESSON,
            title="What is Python?",
            content_data="Python is a high-level, interpreted programming language known for its simplicity.",
            difficulty=1,
            estimated_time_min=15,
        )
        intro_lesson = db_service.create_content(intro_lesson)
        db_service.add_content_to_plan(
            created_plan.id, intro_lesson.id, phase_index=0, order_index=0
        )

        # Create content for Phase 1 (Variables)
        variables_lesson = Content(
            creator_id=test_teacher.id,
            content_type=ContentType.LESSON,
            title="Understanding Variables",
            content_data="Variables are containers for storing data values. In Python, you create variables by assigning values.",
            difficulty=2,
            estimated_time_min=20,
        )
        variables_lesson = db_service.create_content(variables_lesson)
        db_service.add_content_to_plan(
            created_plan.id, variables_lesson.id, phase_index=1, order_index=0
        )

        variables_exercise = Content(
            creator_id=test_teacher.id,
            content_type=ContentType.EXERCISE,
            title="Variable Practice",
            content_data="Practice creating and using variables in Python.",
            difficulty=2,
            estimated_time_min=30,
        )
        variables_exercise = db_service.create_content(variables_exercise)
        db_service.add_content_to_plan(
            created_plan.id, variables_exercise.id, phase_index=1, order_index=1
        )

        # Create content for Phase 2 (Control Flow)
        loops_lesson = Content(
            creator_id=test_teacher.id,
            content_type=ContentType.LESSON,
            title="Loops in Python",
            content_data="Learn about for loops and while loops to repeat code execution.",
            difficulty=3,
            estimated_time_min=25,
        )
        loops_lesson = db_service.create_content(loops_lesson)
        db_service.add_content_to_plan(
            created_plan.id, loops_lesson.id, phase_index=2, order_index=0
        )

        # Assign plan to student
        assignment = StudentStudyPlan(
            student_id=test_student.id,
            study_plan_id=created_plan.id,
            assigned_at=datetime.now(),
        )
        db_service.create_student_study_plan(assignment)

        return {
            "plan": created_plan,
            "contents": {
                "intro_lesson": intro_lesson,
                "variables_lesson": variables_lesson,
                "variables_exercise": variables_exercise,
                "loops_lesson": loops_lesson,
            },
        }

    @pytest.fixture
    def ollama_ai_service(self):
        """
        Get real AI service configured from env-test.properties.

        NOTE: Named 'ollama_ai_service' for backward compatibility but now
        uses the configured provider from env-test.properties (LM Studio by default).
        """
        if not is_configured_ai_available():
            pytest.skip(
                f"Configured AI provider ({get_configured_ai_provider()}) not available"
            )

        settings = get_settings_service()
        provider = get_configured_ai_provider()
        model = get_configured_ai_model()

        # Get endpoint based on provider
        if provider == "lm_studio":
            endpoint = settings.get(
                "ai", "lm_studio.endpoint", "http://localhost:1234/v1"
            )
        elif provider == "ollama":
            endpoint = settings.get("ai", "ollama.url", "http://localhost:11434")
        else:
            endpoint = settings.get("ai", f"{provider}.url", None)

        config = AIModelConfiguration(
            user_id=1, provider=provider, model=model, endpoint=endpoint
        )

        ai_service = AIService(config, logging.getLogger("TestAITutorE2E"))

        try:
            yield ai_service
        finally:
            try:
                ai_service.close()
            except Exception:
                pass

    # ===== Study Plan Selection Tests =====

    def test_load_study_plans_for_student(
        self, db_service, test_student, test_study_plan_with_content
    ):
        """Test loading study plans for a student - same as GUI's load_study_plans()"""
        # This simulates exactly what AITutor.load_study_plans() does
        from sqlalchemy import select
        from core.models import StudentStudyPlan, StudyPlan

        with db_service.get_session() as session:
            # Students see assigned plans
            stmt = (
                select(StudyPlan)
                .join(StudentStudyPlan, StudentStudyPlan.study_plan_id == StudyPlan.id)
                .where(StudentStudyPlan.student_id == test_student.id)
            )
            plans = list(session.execute(stmt).scalars().all())

        assert len(plans) >= 1
        plan = plans[0]
        assert plan.title == "Python Programming Fundamentals"
        assert len(plan.phases) == 3

    def test_load_study_plans_for_teacher(
        self, db_service, test_teacher, test_study_plan_with_content
    ):
        """Test loading study plans for a teacher - same as GUI's load_study_plans()"""
        from sqlalchemy import select
        from core.models import StudyPlan

        with db_service.get_session() as session:
            # Teachers see plans they created
            stmt = select(StudyPlan).where(StudyPlan.creator_id == test_teacher.id)
            plans = list(session.execute(stmt).scalars().all())

        assert len(plans) >= 1
        assert any(p.title == "Python Programming Fundamentals" for p in plans)

    # ===== Topic (Phase) Selection Tests =====

    def test_load_plan_topics(self, db_service, test_study_plan_with_content):
        """Test loading topics/phases from a study plan - same as GUI's load_plan_topics()"""
        plan = test_study_plan_with_content["plan"]

        with db_service.get_session() as session:
            from core.models import StudyPlan

            loaded_plan = session.get(StudyPlan, plan.id)

            assert loaded_plan is not None
            assert loaded_plan.phases is not None
            assert isinstance(loaded_plan.phases, list)

            phases = loaded_plan.phases
            assert len(phases) == 3

            # Verify phase names (supporting both 'name' and 'title' keys)
            phase_names = [p.get("title", p.get("name")) for p in phases]
            assert "Introduction to Python" in phase_names
            assert "Variables and Data Types" in phase_names
            assert "Control Flow" in phase_names

    # ===== Content Selection Tests =====

    def test_load_topic_content(self, db_service, test_study_plan_with_content):
        """Test loading content for a specific topic - same as GUI's load_topic_content()"""
        plan = test_study_plan_with_content["plan"]

        with db_service.get_session() as session:
            from core.models import StudyPlan

            loaded_plan = session.get(StudyPlan, plan.id)
            assert loaded_plan is not None

            # Load content for Phase 1 (Variables and Data Types)
            phase_contents = [
                assoc for assoc in loaded_plan.plan_contents if assoc.phase_index == 1
            ]

            # Should have 2 contents in Phase 1
            assert len(phase_contents) == 2

            # Sort by order_index
            phase_contents.sort(key=lambda x: x.order_index)

            # First content should be the variables lesson
            assert phase_contents[0].content.title == "Understanding Variables"
            # Second should be the exercise
            assert phase_contents[1].content.title == "Variable Practice"

    def test_content_filtering_by_phase(self, db_service, test_study_plan_with_content):
        """Test that content is correctly filtered by phase index"""
        plan = test_study_plan_with_content["plan"]

        with db_service.get_session() as session:
            from core.models import StudyPlan

            loaded_plan = session.get(StudyPlan, plan.id)

            # Phase 0 should have 1 content
            phase_0_contents = [
                a for a in loaded_plan.plan_contents if a.phase_index == 0
            ]
            assert len(phase_0_contents) == 1
            assert phase_0_contents[0].content.title == "What is Python?"

            # Phase 1 should have 2 contents
            phase_1_contents = [
                a for a in loaded_plan.plan_contents if a.phase_index == 1
            ]
            assert len(phase_1_contents) == 2

            # Phase 2 should have 1 content
            phase_2_contents = [
                a for a in loaded_plan.plan_contents if a.phase_index == 2
            ]
            assert len(phase_2_contents) == 1
            assert phase_2_contents[0].content.title == "Loops in Python"

    # ===== Context Summary Tests =====

    def test_study_plan_summary_without_phase_selection(
        self, db_service, test_study_plan_with_content
    ):
        """Test getting study plan summary without selecting a phase"""
        plan = test_study_plan_with_content["plan"]

        summary = db_service.get_study_plan_summary(plan.id)

        assert summary is not None
        assert summary["id"] == plan.id
        assert summary["title"] == "Python Programming Fundamentals"
        assert summary["total_phases"] == 3
        assert summary["selected_phase_index"] is None
        # Default to first phase
        assert summary["current_phase"]["name"] == "Introduction to Python"

    def test_study_plan_summary_with_phase_selection(
        self, db_service, test_study_plan_with_content
    ):
        """Test getting study plan summary with specific phase selected"""
        plan = test_study_plan_with_content["plan"]

        # Select Phase 1 (Variables and Data Types)
        summary = db_service.get_study_plan_summary(plan.id, selected_phase_index=1)

        assert summary is not None
        assert summary["selected_phase_index"] == 1
        assert summary["current_phase"]["name"] == "Variables and Data Types"
        assert (
            "Understand variables and naming conventions"
            in summary["current_phase"]["objectives"]
        )

        # Select Phase 2 (Control Flow)
        summary = db_service.get_study_plan_summary(plan.id, selected_phase_index=2)

        assert summary["selected_phase_index"] == 2
        assert summary["current_phase"]["name"] == "Control Flow"
        assert (
            "Master if/else/elif statements" in summary["current_phase"]["objectives"]
        )

    def test_content_summary(self, db_service, test_study_plan_with_content):
        """Test getting content summary"""
        variables_lesson = test_study_plan_with_content["contents"]["variables_lesson"]

        summary = db_service.get_content_summary(variables_lesson.id)

        assert summary is not None
        assert summary["id"] == variables_lesson.id
        assert summary["title"] == "Understanding Variables"
        assert summary["type"] == "lesson"
        assert summary["difficulty"] == 2
        assert summary["estimated_time_min"] == 20

    # ===== Full Context Flow Tests (Same as GUI send_message) =====

    def test_full_context_gathering_flow(
        self, db_service, test_student, test_study_plan_with_content
    ):
        """
        Test the complete context gathering flow - exactly as GUI's send_message() does.

        This simulates:
        1. User selects a study plan
        2. User selects a topic (phase)
        3. User selects content within that topic
        4. System gathers all context for AI
        """
        plan = test_study_plan_with_content["plan"]
        variables_lesson = test_study_plan_with_content["contents"]["variables_lesson"]

        # Simulate GUI state
        user_id = test_student.id
        selected_plan_id = plan.id
        selected_topic_index = 1  # Phase 1: Variables and Data Types
        selected_content_id = variables_lesson.id

        # Gather context exactly as GUI does in send_message()
        study_plan_context = None
        content_context = None
        user_obj = None

        if user_id:
            user_obj = db_service.get_user_by_id(user_id)

            if selected_plan_id:
                # Get study plan summary with selected topic context
                study_plan_context = db_service.get_study_plan_summary(
                    selected_plan_id, selected_phase_index=selected_topic_index
                )

            if selected_content_id:
                content_context = db_service.get_content_summary(selected_content_id)

        # Verify all context was gathered correctly
        assert user_obj is not None
        assert user_obj.id == test_student.id

        assert study_plan_context is not None
        assert study_plan_context["title"] == "Python Programming Fundamentals"
        assert study_plan_context["selected_phase_index"] == 1
        assert study_plan_context["current_phase"]["name"] == "Variables and Data Types"

        assert content_context is not None
        assert content_context["title"] == "Understanding Variables"

    # ===== Real AI Integration Tests (LM Studio by default) =====

    @pytest.mark.real_ai
    @pytest.mark.skipif(
        not is_configured_ai_available(), reason="Configured AI not available"
    )
    def test_ai_tutoring_with_full_context(
        self, ollama_ai_service, db_service, test_student, test_study_plan_with_content
    ):
        """
        Test AI tutoring with full context - exactly as GUI does.

        This is a REAL AI test using the configured provider (LM Studio by default).
        """
        plan = test_study_plan_with_content["plan"]
        variables_lesson = test_study_plan_with_content["contents"]["variables_lesson"]

        # Gather context
        study_plan_context = db_service.get_study_plan_summary(
            plan.id, selected_phase_index=1
        )
        content_context = db_service.get_content_summary(variables_lesson.id)
        user_obj = db_service.get_user_by_id(test_student.id)

        # Send question to AI - exactly as AIWorker.run() does
        question = "What is a variable in Python and how do I create one?"

        result = ollama_ai_service.provide_tutoring(
            user=user_obj,
            question=question,
            context=None,
            study_plan_context=study_plan_context,
            content_context=content_context,
            conversation_history=[],
        )

        # Validate response structure
        assert isinstance(result, dict)
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

        # Response should be relevant to variables/Python
        answer_lower = result["answer"].lower()
        assert any(
            word in answer_lower
            for word in ["variable", "python", "store", "value", "assign"]
        )

    @pytest.mark.real_ai
    @pytest.mark.skipif(
        not is_configured_ai_available(), reason="Configured AI not available"
    )
    def test_ai_tutoring_multi_turn_conversation(
        self, ollama_ai_service, db_service, test_student, test_study_plan_with_content
    ):
        """
        Test multi-turn conversation with AI - preserving context.

        This simulates a real conversation flow.
        """
        plan = test_study_plan_with_content["plan"]
        loops_lesson = test_study_plan_with_content["contents"]["loops_lesson"]

        # Gather context for Control Flow topic
        study_plan_context = db_service.get_study_plan_summary(
            plan.id, selected_phase_index=2
        )
        content_context = db_service.get_content_summary(loops_lesson.id)
        user_obj = db_service.get_user_by_id(test_student.id)

        conversation_history = []

        # First message
        question1 = "What is a for loop?"
        result1 = ollama_ai_service.provide_tutoring(
            user=user_obj,
            question=question1,
            study_plan_context=study_plan_context,
            content_context=content_context,
            conversation_history=conversation_history,
        )

        assert "answer" in result1
        conversation_history.append({"role": "user", "content": question1})
        conversation_history.append(
            {"role": "assistant", "content": result1.get("answer", "")}
        )

        # Follow-up question (should have context from previous)
        question2 = "Can you show me an example?"
        result2 = ollama_ai_service.provide_tutoring(
            user=user_obj,
            question=question2,
            study_plan_context=study_plan_context,
            content_context=content_context,
            conversation_history=conversation_history,
        )

        assert "answer" in result2
        # Response should contain some code or example
        answer2_lower = result2["answer"].lower()
        assert any(
            word in answer2_lower
            for word in ["for", "loop", "in", "range", "example", ":"]
        )

    @pytest.mark.real_ai
    @pytest.mark.skipif(
        not is_configured_ai_available(), reason="Configured AI not available"
    )
    def test_ai_tutoring_without_topic_selection(
        self, ollama_ai_service, db_service, test_student, test_study_plan_with_content
    ):
        """
        Test AI tutoring with study plan but no topic selected.

        This tests the scenario where user selects a plan but leaves topic on "All Topics".
        """
        plan = test_study_plan_with_content["plan"]

        # Get summary without topic selection (selected_phase_index=None)
        study_plan_context = db_service.get_study_plan_summary(
            plan.id, selected_phase_index=None
        )
        user_obj = db_service.get_user_by_id(test_student.id)

        question = "What will I learn in this course?"

        result = ollama_ai_service.provide_tutoring(
            user=user_obj,
            question=question,
            study_plan_context=study_plan_context,
            content_context=None,  # No specific content
            conversation_history=[],
        )

        assert "answer" in result
        # Response should mention Python or programming
        answer_lower = result["answer"].lower()
        assert (
            "python" in answer_lower
            or "programming" in answer_lower
            or "learn" in answer_lower
        )

    @pytest.mark.real_ai
    @pytest.mark.skipif(
        not is_configured_ai_available(), reason="Configured AI not available"
    )
    def test_ai_tutoring_general_mode(
        self, ollama_ai_service, db_service, test_student
    ):
        """
        Test AI tutoring in general mode (no study plan selected).

        This tests the "None (General Mode)" selection in the GUI.
        """
        user_obj = db_service.get_user_by_id(test_student.id)

        question = "Can you help me understand programming concepts?"

        result = ollama_ai_service.provide_tutoring(
            user=user_obj,
            question=question,
            study_plan_context=None,  # No plan
            content_context=None,  # No content
            conversation_history=[],
        )

        assert "answer" in result
        assert len(result["answer"]) > 0

    # ===== Edge Case Tests =====

    def test_empty_plan_phases(self, db_service, test_teacher):
        """Test handling of study plan with no phases"""
        empty_plan = StudyPlan(
            title="Empty Plan",
            description="A plan with no phases",
            creator_id=test_teacher.id,
            phases=[],
        )
        created_plan = db_service.create_study_plan(empty_plan)

        summary = db_service.get_study_plan_summary(created_plan.id)

        assert summary is not None
        assert summary["total_phases"] == 0
        assert summary["current_phase"] is None

    def test_topic_with_no_content(self, db_service, test_teacher):
        """Test handling of topic with no associated content"""
        plan = StudyPlan(
            title="Plan with Empty Topics",
            description="A plan where some topics have no content",
            creator_id=test_teacher.id,
            phases=[
                {"name": "Topic 1", "objectives": ["Objective 1"]},
                {"name": "Topic 2", "objectives": ["Objective 2"]},
            ],
        )
        created_plan = db_service.create_study_plan(plan)

        # Only add content to first topic
        content = Content(
            creator_id=test_teacher.id,
            content_type=ContentType.LESSON,
            title="Only Content",
            difficulty=1,
        )
        content = db_service.create_content(content)
        db_service.add_content_to_plan(
            created_plan.id, content.id, phase_index=0, order_index=0
        )

        with db_service.get_session() as session:
            from core.models import StudyPlan as SP

            loaded = session.get(SP, created_plan.id)

            # Topic 0 should have content
            topic_0_content = [a for a in loaded.plan_contents if a.phase_index == 0]
            assert len(topic_0_content) == 1

            # Topic 1 should have no content
            topic_1_content = [a for a in loaded.plan_contents if a.phase_index == 1]
            assert len(topic_1_content) == 0


class TestAITutorE2EWithMockedAI:
    """
    E2E tests using mocked AI for faster, deterministic testing.

    These tests verify the complete data flow without requiring a real AI provider.
    """

    @pytest.fixture(scope="class")
    def db_service(self):
        """Create test database"""
        os.environ["SLM_TEST_MODE"] = "1"
        db = DatabaseService(":memory:")
        yield db
        db.close()

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service for deterministic testing"""
        from unittest.mock import MagicMock
        from core.services.ai_service import AIResponse, AIProvider

        model = get_configured_ai_model()
        provider_str = get_configured_ai_provider()

        # Map provider string to AIProvider enum
        provider_enum_map = {
            "lm_studio": AIProvider.LM_STUDIO,
            "ollama": AIProvider.OLLAMA,
            "openai": AIProvider.OPENAI,
            "anthropic": AIProvider.ANTHROPIC,
            "openrouter": AIProvider.OPENROUTER,
        }
        provider_enum = provider_enum_map.get(provider_str, AIProvider.LM_STUDIO)

        settings = get_settings_service()
        if provider_str == "lm_studio":
            endpoint = settings.get(
                "ai", "lm_studio.endpoint", "http://localhost:1234/v1"
            )
        elif provider_str == "ollama":
            endpoint = settings.get("ai", "ollama.url", "http://localhost:11434")
        else:
            endpoint = settings.get("ai", f"{provider_str}.url", None)

        config = AIModelConfiguration(
            user_id=1, provider=provider_str, model=model, endpoint=endpoint
        )

        ai_service = AIService(config, logging.getLogger("TestAITutorE2E"))

        # Mock the _call_ai method
        mock_response = AIResponse(
            content='{"answer": "This is a test response about variables.", "explanation": "Variables store data.", "related_topics": ["data types"], "encouragement": "Keep learning!"}',
            tokens_used=50,
            model=model,
            provider=provider_enum,
            response_time=0.1,
            timestamp=datetime.now(),
        )
        ai_service._call_ai = MagicMock(return_value=mock_response)

        yield ai_service

    @pytest.fixture
    def test_data(self, db_service):
        """Create comprehensive test data"""
        # Create teacher
        teacher = User(
            username=f"mock_teacher_{datetime.now().timestamp()}",
            password_hash=hash_password("testpass123"),
            email=f"mock_teacher_{datetime.now().timestamp()}@test.com",
            role=UserRole.TEACHER,
            first_name="Mock",
            last_name="Teacher",
        )
        teacher = db_service.create_user(teacher)

        # Create student
        student = User(
            username=f"mock_student_{datetime.now().timestamp()}",
            password_hash=hash_password("testpass123"),
            email=f"mock_student_{datetime.now().timestamp()}@test.com",
            role=UserRole.STUDENT,
            first_name="Mock",
            last_name="Student",
            grade_level="10",
        )
        student = db_service.create_user(student)

        # Create study plan
        plan = StudyPlan(
            title="Test Python Course",
            description="A test course for mock testing",
            creator_id=teacher.id,
            phases=[
                {"name": "Basics", "title": "Basics", "objectives": ["Learn basics"]},
                {
                    "name": "Advanced",
                    "title": "Advanced",
                    "objectives": ["Learn advanced"],
                },
            ],
        )
        plan = db_service.create_study_plan(plan)

        # Create content
        content1 = Content(
            creator_id=teacher.id,
            content_type=ContentType.LESSON,
            title="Basic Lesson",
            difficulty=1,
        )
        content1 = db_service.create_content(content1)
        db_service.add_content_to_plan(
            plan.id, content1.id, phase_index=0, order_index=0
        )

        content2 = Content(
            creator_id=teacher.id,
            content_type=ContentType.LESSON,
            title="Advanced Lesson",
            difficulty=3,
        )
        content2 = db_service.create_content(content2)
        db_service.add_content_to_plan(
            plan.id, content2.id, phase_index=1, order_index=0
        )

        # Assign to student
        assignment = StudentStudyPlan(
            student_id=student.id, study_plan_id=plan.id, assigned_at=datetime.now()
        )
        db_service.create_student_study_plan(assignment)

        return {
            "teacher": teacher,
            "student": student,
            "plan": plan,
            "content1": content1,
            "content2": content2,
        }

    def test_complete_flow_with_mocked_ai(self, db_service, mock_ai_service, test_data):
        """
        Test complete GUI flow with mocked AI.

        Simulates:
        1. Load study plans for student
        2. Select a study plan
        3. Load topics
        4. Select a topic
        5. Load content for topic
        6. Select content
        7. Send message with full context
        8. Receive AI response
        """
        from sqlalchemy import select
        from core.models import StudentStudyPlan, StudyPlan

        student = test_data["student"]
        plan = test_data["plan"]
        content = test_data["content2"]  # Advanced Lesson

        # Step 1: Load study plans (as GUI does)
        with db_service.get_session() as session:
            stmt = (
                select(StudyPlan)
                .join(StudentStudyPlan, StudentStudyPlan.study_plan_id == StudyPlan.id)
                .where(StudentStudyPlan.student_id == student.id)
            )
            plans = list(session.execute(stmt).scalars().all())

        assert len(plans) >= 1
        selected_plan = plans[0]

        # Step 2-3: Load topics from selected plan
        with db_service.get_session() as session:
            loaded_plan = session.get(StudyPlan, selected_plan.id)
            topics = loaded_plan.phases

        assert len(topics) == 2
        selected_topic_index = 1  # Select "Advanced"

        # Step 4-5: Load content for selected topic
        with db_service.get_session() as session:
            loaded_plan = session.get(StudyPlan, selected_plan.id)
            topic_contents = [
                a
                for a in loaded_plan.plan_contents
                if a.phase_index == selected_topic_index
            ]

            assert len(topic_contents) == 1
            # Get the content ID while still in session
            selected_content_id = topic_contents[0].content.id
            content_title = topic_contents[0].content.title

        # Step 6: Gather context (exactly as send_message does)
        user_obj = db_service.get_user_by_id(student.id)
        study_plan_context = db_service.get_study_plan_summary(
            selected_plan.id, selected_phase_index=selected_topic_index
        )
        content_context = db_service.get_content_summary(selected_content_id)

        # Verify context
        assert study_plan_context["current_phase"]["name"] == "Advanced"
        assert content_context["title"] == content_title

        # Step 7-8: Send message and get response
        question = "Tell me about this topic"
        conversation_history = []

        result = mock_ai_service.provide_tutoring(
            user=user_obj,
            question=question,
            study_plan_context=study_plan_context,
            content_context=content_context,
            conversation_history=conversation_history,
        )

        # Verify response
        assert "answer" in result
        assert len(result["answer"]) > 0

        # The mock should have been called
        mock_ai_service._call_ai.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
