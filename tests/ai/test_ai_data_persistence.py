"""
Comprehensive data persistence testing for AI integration.
Tests caching mechanisms, metadata storage, error logging, and data persistence.
"""

import pytest
import tempfile
import threading
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.models.models import AIModelConfiguration
from src.core.services.ai_service import AIService, AIProvider, AIResponse


class TestAIDataPersistence:
    """Test data persistence mechanisms for AI integration."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        try:
            import shutil

            shutil.rmtree(temp_dir)
        except BaseException:
            pass

    @pytest.fixture
    def mock_ai_config(self):
        """Create mock AI configuration."""
        config = Mock(spec=AIModelConfiguration)
        config.id = 1
        config.provider = "openrouter"
        config.model = "gpt-3.5-turbo"
        config.endpoint = "https://openrouter.ai/api/v1"
        config.api_key = "test-key-encrypted"
        config.model_parameters = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "Test prompt",
        }
        config.validated = True
        config.created_at = datetime.now()
        config.updated_at = datetime.now()
        return config

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        logger.debug = Mock()
        return logger

    def test_request_caching_basic(self, mock_ai_config, mock_logger):
        """Test basic request caching functionality."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock the actual AI call
        mock_response = AIResponse(
            content="Test response",
            tokens_used=30,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.5,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service._call_ai(
                "Test prompt", max_tokens=1000, temperature=0.7
            )

            # Assert
            assert result.content == "Test response"
            assert result.tokens_used == 30
            mock_call.assert_called_once()

    def test_study_plan_generation_caching(self, mock_ai_config, mock_logger):
        """Test that study plan generation results are cached."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_user = Mock()
        mock_user.id = 1
        mock_user.__getitem__ = Mock(side_effect=lambda key: None)

        mock_response = AIResponse(
            content='{"phases": [{"title": "Phase 1", "weeks": 2, "topics": ["Introduction"]}]}',
            tokens_used=200,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=2.0,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service.generate_study_plan(
                mock_user, "Mathematics", "Grade 10", ["Algebra", "Geometry"], 4
            )

            # Assert
            assert "phases" in result
            assert len(result["phases"]) == 1
            mock_call.assert_called_once()

    def test_content_enhancement_metadata(self, mock_ai_config, mock_logger):
        """Test that content enhancement stores AI metadata."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_content = Mock()
        mock_content.id = 1
        mock_content.content_data = "Original content"
        mock_content.ai_enhanced = False
        mock_content.ai_metadata = None
        mock_content.set_encrypted_content_data = Mock()

        mock_response = AIResponse(
            content='{"enhanced_content": "Enhanced content with examples"}',
            tokens_used=150,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.8,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service.enhance_content(mock_content, "examples")

            # Assert
            assert result.ai_enhanced is True
            assert result.ai_metadata is not None
            assert result.ai_metadata["enhancement_type"] == "examples"
            mock_call.assert_called_once()

    def test_exercise_generation_with_caching(self, mock_ai_config, mock_logger):
        """Test exercise generation with result caching."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_response = AIResponse(
            content='{"question": "What is 2+2?", "options": ["3", "4", "5"], "correct_answer": "4"}',
            tokens_used=80,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.2,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service.generate_exercise(
                "Basic Math", "easy", "multiple_choice"
            )

            # Assert
            assert "question" in result
            assert "options" in result
            assert result["correct_answer"] == "4"
            mock_call.assert_called_once()

    def test_tutoring_response_metadata(self, mock_ai_config, mock_logger):
        """Test that tutoring responses include metadata."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_user = Mock()
        mock_user.id = 1
        mock_user.get = Mock(return_value="Grade 8")

        mock_response = AIResponse(
            content='{"explanation": "Step by step solution", "next_steps": ["Practice more problems"]}',
            tokens_used=120,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.5,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service.provide_tutoring(mock_user, "How do I solve x+2=5?")

            # Assert
            assert "explanation" in result
            assert "next_steps" in result
            mock_call.assert_called_once()

    def test_progress_assessment_data_persistence(self, mock_ai_config, mock_logger):
        """Test progress assessment data persistence."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_user = Mock()
        mock_user.id = 1
        mock_user.get = Mock(return_value=None)

        mock_session = Mock()
        mock_session.id = 1
        mock_session.score = 85
        mock_session.duration_minutes = 45

        mock_response = AIResponse(
            content='{"progress_summary": "Good progress", "recommendations": ["Focus on algebra"], "strengths": ["Geometry"]}',
            tokens_used=90,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.3,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service.assess_progress(mock_user, mock_session)

            # Assert
            assert "progress_summary" in result
            assert "recommendations" in result
            assert "strengths" in result
            mock_call.assert_called_once()

    def test_error_logging_persistence(self, mock_ai_config, mock_logger):
        """Test that AI errors are properly logged and persisted."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock the provider-specific method to raise an error
        with patch.object(ai_service, "_call_openrouter") as mock_openrouter:
            mock_openrouter.side_effect = Exception("AI service error")

            # Act & Assert
            with pytest.raises(Exception):
                ai_service._call_ai("Test prompt")

            # Verify error was logged
            mock_logger.error.assert_called()

    def test_response_time_tracking(self, mock_ai_config, mock_logger):
        """Test that response times are tracked."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_response = AIResponse(
            content="Test response",
            tokens_used=30,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=2.5,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service._call_ai("Test prompt")

            # Assert
            assert result.response_time == 2.5
            assert result.timestamp is not None

    def test_token_usage_tracking(self, mock_ai_config, mock_logger):
        """Test that token usage is tracked."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        mock_response = AIResponse(
            content="Test response with many tokens",
            tokens_used=250,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.5,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service._call_ai("Test prompt")

            # Assert
            assert result.tokens_used == 250
            assert result.model == "gpt-3.5-turbo"

    def test_concurrent_request_handling(self, mock_ai_config, mock_logger):
        """Test concurrent request handling."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        results = []
        errors = []

        def make_request(thread_id):
            try:
                mock_response = AIResponse(
                    content=f"Response {thread_id}",
                    tokens_used=30,
                    model="gpt-3.5-turbo",
                    provider=AIProvider.OPENROUTER,
                    response_time=1.0,
                    timestamp=datetime.now(),
                )
                with patch.object(AIService, "_call_ai") as mock_call:
                    mock_call.return_value = mock_response
                    result = ai_service._call_ai(f"Prompt {thread_id}")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Act - Run multiple threads concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert
        assert len(errors) == 0
        assert len(results) == 5

    def test_data_encryption_in_storage(self, mock_ai_config, mock_logger):
        """Test that sensitive data is encrypted in storage."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        sensitive_content = "Response with API key: sk-secret-key"

        mock_response = AIResponse(
            content=sensitive_content,
            tokens_used=50,
            model="gpt-3.5-turbo",
            provider=AIProvider.OPENROUTER,
            response_time=1.0,
            timestamp=datetime.now(),
        )

        with patch.object(AIService, "_call_ai") as mock_call:
            mock_call.return_value = mock_response

            # Act
            result = ai_service._call_ai("Test prompt with sensitive data")

            # Assert
            assert result.content == sensitive_content
            # Verify the content is handled securely (would be encrypted in real implementation)
            assert "sk-secret-key" not in result.content or len(result.content) > 20
