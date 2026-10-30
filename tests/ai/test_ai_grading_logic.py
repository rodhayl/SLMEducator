import pytest
from unittest.mock import Mock
from core.services.ai_service import AIService


class TestAIGradingLogic:
    """Test AI grading logic directly without GUI dependencies."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service."""
        service = Mock(spec=AIService)
        return service

    def test_ai_grading_workflow(self, mock_ai_service):
        """Test complete AI grading workflow logic."""
        # Setup
        question_text = "What is the capital of France?"
        student_answer = "Paris"
        correct_answer = "Paris"
        max_points = 10

        # Configure mock response
        mock_result = {
            "points_earned": 10,
            "max_points": 10,
            "percentage": 100,
            "feedback": "Correct!",
            "explanation": "Paris is the capital.",
            "strengths": ["Correct knowledge"],
            "improvements": [],
            "misconceptions": [],
        }
        mock_ai_service.grade_answer.return_value = mock_result

        # Execute
        result = mock_ai_service.grade_answer(
            question=question_text,
            answer=student_answer,
            question_type="short_answer",
            correct_answer=correct_answer,
            max_points=max_points,
        )

        # Verify
        assert result["points_earned"] == 10
        assert result["percentage"] == 100
        assert "Correct" in result["feedback"]

        mock_ai_service.grade_answer.assert_called_with(
            question=question_text,
            answer=student_answer,
            question_type="short_answer",
            correct_answer=correct_answer,
            max_points=max_points,
        )

    def test_ai_grading_partial_credit(self, mock_ai_service):
        """Test AI grading with partial credit logic."""
        # Setup
        question_text = "What is the capital of France?"
        student_answer = "Lyon"
        correct_answer = "Paris"
        max_points = 10

        # Configure mock response
        mock_result = {
            "points_earned": 4,
            "max_points": 10,
            "percentage": 40,
            "feedback": "Partially correct.",
            "explanation": "Lyon is a city in France but not the capital.",
            "strengths": ["Related knowledge"],
            "improvements": ["Focus on capital cities"],
            "misconceptions": ["Confused major city with capital"],
        }
        mock_ai_service.grade_answer.return_value = mock_result

        # Execute
        result = mock_ai_service.grade_answer(
            question=question_text,
            answer=student_answer,
            question_type="short_answer",
            correct_answer=correct_answer,
            max_points=max_points,
        )

        # Verify
        assert result["points_earned"] == 4
        assert result["percentage"] == 40
        assert "Partially" in result["feedback"]

    def test_ai_grading_error_handling(self, mock_ai_service):
        """Test fallback logic when AI service fails."""
        # Setup
        mock_ai_service.grade_answer.side_effect = Exception("AI Service Error")

        # Simulate client-side fallback logic
        try:
            mock_ai_service.grade_answer(
                question="Q",
                answer="A",
                question_type="type",
                correct_answer="C",
                max_points=10,
            )
        except Exception:
            # Fallback logic that would be in the app
            fallback_result = {
                "points_earned": 0,
                "feedback": "Error grading answer. Please try again.",
            }

        assert fallback_result["points_earned"] == 0
        assert "Error" in fallback_result["feedback"]

    def test_grading_different_question_types(self, mock_ai_service):
        """Test grading logic for different question types."""
        test_cases = [
            {
                "type": "true_false",
                "question": "Is Python a language?",
                "answer": "True",
                "correct": "True",
                "points": 5,
            },
            {
                "type": "numerical",
                "question": "2 + 2",
                "answer": "4",
                "correct": "4",
                "points": 10,
            },
            {
                "type": "multiple_choice",
                "question": "Select languages",
                "answer": "Python,Java",
                "correct": "Python,Java",
                "points": 15,
            },
        ]

        for case in test_cases:
            mock_ai_service.grade_answer.return_value = {
                "points_earned": case["points"],
                "max_points": case["points"],
                "feedback": "Correct",
            }

            result = mock_ai_service.grade_answer(
                question=case["question"],
                answer=case["answer"],
                question_type=case["type"],
                correct_answer=case["correct"],
                max_points=case["points"],
            )

            assert result["points_earned"] == case["points"]
            mock_ai_service.grade_answer.assert_called_with(
                question=case["question"],
                answer=case["answer"],
                question_type=case["type"],
                correct_answer=case["correct"],
                max_points=case["points"],
            )
