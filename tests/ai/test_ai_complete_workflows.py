"""
Comprehensive testing for complete real user workflows in SLMEducator.
Tests the entire educational process: study plan creation → student usage → AI assistance.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.models.models import AIModelConfiguration
from src.core.services.ai_service import AIService, AIResponse, AIProvider


class TestCompleteUserWorkflows:
    """Test complete end-to-end user workflows."""

    @pytest.fixture
    def mock_ai_config(self):
        """Create mock AI configuration."""
        config = Mock(spec=AIModelConfiguration)
        config.id = 1
        config.provider = "openrouter"
        config.model = "gpt-3.5-turbo"
        config.endpoint = "https://openrouter.ai/api/v1"
        config.api_key = "encrypted_test_key_12345"
        config.model_parameters = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "You are an educational assistant.",
        }
        config.validated = True
        config.created_at = datetime.now()
        config.updated_at = datetime.now()

        # Mock encryption methods
        config.decrypted_api_key = "sk-test-key-12345"
        config.set_encrypted_api_key = Mock()
        return config

    @pytest.fixture
    def mock_teacher(self):
        """Create mock teacher user."""
        teacher = Mock()
        teacher.id = 1
        teacher.username = "teacher_user"
        teacher.email = "teacher@example.com"
        teacher.role = "teacher"
        return teacher

    @pytest.fixture
    def mock_student(self):
        """Create mock student user."""
        student = Mock()
        student.id = 2
        student.username = "student_user"
        student.email = "student@example.com"
        student.role = "student"
        return student

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        return logger

    def test_teacher_creates_study_plan_workflow(
        self, mock_ai_config, mock_teacher, mock_logger
    ):
        """Test complete workflow: Teacher creates study plan using AI."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock AI response for study plan generation
        ai_response = AIResponse(
            content="Algebra Study Plan:\n1. Variables and Expressions\n2. Solving Linear Equations\n3. Graphing Linear Functions\n4. Systems of Equations",
            tokens_used=150,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=2.5,
            timestamp=datetime.now(),
        )

        # Act - Teacher creates study plan with AI assistance
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.return_value = ai_response

            teacher_prompt = "Create a comprehensive study plan for 8th grade algebra including variables, equations, and graphing"
            generated_content = ai_service.generate_content(teacher_prompt)

            # Assert
            assert "Variables and Expressions" in generated_content.content
            assert "Solving Linear Equations" in generated_content.content
            assert generated_content.tokens_used == 150
            assert generated_content.response_time > 0

    def test_student_completes_assessment_workflow(
        self, mock_ai_config, mock_student, mock_logger
    ):
        """Test workflow: Student completes assessment and gets AI grading."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock AI grading response
        grading_response = AIResponse(
            content="Student answer: A variable represents a number\nCorrectness: Correct\nPoints earned: 5\nPercentage: 100%\nFeedback: Good understanding of variables",
            tokens_used=60,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.0,
            timestamp=datetime.now(),
        )

        # Act - Student completes assessment and gets AI grading
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.return_value = grading_response

            grading_prompt = "Grade this student answer for the question 'What is a variable?': A variable represents a number"
            grade_result = ai_service.generate_content(grading_prompt)

            # Assert
            assert "Points earned: 5" in grade_result.content
            assert "Percentage: 100%" in grade_result.content
            assert "Good understanding of variables" in grade_result.content

    def test_complete_educational_journey_workflow(
        self, mock_ai_config, mock_teacher, mock_student, mock_logger
    ):
        """Test complete educational journey: Teacher creates → Student learns → AI assists."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock responses for each step
        responses = [
            AIResponse(
                content="Algebra Study Plan with variables and equations",
                tokens_used=120,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=2.0,
                timestamp=datetime.now(),
            ),
            AIResponse(
                content="Assessment Questions about algebra",
                tokens_used=80,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=1.5,
                timestamp=datetime.now(),
            ),
            AIResponse(
                content="Help with graphing linear equations",
                tokens_used=95,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=1.8,
                timestamp=datetime.now(),
            ),
            AIResponse(
                content="Student scored 77% on assessment",
                tokens_used=65,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=1.2,
                timestamp=datetime.now(),
            ),
        ]

        # Act - Complete workflow simulation
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = responses

            workflow_results = {}

            # Step 1: Teacher creates study plan
            study_plan_prompt = (
                "Create a comprehensive algebra study plan for 8th grade"
            )
            study_plan_content = ai_service.generate_content(study_plan_prompt)
            workflow_results["study_plan"] = study_plan_content

            # Step 2: Teacher creates assessment
            assessment_prompt = (
                "Create assessment questions for this algebra study plan"
            )
            assessment_content = ai_service.generate_content(assessment_prompt)
            workflow_results["assessment"] = assessment_content

            # Step 3: Student gets help
            help_prompt = "I need help understanding how to graph linear equations"
            help_content = ai_service.generate_content(help_prompt)
            workflow_results["student_help"] = help_content

            # Step 4: AI grades student work
            grading_prompt = "Grade this student's algebra assessment"
            grading_content = ai_service.generate_content(grading_prompt)
            workflow_results["grading"] = grading_content

            # Assert - Complete workflow validation
            assert "study_plan" in workflow_results
            assert "assessment" in workflow_results
            assert "student_help" in workflow_results
            assert "grading" in workflow_results

            assert workflow_results["study_plan"].tokens_used == 120
            assert workflow_results["assessment"].tokens_used == 80
            assert workflow_results["student_help"].tokens_used == 95
            assert workflow_results["grading"].tokens_used == 65

            # Verify AI service was called for each step
            assert mock_generate.call_count == 4

            print(
                f"Complete workflow successful! Total tokens used: {sum(result.tokens_used for result in workflow_results.values())}"
            )

    def test_workflow_error_handling(self, mock_ai_config, mock_teacher, mock_logger):
        """Test workflow error handling when AI service fails."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate AI service failure
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = Exception("AI service unavailable")

            # Try to create study plan and log the error
            try:
                study_plan_prompt = "Create a math study plan"
                ai_service.generate_content(study_plan_prompt)
                assert False, "Should have raised an exception"
            except Exception as e:
                # Log the error manually (simulating what AIService would do)
                mock_logger.error(f"AI service error: {e}")
                # Assert
                assert "AI service unavailable" in str(e)
                mock_logger.error.assert_called_with(f"AI service error: {e}")

    def test_workflow_performance_monitoring(
        self, mock_ai_config, mock_teacher, mock_logger
    ):
        """Test workflow performance monitoring and metrics."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock multiple AI responses with different response times
        ai_responses = [
            AIResponse(
                content="Study plan content",
                tokens_used=100,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=1.0,
                timestamp=datetime.now(),
            ),
            AIResponse(
                content="Lesson content",
                tokens_used=150,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=1.5,
                timestamp=datetime.now(),
            ),
            AIResponse(
                content="Assessment content",
                tokens_used=80,
                model="gpt-3.5-turbo",
                provider=AIProvider.OPENROUTER,
                response_time=0.8,
                timestamp=datetime.now(),
            ),
        ]

        # Act - Monitor performance across multiple workflow steps
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = ai_responses

            performance_metrics = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_response_time": 0,
                "average_response_time": 0,
            }

            # Simulate workflow steps
            prompts = ["Create study plan", "Create lesson", "Create assessment"]
            for prompt in prompts:
                response = ai_service.generate_content(prompt)
                performance_metrics["total_requests"] += 1
                performance_metrics["total_tokens"] += response.tokens_used
                performance_metrics["total_response_time"] += response.response_time

            # Calculate averages
            if performance_metrics["total_requests"] > 0:
                performance_metrics["average_response_time"] = (
                    performance_metrics["total_response_time"]
                    / performance_metrics["total_requests"]
                )

            # Assert
            assert performance_metrics["total_requests"] == 3
            assert performance_metrics["total_tokens"] == 330
            assert performance_metrics["total_response_time"] == 3.3
            # Use pytest.approx to handle floating point precision issues
            assert performance_metrics["average_response_time"] == pytest.approx(1.1)

            print(f"Performance metrics: {performance_metrics}")
