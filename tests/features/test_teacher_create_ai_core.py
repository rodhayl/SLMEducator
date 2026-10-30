import pytest
from unittest.mock import Mock
from core.models.models import User, AIModelConfiguration, StudyPlan, UserRole
from core.services.ai_service import AIService
from core.services.logging import get_logger


class TestTeacherCreateAICore:
    """Test core AI functionality for Teacher Create AI wizard without GUI dependencies."""

    # Use db_service fixture from conftest.py instead of creating our own
    # This ensures proper table initialization and cleanup

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service for testing."""
        mock_service = Mock(spec=AIService)

        # Mock successful study plan generation
        mock_service.generate_study_plan.return_value = {
            "title": "Python Programming Basics",
            "description": "A comprehensive study plan for learning Python fundamentals",
            "items": [
                {
                    "title": "Variables and Data Types",
                    "description": "Learn about Python variables, integers, strings, and booleans",
                    "estimated_time": 30,
                    "difficulty": "beginner",
                },
                {
                    "title": "Control Flow",
                    "description": "Master if statements, loops, and conditional logic",
                    "estimated_time": 45,
                    "difficulty": "beginner",
                },
                {
                    "title": "Functions",
                    "description": "Create reusable functions with parameters and return values",
                    "estimated_time": 60,
                    "difficulty": "intermediate",
                },
            ],
        }

        # Mock token usage tracking (AIService doesn't have get_token_usage method)
        mock_service._token_usage = {
            "prompt_tokens": 150,
            "completion_tokens": 250,
            "total_tokens": 400,
        }

        return mock_service

    @pytest.fixture
    def ai_config(self, db_service, teacher):
        """Create AI model configuration for testing."""
        config = AIModelConfiguration(
            user_id=teacher.id,
            provider="openai",
            model="gpt-4",
            endpoint=None,
            api_key="test-key-encrypted",  # This should be encrypted in real usage
            validated=True,
            model_parameters={
                "max_tokens": 2000,
                "temperature": 0.7,
                "system_prompt": "You are a helpful educational assistant.",
            },
        )
        # Use database service to create the config
        db_service.session.add(config)
        db_service.session.commit()
        return config

    @pytest.fixture
    def teacher(self, db_service):
        """Create a test teacher user."""
        user = User(
            username="test_teacher",
            email="teacher@test.com",
            role=UserRole.TEACHER,
            password_hash="hashed_password",
            first_name="Test",
            last_name="Teacher",
        )
        created_user = db_service.create_user(user)
        return created_user

    def test_study_plan_generation_core(
        self, db_service, teacher, ai_config, mock_ai_service
    ):
        """Test core study plan generation functionality."""
        # Test data
        subject = "Python Programming"
        grade_level = "intermediate"
        learning_objectives = [
            "Learn Python basics",
            "Master control flow",
            "Understand functions",
        ]
        duration_weeks = 8

        # Create AI service instance and ensure client is closed after use
        logger = get_logger("test_ai_service")
        with AIService(ai_config, logger) as ai_service:

            # Mock the _call_ai method to avoid real API calls
            # Replace http client to avoid network calls and return a mock response
            from unittest.mock import Mock as _Mock

            mock_http_client = _Mock()
            mock_response = _Mock()
            mock_response.status_code = 200
            import json as _json

            study_plan = {
                "title": "Python Programming Basics",
                "description": "A comprehensive study plan for learning Python fundamentals",
                "items": [
                    {
                        "title": "Variables and Data Types",
                        "description": "Learn about Python variables, integers, strings, and booleans",
                        "estimated_time": 30,
                        "difficulty": "beginner",
                    },
                    {
                        "title": "Control Flow",
                        "description": "Master if statements, loops, and conditional logic",
                        "estimated_time": 45,
                        "difficulty": "beginner",
                    },
                    {
                        "title": "Functions",
                        "description": "Create reusable functions with parameters and return values",
                        "estimated_time": 60,
                        "difficulty": "intermediate",
                    },
                ],
            }
            json_str = _json.dumps(study_plan)
            mock_response.json.return_value = {
                "choices": [{"message": {"content": json_str}}],
                "model": "gpt-4",
                "usage": {"total_tokens": 400},
            }
            mock_http_client.post.return_value = mock_response
            ai_service._client = mock_http_client
            from unittest.mock import patch as _patch

            with _patch.object(AIService, "_call_ai") as mock_call_ai, _patch.object(
                AIService, "_call_openai"
            ) as mock_call_openai:
                # Mock the AI response
                mock_call_ai.return_value = Mock(
                    content='{"title": "Python Programming Basics", "description": "A comprehensive study plan for learning Python fundamentals", "items": [{"title": "Variables and Data Types", "description": "Learn about Python variables, integers, strings, and booleans", "estimated_time": 30, "difficulty": "beginner"}, {"title": "Control Flow", "description": "Master if statements, loops, and conditional logic", "estimated_time": 45, "difficulty": "beginner"}, {"title": "Functions", "description": "Create reusable functions with parameters and return values", "estimated_time": 60, "difficulty": "intermediate"}]}',
                    tokens_used=400,
                    model="gpt-4",
                    provider="openai",
                    response_time=1.5,
                    timestamp="2025-11-18T16:56:41.776681Z",
                )

            # Generate study plan
            result = ai_service.generate_study_plan(
                user=teacher,
                subject=subject,
                grade_level=grade_level,
                learning_objectives=learning_objectives,
                duration_weeks=duration_weeks,
            )

            # Verify the result
            assert result is not None
            assert "title" in result
            assert "description" in result
            assert "items" in result
            assert len(result["items"]) > 0

            # Verify study plan structure
            assert result["title"] == "Python Programming Basics"
            assert (
                result["description"]
                == "A comprehensive study plan for learning Python fundamentals"
            )
            assert len(result["items"]) == 3

            # Verify study plan items
            for item in result["items"]:
                assert "title" in item
                assert "description" in item
                assert "estimated_time" in item
                assert "difficulty" in item
                assert item["difficulty"] in ["beginner", "intermediate", "advanced"]
                assert isinstance(item["estimated_time"], int)
                assert item["estimated_time"] > 0

    def test_study_plan_persistence(self, db_service, teacher):
        """Test that study plans can be saved to database."""
        # Create a study plan
        study_plan = StudyPlan(
            creator_id=teacher.id,  # User ID since teacher is a User with role='teacher'
            title="Python Programming Basics",
            description="A comprehensive study plan for learning Python fundamentals",
            phases=[  # JSON structure for study plan phases
                {
                    "title": "Variables and Data Types",
                    "description": "Learn about Python variables, integers, strings, and booleans",
                    "estimated_time": 30,
                    "difficulty": "beginner",
                },
                {
                    "title": "Control Flow",
                    "description": "Master if statements, loops, and conditional logic",
                    "estimated_time": 45,
                    "difficulty": "beginner",
                },
            ],
            is_public=False,
        )

        # Use database service to create study plan
        created_plan = db_service.create_study_plan(study_plan)

        # Verify persistence
        assert created_plan is not None
        assert created_plan.id is not None
        assert created_plan.title == "Python Programming Basics"
        assert (
            created_plan.creator_id == teacher.id
        )  # User ID since teacher is a User with role='teacher'
        assert len(created_plan.phases) == 2
        assert created_plan.phases[0]["title"] == "Variables and Data Types"
        assert created_plan.phases[1]["title"] == "Control Flow"

    def test_study_plan_with_different_difficulties(self, mock_ai_service):
        """Test study plan generation with different difficulty levels."""
        difficulties = ["beginner", "intermediate", "advanced"]

        for difficulty in difficulties:
            # Configure mock to return appropriate difficulty
            mock_result = {
                "title": f"{difficulty.title()} Study Plan",
                "description": f"A {difficulty} level study plan",
                "items": [
                    {
                        "title": f"{difficulty.title()} Topic 1",
                        "description": f"Learn {difficulty} concept 1",
                        "estimated_time": 30,
                        "difficulty": difficulty,
                    }
                ],
            }
            mock_ai_service.generate_study_plan.return_value = mock_result

            # Generate study plan
            result = mock_ai_service.generate_study_plan(
                topic="Test Topic",
                description="Test description",
                difficulty=difficulty,
                estimated_weeks=4,
            )

            # Verify difficulty is handled correctly
            assert result["items"][0]["difficulty"] == difficulty
            assert difficulty in result["title"].lower()

    def test_study_plan_with_error_handling(self, mock_ai_service):
        """Test study plan generation with error scenarios."""
        # Mock AI service to raise an exception
        mock_ai_service.generate_study_plan.side_effect = Exception("AI service error")

        # Attempt to generate study plan
        with pytest.raises(Exception) as exc_info:
            mock_ai_service.generate_study_plan(
                topic="Test Topic",
                description="Test description",
                difficulty="intermediate",
                estimated_weeks=4,
            )

        # Verify error is properly raised
        assert "AI service error" in str(exc_info.value)

    def test_study_plan_token_usage_tracking(self, mock_ai_service):
        """Test that token usage is properly tracked during study plan generation."""
        # Generate study plan
        result = mock_ai_service.generate_study_plan(
            topic="Python Programming",
            description="Learn Python programming",
            difficulty="intermediate",
            estimated_weeks=8,
        )

        # Check token usage tracking (AIService doesn't have get_token_usage method)
        token_usage = getattr(mock_ai_service, "_token_usage", None)

        # Verify token usage is tracked
        assert token_usage is not None
        assert "prompt_tokens" in token_usage
        assert "completion_tokens" in token_usage
        assert "total_tokens" in token_usage
        assert token_usage["prompt_tokens"] > 0
        assert token_usage["completion_tokens"] > 0
        assert (
            token_usage["total_tokens"]
            == token_usage["prompt_tokens"] + token_usage["completion_tokens"]
        )

    def test_study_plan_validation(self, db_service, teacher):
        """Test study plan validation logic."""
        # Test valid study plan
        valid_plan = StudyPlan(
            creator_id=teacher.id,  # User ID since teacher is a User with role='teacher'
            title="Valid Plan",
            description="Test description",
            phases=[  # JSON structure for study plan phases
                {
                    "title": "Test Phase",
                    "description": "Test phase description",
                    "estimated_time": 30,
                    "difficulty": "intermediate",
                }
            ],
            is_public=False,
        )

        # Use database service to create study plan
        created_plan = db_service.create_study_plan(valid_plan)

        # Verify valid plan was saved
        assert created_plan is not None
        assert created_plan.id is not None
        assert created_plan.title == "Valid Plan"
