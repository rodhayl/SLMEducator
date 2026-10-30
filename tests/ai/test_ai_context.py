import pytest
from unittest.mock import MagicMock, patch
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_settings():
    with patch("src.core.services.ai_service.get_settings_service") as mock:
        mock.return_value.get.return_value = "http://test-endpoint"
        yield mock


@pytest.fixture
def ai_service(mock_logger, mock_settings):
    config = RuntimeAIConfig(
        provider="ollama",
        model="llama3",
        preprocessing_model="llama3-tiny",
        enable_preprocessing=True,
    )
    service = AIService(config, mock_logger)
    service._client = MagicMock()
    try:
        yield service
    finally:
        try:
            service.close()
        except Exception:
            pass


def test_runtime_config_init(mock_logger, mock_settings):
    """Test initialization with RuntimeAIConfig"""
    config = RuntimeAIConfig(
        provider="ollama",
        model="llama3",
        preprocessing_model="llama3-tiny",
        enable_preprocessing=True,
    )
    service = AIService(config, mock_logger)
    assert service.config.model == "llama3"
    assert service.config.preprocessing_model == "llama3-tiny"
    assert service.config.enable_preprocessing is True


def test_preprocess_context_enabled(ai_service):
    """Test _preprocess_context when enabled"""
    # Mock the _call_ai method to return a mocked response
    mock_response = MagicMock()
    mock_response.content = "Summarized context"

    with patch.object(ai_service, "_call_ai", return_value=mock_response) as mock_call:
        result = ai_service._preprocess_context("Original long context for testing")

        # Should have called _call_ai with preprocessing prompt
        mock_call.assert_called_once()
        assert (
            "Summarize" in mock_call.call_args[1]["prompt"]
            or "Summarize" in mock_call.call_args[0][0]
        )
        assert result == "Summarized context"


def test_preprocess_context_disabled(mock_logger, mock_settings):
    """Test _preprocess_context when disabled"""
    config = RuntimeAIConfig(
        provider="ollama",
        model="llama3",
        preprocessing_model="llama3-tiny",
        enable_preprocessing=False,  # Disabled
    )
    service = AIService(config, mock_logger)

    # Should return original context when disabled
    original = "Original context string"
    result = service._preprocess_context(original)
    assert result == original


def test_preprocess_context_no_model(mock_logger, mock_settings):
    """Test _preprocess_context when no preprocessing model configured"""
    config = RuntimeAIConfig(
        provider="ollama",
        model="llama3",
        preprocessing_model=None,  # No preprocessing model
        enable_preprocessing=True,
    )
    service = AIService(config, mock_logger)

    # Should return original context when no preprocessing model
    original = "Original context string"
    result = service._preprocess_context(original)
    assert result == original
