"""Single-lesson API rejects unusable provider objects like package generation."""

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
def lesson_client():
    """Use the real adapter/parser with a synthetic HTTP response transport."""
    output = {}

    def transport(request):
        return httpx.Response(200, json={
            "model": "synthetic-contract-fixture",
            "choices": [{"message": {"content": json.dumps(output)}}],
        })

    service = AIService(
        RuntimeAIConfig(provider="lm_studio", model="synthetic-contract-fixture"),
        logging.getLogger(__name__),
    )
    service._client.close()
    service._client = httpx.Client(transport=httpx.MockTransport(transport))
    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[generation.require_teacher_or_admin] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[generation.get_ai_service_dependency] = lambda: service
    with TestClient(app) as client:
        yield client, output
    service.close()


def request_lesson(client):
    """Request a synthetic lesson without persisting or approving any content."""
    return client.post("/api/generate/lesson", json={
        "topic": "Zil flower facts",
        "grade_level": "Adult introductory",
        "learning_objectives": ["Recall supplied facts"],
        "source_material": "A zil flower has four blue petals.",
    })


@pytest.mark.parametrize("output", [
    {},
    {"title": "An empty generated lesson"},
    {"sections": [{"content": "   "}]},
    {"sections": [{"content": ["Invalid non-text section"]}]},
    {"error": "provider returned an error", "content": "Not a lesson"},
])
def test_single_lesson_rejects_unusable_provider_objects(lesson_client, output):
    client, response_body = lesson_client
    response_body.update(output)
    response = request_lesson(client)
    assert response.status_code == 500
    assert response.json().get("detail")


@pytest.mark.parametrize("output", [
    {"title": "Zil flowers", "content": "A zil flower has four blue petals."},
    {"title": "Zil flowers", "sections": [{"title": "Petals", "content": "Four blue petals."}]},
])
def test_single_lesson_preserves_valid_response_fields(lesson_client, output):
    client, response_body = lesson_client
    output = {**output, "source_review": {"status": "no_issue_reported", "issues": []}}
    response_body.update(output)
    response = request_lesson(client)
    assert response.status_code == 200
    actual = response.json()
    assert actual.pop("_source_usage")["use_coverage"] == "complete"
    assert actual == {**output, "objectives": ["Recall supplied facts"]}
