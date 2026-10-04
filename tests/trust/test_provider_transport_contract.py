"""Real provider adapters exercised with synthetic HTTP responses, never sockets."""

import logging
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.exceptions import AIServiceError
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def provider_service():
    services = []

    def make(provider, endpoint="https://synthetic.invalid/v1", **options):
        service = AIService(
            RuntimeAIConfig(
                provider=provider,
                model="synthetic-model",
                api_key="synthetic-adapter-token",
                endpoint=endpoint,
                **options
            ),
            logging.getLogger(__name__),
        )
        service._client = MagicMock()
        services.append(service)
        return service

    yield make
    for service in services:
        service.close()


def reply(data, status=200, headers=None):
    return httpx.Response(
        status,
        json=data,
        headers=headers,
        request=httpx.Request("POST", "https://synthetic.invalid/"),
    )


@pytest.mark.parametrize("provider", ["openai", "openrouter", "lm_studio", "ollama"])
@pytest.mark.parametrize("system", [None, "Synthetic instruction"])
def test_adapters_deliver_configured_limits_and_report_real_usage(
    provider_service, provider, system
):
    service = provider_service(provider, max_tokens=321, temperature=0.25)
    data = {
        "model": "served-model",
        "choices": [{"message": {"content": "Synthetic answer"}}],
        "usage": {"total_tokens": 12},
    }
    if provider == "ollama":
        data = {"response": "Synthetic answer", "prompt_eval_count": 7, "eval_count": 5}
    service._client.post.return_value = reply(data)
    result = service._call_ai("Question", max_tokens=1200, temperature=0.8, system_prompt=system)
    call = service._client.post.call_args
    body = call.kwargs["json"]
    assert result.content == "Synthetic answer" and result.tokens_used == 12
    assert service.last_response is result
    if provider == "ollama":
        assert body["options"] == {"temperature": 0.25, "num_predict": 321}
        assert body["stream"] is False
        assert call.args[0].endswith("/api/generate")
        assert body.get("system") == system
    else:
        assert body["max_tokens"] == 321 and body["temperature"] == 0.25
        assert body["messages"][-1] == {"role": "user", "content": "Question"}
        assert len(body["messages"]) == (2 if system else 1)
        if provider == "lm_studio":
            assert call.args[0] == "https://synthetic.invalid/v1/chat/completions"
        else:
            assert call.kwargs["headers"]["Authorization"] == "Bearer synthetic-adapter-token"


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
@pytest.mark.parametrize(
    "usage,expected", [({"input_tokens": 3, "output_tokens": 4}, 7), ({}, 0), (None, 0)]
)
def test_alternate_or_missing_provider_usage_is_not_invented(
    provider_service, provider, usage, expected
):
    service = provider_service(provider)
    service._client.post.return_value = reply(
        {"model": "synthetic", "choices": [{"message": {"content": "Answer"}}], "usage": usage}
    )
    assert service._call_ai("Question").tokens_used == expected


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_cloud_adapter_requires_credential_before_transport(provider_service, provider):
    service = provider_service(provider)
    service.config.api_key = None
    with pytest.raises(AIServiceError, match="key not configured"):
        service._call_ai("Question")
    service._client.post.assert_not_called()


@pytest.mark.parametrize(
    "status,expected",
    [
        (429, "Rate limit"),
        (401, "Authentication"),
        (403, "forbidden"),
        (503, "temporarily unavailable"),
        (502, "server error"),
        (400, "Invalid synthetic input"),
    ],
)
def test_openrouter_status_failures_remain_errors(provider_service, status, expected):
    service = provider_service("openrouter")
    service._client.post.return_value = reply(
        {"error": {"message": "Invalid synthetic input"}}, status, {"retry-after": "11"}
    )
    with pytest.raises(AIServiceError, match=expected):
        service._call_ai("Question")
    assert not hasattr(service, "last_response")


@pytest.mark.parametrize(
    "failure,expected",
    [
        (httpx.ReadTimeout("slow"), "timed out"),
        (httpx.ConnectError("offline"), "connect"),
        (ValueError("invalid JSON"), "invalid JSON"),
    ],
)
def test_openrouter_transport_and_parse_errors_never_become_answers(
    provider_service, failure, expected
):
    service = provider_service("openrouter")
    service._client.post.side_effect = failure
    with pytest.raises(AIServiceError, match=expected):
        service._call_ai("Question")


@pytest.mark.parametrize("provider", ["openai", "openrouter", "lm_studio", "ollama"])
def test_model_discovery_normalizes_supported_endpoints_and_sorts(provider_service, provider):
    endpoint = "https://synthetic.invalid/v1"
    if provider == "openai":
        endpoint = "https://synthetic.invalid"
    if provider == "openrouter":
        endpoint = "https://synthetic.invalid/v1/chat/completions"
    service = provider_service(provider)
    payload = {"data": [{"id": "gpt-z"}, {"id": "gpt-a"}]}
    if provider == "ollama":
        payload = {"models": [{"name": "gpt-z"}, {"name": "gpt-a"}]}
    service._client.get.return_value = reply(payload)
    assert service.fetch_available_models(base_url=endpoint) == ["gpt-a", "gpt-z"]
    url = service._client.get.call_args.args[0]
    assert "/v1/v1" not in url and "/chat/completions/models" not in url
    assert url.endswith("/api/tags" if provider == "ollama" else "/v1/models")


@pytest.mark.parametrize("provider", ["openai", "openrouter", "lm_studio", "ollama"])
def test_model_discovery_failure_is_actionable(provider_service, provider):
    service = provider_service(provider)
    service._client.get.side_effect = httpx.ConnectError("synthetic offline")
    with pytest.raises(AIServiceError, match="fetching failed"):
        service.fetch_available_models(base_url="https://synthetic.invalid")


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_model_discovery_requires_cloud_credential(provider_service, provider):
    service = provider_service(provider)
    service.config.api_key = None
    with pytest.raises(AIServiceError, match="key is required"):
        service.fetch_available_models()
    service._client.get.assert_not_called()


def test_retired_provider_cannot_reach_transport(provider_service):
    service = provider_service("anthropic")
    with pytest.raises(AIServiceError, match="Unsupported"):
        service._call_ai("Question")
    with pytest.raises(AIServiceError, match="Unsupported"):
        service.fetch_available_models()
    service._client.post.assert_not_called()
    service._client.get.assert_not_called()
