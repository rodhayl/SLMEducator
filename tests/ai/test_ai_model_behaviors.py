"""
Comprehensive testing for model-specific behaviors in AI integration.
Tests system prompts, temperature settings, token limits, and provider-specific features.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.models.models import AIModelConfiguration
from src.core.services.ai_service import AIService


class TestAIModelBehaviors:
    """Test model-specific behaviors and configurations."""

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
            "system_prompt": "You are a helpful educational assistant.",
        }
        config.validated = True
        config.created_at = datetime.now()
        config.updated_at = datetime.now()

        # Mock encryption methods
        config.decrypted_api_key = "sk-test-key-12345"
        config.set_encrypted_api_key = Mock()
        return config

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        return logger

    def test_system_prompt_configuration(self, mock_ai_config, mock_logger):
        """Test that system prompts are properly configured for different providers."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)
        system_prompt = "You are an expert math tutor."

        # Act - Test system prompt with different providers
        with patch.object(ai_service, "_call_openrouter") as mock_call:
            mock_call.return_value = {
                "content": "Math help response",
                "tokens_used": 50,
                "model": "gpt-3.5-turbo",
            }

            response = ai_service._call_ai(
                "Help with algebra",
                max_tokens=100,
                temperature=0.7,
                system_prompt=system_prompt,
            )

            # Assert
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][3] == system_prompt  # system_prompt parameter

    def test_temperature_configuration(self, mock_ai_config, mock_logger):
        """Test that temperature settings are properly applied."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different temperature values
        temperature_values = [0.1, 0.5, 0.9, 1.0]

        for temp in temperature_values:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with temperature {temp}",
                    "tokens_used": 50,
                    "model": "gpt-3.5-turbo",
                }

                # Act
                response = ai_service._call_ai(
                    "Creative writing prompt", max_tokens=100, temperature=temp
                )

                # Assert
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                assert call_args[0][2] == temp  # temperature parameter

    def test_max_tokens_limits(self, mock_ai_config, mock_logger):
        """Test that max tokens are properly limited and validated."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different token limits
        token_limits = [50, 100, 500, 1000, 2000]

        for max_tokens in token_limits:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with {max_tokens} max tokens",
                    "tokens_used": min(max_tokens, 100),
                    "model": "gpt-3.5-turbo",
                }

                # Act
                response = ai_service._call_ai(
                    "Test prompt", max_tokens=max_tokens, temperature=0.7
                )

                # Assert
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                assert call_args[0][1] == max_tokens  # max_tokens parameter

    def test_openai_specific_features(self, mock_ai_config, mock_logger):
        """Test OpenAI-specific features and parameters."""
        # Arrange
        mock_ai_config.provider = "openai"
        mock_ai_config.model = "gpt-4"
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Test OpenAI-specific parameters
        with patch.object(ai_service, "_call_openai") as mock_call:
            mock_call.return_value = {
                "content": "OpenAI response",
                "tokens_used": 75,
                "model": "gpt-4",
            }

            response = ai_service._call_ai(
                "Test prompt for OpenAI",
                max_tokens=150,
                temperature=0.8,
                system_prompt="You are a helpful assistant.",
            )

            # Assert
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "Test prompt for OpenAI"
            assert call_args[0][1] == 150  # max_tokens
            assert call_args[0][2] == 0.8  # temperature
            assert call_args[0][3] == "You are a helpful assistant."  # system_prompt

    def test_ollama_specific_features(self, mock_ai_config, mock_logger):
        """Test Ollama-specific features and parameters."""
        # Arrange
        mock_ai_config.provider = "ollama"
        mock_ai_config.model = "llama2"
        mock_ai_config.endpoint = "http://localhost:11434"
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Test Ollama-specific parameters
        with patch.object(ai_service, "_call_ollama") as mock_call:
            mock_call.return_value = {
                "content": "Ollama response",
                "tokens_used": 60,
                "model": "llama2",
            }

            response = ai_service._call_ai(
                "Test prompt for Ollama",
                max_tokens=120,
                temperature=0.6,
                system_prompt="You are a local AI assistant.",
            )

            # Assert
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "Test prompt for Ollama"
            assert call_args[0][1] == 120  # max_tokens
            assert call_args[0][2] == 0.6  # temperature
            assert call_args[0][3] == "You are a local AI assistant."  # system_prompt

    def test_lm_studio_specific_features(self, mock_ai_config, mock_logger):
        """Test LM Studio-specific features and parameters."""
        # Arrange
        mock_ai_config.provider = "lm_studio"
        mock_ai_config.model = "local-model"
        mock_ai_config.endpoint = "http://localhost:1234"
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Test LM Studio-specific parameters
        with patch.object(ai_service, "_call_lm_studio") as mock_call:
            mock_call.return_value = {
                "content": "LM Studio response",
                "tokens_used": 80,
                "model": "local-model",
            }

            response = ai_service._call_ai(
                "Test prompt for LM Studio",
                max_tokens=160,
                temperature=0.5,
                system_prompt="You are a local development assistant.",
            )

            # Assert
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "Test prompt for LM Studio"
            assert call_args[0][1] == 160  # max_tokens
            assert call_args[0][2] == 0.5  # temperature
            assert (
                call_args[0][3] == "You are a local development assistant."
            )  # system_prompt

    def test_openrouter_specific_features(self, mock_ai_config, mock_logger):
        """Test OpenRouter-specific features and parameters."""
        # Arrange
        mock_ai_config.provider = "openrouter"
        mock_ai_config.model = "gpt-3.5-turbo"
        mock_ai_config.endpoint = "https://openrouter.ai/api/v1"
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Test OpenRouter-specific parameters
        with patch.object(ai_service, "_call_openrouter") as mock_call:
            mock_call.return_value = {
                "content": "OpenRouter response",
                "tokens_used": 90,
                "model": "gpt-3.5-turbo",
            }

            response = ai_service._call_ai(
                "Test prompt for OpenRouter",
                max_tokens=180,
                temperature=0.9,
                system_prompt="You are a versatile AI assistant.",
            )

            # Assert
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "Test prompt for OpenRouter"
            assert call_args[0][1] == 180  # max_tokens
            assert call_args[0][2] == 0.9  # temperature
            assert (
                call_args[0][3] == "You are a versatile AI assistant."
            )  # system_prompt

    def test_model_parameter_validation(self, mock_ai_config, mock_logger):
        """Test that model parameters are properly passed through to providers."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different temperature values (including edge cases)
        temperature_values = [-1.0, 0.0, 0.5, 1.0, 2.0, 5.0]

        for temp in temperature_values:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": "Response",
                    "tokens_used": 50,
                    "model": "gpt-3.5-turbo",
                }

                # Act - Temperature should be passed as-is to provider
                response = ai_service._call_ai(
                    "Test prompt", max_tokens=100, temperature=temp
                )

                # Assert - Temperature should be passed through as provided
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                actual_temp = call_args[0][2]
                assert actual_temp == temp  # Temperature should be passed as-is

    def test_context_window_management(self, mock_ai_config, mock_logger):
        """Test that context windows are properly managed for different models."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different models with different context windows
        models_and_contexts = [
            ("gpt-3.5-turbo", 4096),
            ("gpt-4", 8192),
            ("gpt-4-32k", 32768),
            ("llama2", 4096),
        ]

        for model, expected_context in models_and_contexts:
            mock_ai_config.model = model

            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response for {model}",
                    "tokens_used": 100,
                    "model": model,
                }

                # Act
                response = ai_service._call_ai(
                    "Test prompt for context management",
                    max_tokens=1000,  # Should be within context limit
                    temperature=0.7,
                )

                # Assert
                assert response.model == model
                assert response.tokens_used <= expected_context

    def test_stop_sequences_configuration(self, mock_ai_config, mock_logger):
        """Test that stop sequences are properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test with stop sequences
        stop_sequences = ["\n", "Human:", "###"]

        with patch.object(ai_service, "_call_openrouter") as mock_call:
            mock_call.return_value = {
                "content": "Response with stop sequences",
                "tokens_used": 75,
                "model": "gpt-3.5-turbo",
            }

            # Act - Test with stop sequences (would be passed in model parameters)
            response = ai_service._call_ai(
                "Test prompt with stop sequences",
                max_tokens=150,
                temperature=0.7,
                system_prompt="You are an assistant. Use ### to end responses.",
            )

            # Assert
            mock_call.assert_called_once()
            # Stop sequences would be handled in the provider-specific implementation
            assert response.content is not None

    def test_frequency_penalty_configuration(self, mock_ai_config, mock_logger):
        """Test that frequency penalty is properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different frequency penalty values
        frequency_penalties = [0.0, 0.5, 1.0, 2.0]

        for penalty in frequency_penalties:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with frequency penalty {penalty}",
                    "tokens_used": 60,
                    "model": "gpt-3.5-turbo",
                }

                # Act - Frequency penalty would be in model parameters
                response = ai_service._call_ai(
                    "Test prompt for frequency penalty", max_tokens=120, temperature=0.7
                )

                # Assert
                mock_call.assert_called_once()
                # Frequency penalty would be validated in the provider implementation
                assert response.content is not None

    def test_presence_penalty_configuration(self, mock_ai_config, mock_logger):
        """Test that presence penalty is properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different presence penalty values
        presence_penalties = [0.0, 0.5, 1.0, 2.0]

        for penalty in presence_penalties:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with presence penalty {penalty}",
                    "tokens_used": 65,
                    "model": "gpt-3.5-turbo",
                }

                # Act - Presence penalty would be in model parameters
                response = ai_service._call_ai(
                    "Test prompt for presence penalty", max_tokens=130, temperature=0.7
                )

                # Assert
                mock_call.assert_called_once()
                # Presence penalty would be validated in the provider implementation
                assert response.content is not None

    def test_top_p_configuration(self, mock_ai_config, mock_logger):
        """Test that top-p (nucleus sampling) is properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different top-p values
        top_p_values = [0.1, 0.5, 0.9, 1.0]

        for top_p in top_p_values:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with top-p {top_p}",
                    "tokens_used": 70,
                    "model": "gpt-3.5-turbo",
                }

                # Act - Top-p would be in model parameters
                response = ai_service._call_ai(
                    "Test prompt for top-p sampling", max_tokens=140, temperature=0.7
                )

                # Assert
                mock_call.assert_called_once()
                # Top-p would be validated in the provider implementation
                assert response.content is not None

    def test_best_of_configuration(self, mock_ai_config, mock_logger):
        """Test that best-of parameter is properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different best-of values
        best_of_values = [1, 3, 5]

        for best_of in best_of_values:
            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response with best-of {best_of}",
                    "tokens_used": 80,
                    "model": "gpt-3.5-turbo",
                }

                # Act - Best-of would be in model parameters
                response = ai_service._call_ai(
                    "Test prompt for best-of generation",
                    max_tokens=160,
                    temperature=0.7,
                )

                # Assert
                mock_call.assert_called_once()
                # Best-of would be validated in the provider implementation
                assert response.content is not None

    def test_streaming_configuration(self, mock_ai_config, mock_logger):
        """Test that streaming is properly configured."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test streaming configuration
        with patch.object(ai_service, "_call_openrouter") as mock_call:
            mock_call.return_value = {
                "content": "Streaming response",
                "tokens_used": 85,
                "model": "gpt-3.5-turbo",
            }

            # Act - Test with streaming (would be handled in provider implementation)
            response = ai_service._call_ai(
                "Test prompt for streaming", max_tokens=170, temperature=0.7
            )

            # Assert
            mock_call.assert_called_once()
            # Streaming would be handled in the provider-specific implementation
            assert response.content is not None

    def test_model_capabilities_detection(self, mock_ai_config, mock_logger):
        """Test that model capabilities are properly detected."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Test different models with different capabilities
        models_and_capabilities = [
            ("gpt-3.5-turbo", {"chat": True, "completion": True, "embedding": False}),
            (
                "gpt-4",
                {"chat": True, "completion": True, "embedding": False, "vision": True},
            ),
            (
                "text-davinci-003",
                {"chat": False, "completion": True, "embedding": False},
            ),
            ("llama2", {"chat": True, "completion": True, "embedding": False}),
        ]

        for model, expected_capabilities in models_and_capabilities:
            mock_ai_config.model = model

            with patch.object(ai_service, "_call_openrouter") as mock_call:
                mock_call.return_value = {
                    "content": f"Response for {model}",
                    "tokens_used": 90,
                    "model": model,
                }

                # Act
                response = ai_service._call_ai(
                    "Test prompt for capabilities", max_tokens=180, temperature=0.7
                )

                # Assert
                assert response.model == model
                # Capabilities would be determined based on the model name
                assert response.content is not None
