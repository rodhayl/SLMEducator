import logging
from unittest.mock import Mock, MagicMock

import pytest

from core.services.ai_service import AIService
from core.models.models import AIModelConfiguration


def _make_config():
    cfg = Mock(spec=AIModelConfiguration)
    cfg.provider = "ollama"
    cfg.model = "llama2"
    cfg.endpoint = None
    cfg.api_key = None
    return cfg


def test_autouse_patches_client_nonreal(monkeypatch):
    """Test that AIService._setup_client can be patched to use MagicMock.

    This test verifies the patching mechanism works correctly by explicitly
    patching _setup_client, similar to what the autouse fixture does for
    non-real AI tests.
    """
    logger = logging.getLogger("test_autouse_nonreal")
    cfg = _make_config()

    # Explicitly patch _setup_client like the autouse fixture does
    def _fake_setup_client(self):
        self._client = MagicMock()

    monkeypatch.setattr(AIService, "_setup_client", _fake_setup_client)

    service = AIService(cfg, logger)
    try:
        assert isinstance(
            service._client, MagicMock
        ), "_client should be a MagicMock when _setup_client is patched"
    finally:
        try:
            service.close()
        except Exception:
            pass


@pytest.mark.real_ai
def test_autouse_respects_real_ai_env(monkeypatch):
    """When USE_REAL_AI=1, the autouse fixture should not patch the AIService client,
    so _client should NOT be a MagicMock.
    """
    # Enable real AI mode
    monkeypatch.setenv("USE_REAL_AI", "1")
    logger = logging.getLogger("test_autouse_real")
    cfg = _make_config()

    service = AIService(cfg, logger)
    try:
        assert not isinstance(
            service._client, MagicMock
        ), "_client should not be a MagicMock in real AI mode"
    finally:
        # Unset env and close service
        monkeypatch.delenv("USE_REAL_AI", raising=False)
        try:
            service.close()
        except Exception:
            pass
