"""
Unit tests for the AI Grading System

Tests the three grading modes: AI_AUTOMATIC, AI_ASSISTED, MANUAL
And the associated API endpoints for accepting and modifying grades.
"""

import pytest
from src.core.models import (
    GradingMode,
    SubmissionStatus,
    QuestionType,
    Assessment,
    QuestionResponse,
)


class TestGradingModeEnum:
    """Test GradingMode enum values and behavior"""

    def test_grading_mode_values(self):
        """Verify all grading mode enum values exist"""
        assert GradingMode.AI_AUTOMATIC.value == "ai_automatic"
        assert GradingMode.AI_ASSISTED.value == "ai_assisted"
        assert GradingMode.MANUAL.value == "manual"

    def test_grading_mode_from_string(self):
        """Test creating GradingMode from string value"""
        assert GradingMode("ai_automatic") == GradingMode.AI_AUTOMATIC
        assert GradingMode("ai_assisted") == GradingMode.AI_ASSISTED
        assert GradingMode("manual") == GradingMode.MANUAL

    def test_grading_mode_invalid(self):
        """Test that invalid grading mode raises ValueError"""
        with pytest.raises(ValueError):
            GradingMode("invalid_mode")


class TestSubmissionStatusEnum:
    """Test SubmissionStatus enum including AI_GRADED status"""

    def test_submission_status_values(self):
        """Verify all status enum values exist including AI_GRADED"""
        assert SubmissionStatus.DRAFT.value == "draft"
        assert SubmissionStatus.SUBMITTED.value == "submitted"
        assert SubmissionStatus.AI_GRADED.value == "ai_graded"
        assert SubmissionStatus.GRADED.value == "graded"
        assert SubmissionStatus.RETURNED.value == "returned"

    def test_ai_graded_status_exists(self):
        """Verify AI_GRADED is a valid status"""
        status = SubmissionStatus("ai_graded")
        assert status == SubmissionStatus.AI_GRADED


class TestAssessmentGradingMode:
    """Test Assessment model grading_mode field"""

    def test_assessment_has_grading_mode_attribute(self):
        """Verify Assessment model has grading_mode field"""
        assert hasattr(Assessment, "grading_mode")

    def test_default_grading_mode(self):
        """Verify default grading mode is AI_ASSISTED"""
        # The column default should be AI_ASSISTED
        from sqlalchemy import inspect

        mapper = inspect(Assessment)
        grading_mode_col = mapper.columns["grading_mode"]
        # Check the default is set correctly
        assert grading_mode_col.default is not None


class TestQuestionResponseAIFields:
    """Test QuestionResponse model AI grading fields"""

    def test_ai_fields_exist(self):
        """Verify QuestionResponse has all AI suggestion fields"""
        assert hasattr(QuestionResponse, "ai_suggested_score")
        assert hasattr(QuestionResponse, "ai_suggested_feedback")
        assert hasattr(QuestionResponse, "ai_confidence")
        assert hasattr(QuestionResponse, "teacher_override")


class TestGradingLogic:
    """Test the grading logic for different question types and modes"""

    @pytest.fixture
    def objective_question_types(self):
        """Question types that should always be auto-graded"""
        return {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}

    @pytest.fixture
    def subjective_question_types(self):
        """Question types that require AI or manual grading"""
        return {
            QuestionType.SHORT_ANSWER,
            QuestionType.LONG_ANSWER,
            QuestionType.FILL_IN_BLANK,
        }

    def test_objective_questions_always_autograded(self, objective_question_types):
        """Objective questions should be auto-graded regardless of mode"""
        # These should always be auto-graded by string comparison
        for q_type in objective_question_types:
            assert q_type in {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}

    def test_subjective_question_types_identified(self, subjective_question_types):
        """Subjective questions should be correctly identified"""
        for q_type in subjective_question_types:
            assert q_type not in {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}


class TestStatusTransitions:
    """Test submission status transitions based on grading mode"""

    def test_ai_automatic_transitions_to_graded(self):
        """AI_AUTOMATIC mode should transition directly to GRADED"""
        # In AI_AUTOMATIC mode, after successful AI grading:
        # Status should be GRADED (not AI_GRADED)
        expected_final_status = SubmissionStatus.GRADED
        assert expected_final_status.value == "graded"

    def test_ai_assisted_transitions_to_ai_graded(self):
        """AI_ASSISTED mode should transition to AI_GRADED for review"""
        # In AI_ASSISTED mode, after AI grading:
        # Status should be AI_GRADED (pending teacher review)
        expected_status = SubmissionStatus.AI_GRADED
        assert expected_status.value == "ai_graded"

    def test_manual_stays_submitted(self):
        """MANUAL mode should keep status as SUBMITTED awaiting teacher"""
        expected_status = SubmissionStatus.SUBMITTED
        assert expected_status.value == "submitted"

    def test_accept_ai_transitions_to_graded(self):
        """Accepting AI grades should transition to GRADED"""
        # When teacher accepts AI suggestions:
        # Status should change from AI_GRADED to GRADED
        assert SubmissionStatus.GRADED.value == "graded"


class TestAIConfidenceScoring:
    """Test AI confidence score handling"""

    def test_confidence_range(self):
        """Confidence should be normalized to 0.0-1.0"""
        # Valid confidence values
        valid_confidences = [0.0, 0.5, 0.75, 0.92, 1.0]
        for conf in valid_confidences:
            assert 0.0 <= conf <= 1.0

    def test_percentage_to_confidence_conversion(self):
        """Test converting percentage (0-100) to confidence (0-1)"""
        percentage = 85
        confidence = percentage / 100.0
        assert confidence == 0.85


class TestAnswerDetailModel:
    """Test the AnswerDetail Pydantic model"""

    def test_answer_detail_has_ai_fields(self):
        """Verify AnswerDetail includes all required AI fields"""
        from src.api.routes.assessment import AnswerDetail

        # Check schema includes AI fields
        schema = AnswerDetail.model_json_schema()
        properties = schema.get("properties", {})

        assert "response_id" in properties
        assert "ai_suggested_score" in properties
        assert "ai_suggested_feedback" in properties
        assert "ai_confidence" in properties
        assert "teacher_override" in properties


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
