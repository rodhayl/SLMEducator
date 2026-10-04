"""Active single-provider configuration; retired preprocessing has no runtime path."""

from dataclasses import fields
from unittest.mock import MagicMock
from src.core.services.ai_service import AIService, RuntimeAIConfig


def test_runtime_config_keeps_only_active_options(monkeypatch):
    monkeypatch.setattr(AIService, "_setup_client", lambda self: setattr(self, "_client", MagicMock()))
    config = RuntimeAIConfig(provider="ollama", model="synthetic", temperature=0.2, max_tokens=321)
    service = AIService(config, MagicMock())
    assert service.config.model == "synthetic"
    assert service.config.max_tokens == 321 and service.config.temperature == 0.2
    assert "preprocessing_model" not in {field.name for field in fields(RuntimeAIConfig)}
    assert not hasattr(service, "_preprocess_context")
    service.close()
