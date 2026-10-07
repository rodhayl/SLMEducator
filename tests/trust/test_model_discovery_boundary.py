"""Model catalogs keep synthetic credentials bound to their saved provider."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import dependencies
from src.api.routes import settings
from src.api.security import get_current_user
from src.core.exceptions import AIServiceError
from src.core.models import AIModelConfiguration, User, UserRole
from src.core.services.ai_service import AIProvider, AIService, RuntimeAIConfig

PROVIDERS = ("openai", "openrouter", "ollama", "lm_studio")
CLOUD = ("openai", "openrouter")
KEY = "synthetic-provider-bound-key"
PAYLOAD = {"data": [{"id": "gpt-synthetic"}], "models": [{"name": "gpt-synthetic"}]}


@pytest.fixture
def discovery(monkeypatch, db_session):
    """Expose the actual settings route with disposable rows and fake transport."""
    user = User(username="catalog-owner", email="catalog@example.invalid",
                first_name="Synthetic", last_name="Catalog", role=UserRole.TEACHER,
                password_hash="unused-test-hash")
    db_session.add(user)
    db_session.commit()
    services = []

    def setup_client(service):
        service._client = MagicMock()
        service._client.get.return_value.json.return_value = PAYLOAD
        services.append(service)

    monkeypatch.setattr(AIService, "_setup_client", setup_client)
    app = FastAPI()
    app.include_router(settings.router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[dependencies.get_db] = lambda: db_session
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=db_session, user=user, services=services)
    for service in services:
        service.close()


def save_config(discovery, provider, endpoint=None, key=KEY):
    """Save only synthetic provider configuration through the supported route."""
    response = discovery.client.post("/api/settings/ai", json={
        "provider": provider, "model": "synthetic", "endpoint": endpoint, "api_key": key,
    })
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("configured", PROVIDERS)
@pytest.mark.parametrize("requested", PROVIDERS)
@pytest.mark.parametrize("key", [KEY, None])
def test_route_discovery_provider_and_key_matrix(discovery, configured, requested, key):
    save_config(discovery, configured, key=key)
    response = discovery.client.get(f"/api/settings/ai/models?provider={requested}")
    if configured != requested:
        assert response.status_code == 409, response.text
        assert not discovery.services
    elif configured in CLOUD and key is None:
        assert response.status_code == 500, response.text
        assert "key is required" in response.json()["detail"]
        discovery.services[0]._client.get.assert_not_called()
    else:
        assert response.status_code == 200, response.text
        assert response.json() == {"models": ["gpt-synthetic"], "provider": requested}
        headers = discovery.services[0]._client.get.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == (f"Bearer {KEY}" if requested in CLOUD else None)
    assert KEY not in response.text


@pytest.mark.parametrize("provider", ["unknown", "anthropic"])
def test_unknown_or_retired_provider_never_constructs_service(discovery, provider):
    save_config(discovery, "openai")
    result = discovery.client.get(f"/api/settings/ai/models?provider={provider}")
    assert result.status_code == (400 if provider == "unknown" else 422)
    assert not discovery.services


@pytest.mark.parametrize("provider", PROVIDERS)
def test_omitted_provider_uses_saved_provider(discovery, provider):
    save_config(discovery, provider)
    response = discovery.client.get("/api/settings/ai/models")
    assert response.status_code == 200, response.text
    assert response.json()["provider"] == provider


@pytest.mark.parametrize("provider", PROVIDERS)
def test_unsaved_defaults_use_actual_configured_provider(discovery, monkeypatch, provider):
    def default(user_id):
        return AIModelConfiguration(user_id=user_id, provider=provider, model="synthetic",
                                    endpoint="https://default.example.invalid/v1")

    monkeypatch.setattr(settings, "default_ai_configuration", default)
    monkeypatch.setattr(dependencies, "default_ai_configuration", default)
    response = discovery.client.get("/api/settings/ai/models")
    if provider in CLOUD:
        assert response.status_code == 500
        assert "key is required" in response.json()["detail"]
        discovery.services[0]._client.get.assert_not_called()
    else:
        assert response.status_code == 200, response.text
        assert response.json()["provider"] == provider
        assert discovery.services[0]._client.get.call_args.args[0].startswith("https://default.example.invalid/")
    assert discovery.db.query(AIModelConfiguration).count() == 0


@pytest.mark.parametrize("configured", PROVIDERS)
@pytest.mark.parametrize("requested", PROVIDERS)
def test_service_rejects_cross_provider_even_with_explicit_endpoint(configured, requested):
    service = AIService(RuntimeAIConfig(configured, "synthetic", api_key=KEY), logging.getLogger(__name__))
    service._client.get.return_value.json.return_value = PAYLOAD
    try:
        if configured != requested:
            with pytest.raises(AIServiceError, match="configured provider"):
                service.fetch_available_models(AIProvider(requested), "https://requested.example.invalid/v1")
            service._client.get.assert_not_called()
        else:
            assert service.fetch_available_models(AIProvider(requested), "https://requested.example.invalid/v1") == ["gpt-synthetic"]
    finally:
        service.close()


ENDPOINTS = [
    (provider, suffix, "/v1/models")
    for provider in ("openai", "lm_studio")
    for suffix in ("", "/", "/v1", "/v1/", "/v1/chat/completions", "/v1/chat/completions/")
] + [
    ("openrouter", suffix, "/api/v1/models")
    for suffix in ("/api/v1", "/api/v1/", "/api/v1/chat/completions", "/api/v1/chat/completions/")
] + [
    ("ollama", suffix, "/api/tags")
    for suffix in ("", "/", "/api/generate", "/api/generate/")
]


@pytest.mark.parametrize("provider,suffix,expected", ENDPOINTS)
def test_saved_endpoint_aliases_remain_on_saved_destination(discovery, provider, suffix, expected):
    base = "https://saved.example.invalid/custom"
    save_config(discovery, provider, endpoint=base + suffix)
    response = discovery.client.get(f"/api/settings/ai/models?provider={provider}")
    assert response.status_code == 200, response.text
    call = discovery.services[0]._client.get.call_args
    assert call.args[0] == base + expected


@pytest.mark.parametrize("provider", CLOUD)
def test_missing_key_does_not_fall_back_to_general_or_provider_setting(discovery, monkeypatch, provider):
    save_config(discovery, provider, key=None)
    runtime_settings = MagicMock()
    runtime_settings.get.return_value = "synthetic-system-key-must-not-be-used"
    monkeypatch.setattr("src.core.services.ai_service.get_settings_service", lambda: runtime_settings)
    response = discovery.client.get(f"/api/settings/ai/models?provider={provider}")
    assert response.status_code == 500, response.text
    discovery.services[0]._client.get.assert_not_called()
    assert "synthetic-system-key" not in response.text


@pytest.mark.parametrize("transport_fails", [False, True])
def test_route_closes_provider_client_after_success_or_failure(discovery, monkeypatch, transport_fails):
    save_config(discovery, "openai")

    def service_for_user(user, db):
        service = dependencies.get_ai_service_dependency(user, db)
        if transport_fails:
            service._client.get.side_effect = RuntimeError("synthetic transport failure")
        return service

    monkeypatch.setattr(settings, "get_ai_service_dependency", service_for_user)
    response = discovery.client.get("/api/settings/ai/models?provider=openai")
    assert response.status_code == (500 if transport_fails else 200), response.text
    discovery.services[0]._client.close.assert_called_once_with()


def test_service_guard_blocks_config_change_between_route_reads(discovery, monkeypatch):
    save_config(discovery, "openai")
    different = AIService(RuntimeAIConfig("openrouter", "synthetic", api_key=KEY), logging.getLogger(__name__))
    monkeypatch.setattr(settings, "get_ai_service_dependency", lambda user, db: different)
    response = discovery.client.get("/api/settings/ai/models?provider=openai")
    assert response.status_code == 500, response.text
    assert "configured provider" in response.json()["detail"]
    different._client.get.assert_not_called()
    different._client.close.assert_called_once_with()
