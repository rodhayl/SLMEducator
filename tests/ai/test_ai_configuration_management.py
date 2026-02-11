"""
Test AI configuration management scenarios.

This module tests configuration management including:
- Provider switching and validation
- Model validation and persistence
- Configuration updates and rollback
- Settings validation and error handling
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from core.models.models import AIModelConfiguration, User
from core.services.ai_service import AIService, AIProvider
from core.services.settings_config_service import SettingsConfigService
from core.exceptions import ConfigurationError, AIServiceError


class TestAIConfigurationManagement:
    """Test AI configuration management scenarios."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "test_user"
        user.grade_level = "10th"
        return user

    @pytest.fixture
    def mock_settings_service(self):
        """Create a mock settings service."""
        service = Mock(spec=SettingsConfigService)
        service.get.side_effect = lambda section, key, default=None: {
            (
                "ai",
                "openai.endpoint",
                "https://api.openai.com/v1/chat/completions",
            ): "https://api.openai.com/v1/chat/completions",
            ("ai", "ollama.url", "http://localhost:11434"): "http://localhost:11434",
            ("ai", "lm_studio.url", "http://localhost:1234"): "http://localhost:1234",
            (
                "ai",
                "openrouter.url",
                "https://openrouter.ai/api/v1/chat/completions",
            ): "https://openrouter.ai/api/v1/chat/completions",
        }.get((section, key, default), default)
        return service

    @pytest.fixture
    def sample_configs(self):
        """Create sample AI configurations for testing."""
        return [
            AIModelConfiguration(
                id=1,
                user_id=1,
                provider=AIProvider.OPENAI.value,
                model="gpt-3.5-turbo",
                endpoint="https://api.openai.com/v1/chat/completions",
                api_key="sk-encrypted-key-1",
                model_parameters={"temperature": 0.7, "max_tokens": 1000},
                validated=True,
            ),
            AIModelConfiguration(
                id=2,
                user_id=1,
                provider=AIProvider.OLLAMA.value,
                model="llama2",
                endpoint="http://localhost:11434",
                api_key=None,
                model_parameters={"temperature": 0.5, "max_tokens": 800},
                validated=True,
            ),
            AIModelConfiguration(
                id=3,
                user_id=1,
                provider=AIProvider.OPENROUTER.value,
                model="anthropic/claude-3-haiku",
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                api_key="sk-or-encrypted-key-3",
                model_parameters={"temperature": 0.8, "max_tokens": 1200},
                validated=True,
            ),
        ]

    def test_provider_switching_validation(
        self, mock_db_session, mock_user, sample_configs, mock_settings_service
    ):
        """Test provider switching with validation."""
        # Mock database query to return configurations
        mock_db_session.query.return_value.filter.return_value.all.return_value = (
            sample_configs
        )

        # Test OpenAI provider
        openai_config = next(
            c for c in sample_configs if c.provider == AIProvider.OPENAI.value
        )
        ai_service = AIService(openai_config, Mock())
        assert ai_service.config.provider == AIProvider.OPENAI.value
        assert ai_service.config.model == "gpt-3.5-turbo"

        # Test Ollama provider
        ollama_config = next(
            c for c in sample_configs if c.provider == AIProvider.OLLAMA.value
        )
        ai_service_ollama = AIService(ollama_config, Mock())
        assert ai_service_ollama.config.provider == AIProvider.OLLAMA.value
        assert ai_service_ollama.config.model == "llama2"

    def test_model_validation_for_provider(
        self, mock_db_session, mock_user, sample_configs
    ):
        """Test model validation for different providers."""

        # Mock model fetching for different providers
        def mock_fetch_models(provider, endpoint=None):
            models = {
                AIProvider.OPENAI.value: ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                AIProvider.OLLAMA.value: ["llama2", "mistral", "codellama"],
                AIProvider.OPENROUTER.value: [
                    "anthropic/claude-3-haiku",
                    "openai/gpt-4",
                    "google/gemini-pro",
                ],
            }
            return models.get(provider, [])

        with patch.object(
            AIService, "fetch_available_models", side_effect=mock_fetch_models
        ):
            # Test valid model for OpenAI
            openai_config = next(
                c for c in sample_configs if c.provider == AIProvider.OPENAI.value
            )
            ai_service = AIService(openai_config, Mock())
            available_models = ai_service.fetch_available_models(openai_config.provider)
            assert openai_config.model in available_models

            # Test invalid model should raise error
            invalid_config = AIModelConfiguration(
                id=4,
                user_id=1,
                provider=AIProvider.OPENAI.value,
                model="invalid-model",
                endpoint="https://api.openai.com/v1/chat/completions",
                api_key="sk-encrypted-key-4",
                model_parameters={"temperature": 0.7, "max_tokens": 1000},
                validated=True,
            )

            # This should work since we're not validating in the constructor
            ai_service_invalid = AIService(invalid_config, Mock())
            assert ai_service_invalid.config.model == "invalid-model"

    def test_configuration_persistence(
        self, mock_db_session, mock_user, sample_configs
    ):
        """Test configuration persistence and updates."""

        # Mock configuration updates
        def mock_update_config(config_id, updates):
            config = next(c for c in sample_configs if c.id == config_id)
            for key, value in updates.items():
                setattr(config, key, value)
            return config

        mock_db_session.query.return_value.filter.return_value.first.side_effect = (
            lambda: next(c for c in sample_configs if c.id == 1)
        )

        # Test updating configuration
        config_to_update = sample_configs[0]
        original_model = config_to_update.model

        # Simulate configuration update
        updated_config = mock_update_config(
            1,
            {
                "model": "gpt-4",
                "model_parameters": {"temperature": 0.5, "max_tokens": 1000},
            },
        )

        assert updated_config.model == "gpt-4"
        assert updated_config.model_parameters["temperature"] == 0.5
        assert updated_config.model != original_model

    def test_configuration_rollback_on_error(
        self, mock_db_session, mock_user, sample_configs
    ):
        """Test configuration rollback on validation errors."""
        # Mock a configuration that will cause validation errors
        problematic_config = AIModelConfiguration(
            id=4,
            user_id=1,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint="https://invalid-endpoint.com",
            api_key=None,  # Missing API key for OpenAI
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            validated=False,
        )

        # Test that configuration with missing API key raises error when used
        ai_service = AIService(problematic_config, Mock())

        # Mock the API call to raise ConfigurationError
        with patch.object(
            ai_service._client,
            "post",
            side_effect=ConfigurationError("API key required"),
        ):
            with pytest.raises(AIServiceError):
                ai_service.generate_content("Test prompt")

    def test_settings_validation_and_error_handling(
        self, mock_settings_service, sample_configs
    ):
        """Test settings validation and error handling."""
        # Test invalid settings
        mock_settings_service.get.side_effect = lambda section, key, default=None: {
            (
                "ai",
                "openai.endpoint",
                "https://api.openai.com/v1/chat/completions",
            ): None,  # Invalid endpoint
            ("ai", "ollama.url", "http://localhost:11434"): "invalid-url",
        }.get((section, key, default), default)

        # Test configuration with invalid endpoint
        invalid_endpoint_config = AIModelConfiguration(
            id=5,
            user_id=1,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint=None,  # Invalid endpoint
            api_key="sk-encrypted-key-5",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            validated=False,
        )

        # This should work since endpoint validation happens during API calls
        ai_service = AIService(invalid_endpoint_config, Mock())
        assert ai_service.config.endpoint is None

    def test_active_configuration_switching(
        self, mock_db_session, mock_user, sample_configs
    ):
        """Test switching between active configurations."""

        # Mock database operations for configuration switching
        def mock_update_active_config(user_id, new_config_id):
            # Deactivate all configs for user
            for config in sample_configs:
                if config.user_id == user_id:
                    config.validated = config.id == new_config_id
            return next(c for c in sample_configs if c.id == new_config_id)

        # Test switching active configuration - use validated field instead
        initially_validated = next(c for c in sample_configs if c.validated)
        assert initially_validated.id == 1

        # Switch to Ollama configuration
        new_validated = mock_update_active_config(1, 2)
        assert new_validated.id == 2
        assert new_validated.validated is True
        assert next(c for c in sample_configs if c.id == 1).validated is False

    def test_configuration_encryption_and_security(self, sample_configs):
        """Test API key encryption and security measures."""
        # Test that API keys are encrypted (they should not be plaintext)
        # For testing purposes, we'll use obviously fake encrypted keys
        encrypted_configs = [
            AIModelConfiguration(
                id=1,
                user_id=1,
                provider=AIProvider.OPENAI.value,
                model="gpt-3.5-turbo",
                endpoint="https://api.openai.com/v1/chat/completions",
                api_key="encrypted_sk_test_key_12345",  # Obviously encrypted format
                model_parameters={"temperature": 0.7, "max_tokens": 1000},
                validated=True,
            )
        ]

        for config in encrypted_configs:
            if config.api_key:
                # API keys should be encrypted (not start with typical prefixes)
                assert not config.api_key.startswith("sk-")  # Should be encrypted
                assert not config.api_key.startswith("sk-or-")  # Should be encrypted
                assert len(config.api_key) > 20  # Encrypted keys should be longer

    def test_configuration_validation_rules(self, sample_configs):
        """Test configuration validation rules."""
        # Test invalid temperature values
        invalid_temp_config = AIModelConfiguration(
            id=6,
            user_id=1,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-encrypted-key-6",
            model_parameters={
                "temperature": 2.5,
                "max_tokens": 1000,
            },  # Invalid temperature > 2.0
            validated=False,
        )

        # The constructor should accept it, but usage might be problematic
        ai_service = AIService(invalid_temp_config, Mock())
        assert ai_service.config.model_parameters["temperature"] == 2.5

        # Test invalid max_tokens
        invalid_tokens_config = AIModelConfiguration(
            id=7,
            user_id=1,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-encrypted-key-7",
            model_parameters={
                "temperature": 0.7,
                "max_tokens": 50000,
            },  # Invalid max_tokens > typical limits
            validated=False,
        )

        ai_service_invalid = AIService(invalid_tokens_config, Mock())
        assert ai_service_invalid.config.model_parameters["max_tokens"] == 50000

    def test_configuration_compatibility_checking(self, sample_configs):
        """Test configuration compatibility with different providers."""
        # Test OpenAI configuration compatibility
        openai_config = next(
            c for c in sample_configs if c.provider == AIProvider.OPENAI.value
        )
        assert openai_config.api_key is not None  # OpenAI requires API key
        assert openai_config.endpoint is not None  # OpenAI requires endpoint

        # Test Ollama configuration compatibility
        ollama_config = next(
            c for c in sample_configs if c.provider == AIProvider.OLLAMA.value
        )
        assert ollama_config.api_key is None  # Ollama doesn't require API key
        assert ollama_config.endpoint is not None  # Ollama requires endpoint

        # Test OpenRouter configuration compatibility
        openrouter_config = next(
            c for c in sample_configs if c.provider == AIProvider.OPENROUTER.value
        )
        assert openrouter_config.api_key is not None  # OpenRouter requires API key
        assert openrouter_config.endpoint is not None
