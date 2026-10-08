"""Synthetic provider-200 failure classification without provider traffic or saves."""

import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import generation
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def provider_client():
    """Use the actual LM Studio adapter with deterministic HTTP-200 responses."""
    scenario = {"content": "{}", "finish_reason": "stop"}
    service = AIService(RuntimeAIConfig(provider="lm_studio", model="synthetic", max_tokens=1000), logging.getLogger(__name__))
    service._client.close()
    service._client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
        "model": "synthetic", "choices": [{"message": {"content": scenario["content"]}, "finish_reason": scenario["finish_reason"]}],
    })))
    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[generation.require_teacher_or_admin] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[generation.get_ai_service_dependency] = lambda: service
    with TestClient(app) as client:
        yield client, scenario, service
    service.close()


def request(client):
    """Send an unpersisted lesson request using only synthetic task text."""
    return client.post('/api/generate/lesson', json={
        'topic': 'Synthetic fractions', 'grade_level': 'adult', 'learning_objectives': ['Compare parts'],
    })


@pytest.mark.parametrize(('content', 'finish_reason', 'code'), [
    ('{"title":"Incomplete', 'length', 'generation_output_limit'),
    ('not structured output', 'stop', 'generation_invalid_output'),
    ('{"title":"Empty lesson"}', 'stop', 'generation_invalid_output'),
])
def test_provider_200_failure_is_explicit_and_diagnostic(provider_client, caplog, content, finish_reason, code):
    client, scenario, _ = provider_client
    scenario.update(content=content, finish_reason=finish_reason)
    with caplog.at_level(logging.WARNING, logger='src.api.routes.generation'):
        response = request(client)
    assert response.status_code == 502
    assert response.json() == {'detail': {'code': code, 'saved': False}}
    assert code in caplog.text
    assert 'trace=' in caplog.text
    assert content not in response.text


def test_complete_provider_200_creates_reviewable_unsaved_proposal(provider_client):
    client, scenario, _ = provider_client
    scenario['content'] = json.dumps({'title': 'Fractions', 'sections': [{'title': 'Parts', 'content': 'Compare equal parts.'}]})
    response = request(client)
    assert response.status_code == 200
    assert response.json()['sections'][0]['content'] == 'Compare equal parts.'


def test_unexpected_failure_remains_unknown_and_logs_no_exception_values(provider_client, monkeypatch, caplog):
    client, _, service = provider_client
    def fail(**kwargs):
        raise RuntimeError('PRIVATE EXCEPTION PAYLOAD')
    monkeypatch.setattr(service, 'generate_lesson', fail)
    with caplog.at_level(logging.WARNING, logger='src.api.routes.generation'):
        response = request(client)
    assert response.status_code == 500
    assert response.json() == {'detail': 'Generation failed unexpectedly'}
    assert 'generation_unexpected' in caplog.text
    assert 'PRIVATE EXCEPTION PAYLOAD' not in caplog.text + response.text


@pytest.mark.parametrize('error_type', ['AIOutputLimitError', 'AIResponseParseError', 'AIContentValidationError', 'AIServiceError'])
def test_all_classified_exception_values_stay_out_of_http_and_logs(provider_client, monkeypatch, caplog, error_type):
    from src.core import exceptions
    client, _, service = provider_client
    sentinel = 'PRIVATE_PROVIDER_VALUE_SENTINEL'
    def fail(**kwargs):
        raise getattr(exceptions, error_type)(sentinel)
    monkeypatch.setattr(service, 'generate_lesson', fail)
    with caplog.at_level(logging.DEBUG):
        response = request(client)
    assert response.status_code == 502
    assert response.json()['detail']['saved'] is False
    assert sentinel not in response.text + caplog.text


def test_real_adapter_transport_exception_value_is_not_logged(provider_client, monkeypatch, caplog):
    client, _, service = provider_client
    sentinel = 'PRIVATE_TRANSPORT_VALUE_SENTINEL'
    def fail(*args, **kwargs):
        raise RuntimeError(sentinel)
    monkeypatch.setattr(service._client, 'post', fail)
    with caplog.at_level(logging.DEBUG):
        response = request(client)
    assert response.json() == {'detail': {'code': 'generation_provider_failed', 'saved': False}}
    assert sentinel not in response.text + caplog.text


@pytest.mark.parametrize(('content', 'finish'), [('PRIVATE_REPLY_VALUE_SENTINEL', 'stop'), ('PRIVATE_REPLY_VALUE_SENTINEL', 'length')])
def test_real_adapter_reply_body_is_not_logged(provider_client, caplog, content, finish):
    client, scenario, _ = provider_client
    scenario.update(content=content, finish_reason=finish)
    with caplog.at_level(logging.DEBUG):
        response = request(client)
    assert response.status_code == 502
    assert content not in response.text + caplog.text


@pytest.mark.parametrize('failure', [httpx.TimeoutException('PRIVATE_DETAIL_SENTINEL'), httpx.ConnectError('PRIVATE_DETAIL_SENTINEL')])
def test_safe_transport_categories_remain_useful_without_detail(provider_client, monkeypatch, caplog, failure):
    client, _, service = provider_client
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(service._client, 'post', fail)
    with caplog.at_level(logging.DEBUG):
        response = request(client)
    assert response.status_code == 502
    assert 'PRIVATE_DETAIL_SENTINEL' not in response.text + caplog.text


def test_openrouter_error_body_and_key_are_not_logged(provider_client, monkeypatch, caplog):
    client, _, service = provider_client
    service.config.provider = 'openrouter'
    service.config.api_key = 'PRIVATE_KEY_VALUE_SENTINEL'
    response = httpx.Response(400, request=httpx.Request('POST', 'https://provider.example.invalid/v1'),
                              json={'error': {'message': 'PRIVATE_BODY_VALUE_SENTINEL'}})
    monkeypatch.setattr(service._client, 'post', lambda *a, **kw: response)
    with caplog.at_level(logging.DEBUG):
        actual = request(client)
    assert actual.status_code == 502
    assert actual.json()['detail']['saved'] is False
    assert 'PRIVATE_KEY_VALUE_SENTINEL' not in actual.text + caplog.text
    assert 'PRIVATE_BODY_VALUE_SENTINEL' not in actual.text + caplog.text
