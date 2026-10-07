"""Synthetic route regressions for parser-approved tutor answer alternatives."""

import json
import logging
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_db
from src.api.routes import ai
from src.api.security import get_current_user
from src.core.models import User, UserRole
from src.core.services import ai_request_lifecycle as lifecycle
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def tutor_client(db_session, monkeypatch):
    """Exercise ordinary learner routes with the real parser and no transport."""
    learner = User(
        username="response_selection_learner",
        email="response-selection@example.invalid",
        first_name="Synthetic",
        last_name="Learner",
        role=UserRole.STUDENT,
        password_hash="unused-synthetic",
    )
    db_session.add(learner)
    db_session.commit()
    service = AIService(
        RuntimeAIConfig(provider="ollama", model="synthetic"),
        logging.getLogger(__name__),
    )
    response = SimpleNamespace(content="")
    monkeypatch.setattr(service, "_call_ai", lambda *args, **kwargs: response)
    monkeypatch.setattr(ai, "get_ai_service_dependency", lambda *args: service)
    monkeypatch.setattr(lifecycle, "_RECORDS", {})
    monkeypatch.setattr(lifecycle, "_ACTIVE", {})
    app = FastAPI()
    app.include_router(ai.router)
    app.dependency_overrides[get_current_user] = lambda: learner
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client, response


def _request(client, route: str):
    """Submit one fresh request through either maintained tutor route."""
    input_field = "message" if route == "chat" else "question"
    response = client.post(
        f"/api/ai/{route}",
        json={input_field: "Explain equal parts", "client_request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("route", ["chat", "answer-question"])
@pytest.mark.parametrize(
    "provider_result, expected",
    [
        ({"explanation": "   ", "answer": "Usable answer"}, "Usable answer"),
        ({"explanation": {"detail": "Other value"}, "answer": "Usable answer"}, "Usable answer"),
        ({"explanation": 12, "answer": "Usable answer"}, "Usable answer"),
        ({"answer": "\n\t", "response": "Usable response"}, "Usable response"),
        ({"explanation": "Preferred explanation", "answer": "Other answer"}, "Preferred explanation"),
        ({"answer": "  Preserve answer spacing  "}, "  Preserve answer spacing  "),
    ],
)
def test_routes_deliver_parser_approved_answer(tutor_client, route, provider_result, expected):
    """Unusable optional alternatives must not mask a valid answer string."""
    client, provider = tutor_client
    provider.content = json.dumps(provider_result)
    result = _request(client, route)
    assert result["receipt"]["status"] == "completed"
    assert result["response" if route == "chat" else "answer"] == expected
    assert result.get("success", True) is True


@pytest.mark.parametrize("route", ["chat", "answer-question"])
@pytest.mark.parametrize("suggestions", ["Try another example", {"next": "Example"}, [1], None])
def test_optional_suggestions_do_not_discard_answer(tutor_client, route, suggestions):
    """Malformed optional suggestions are omitted, matching the chat contract."""
    client, provider = tutor_client
    provider.content = json.dumps({"answer": "Usable answer", "suggestions": suggestions})
    result = _request(client, route)
    assert result["receipt"]["status"] == "completed"
    assert result["response" if route == "chat" else "answer"] == "Usable answer"
    assert result["suggestions"] is None


@pytest.mark.parametrize("route", ["chat", "answer-question"])
def test_valid_suggestions_are_preserved(tutor_client, route):
    """Keep valid optional suggestions intact on both routes."""
    client, provider = tutor_client
    provider.content = json.dumps({"answer": "Usable answer", "suggestions": ["Try halves"]})
    result = _request(client, route)
    assert result["receipt"]["status"] == "completed"
    assert result["suggestions"] == ["Try halves"]


@pytest.mark.parametrize("route", ["chat", "answer-question"])
@pytest.mark.parametrize("provider_text", ['{"answer": "   "}', '{"answer": "unfinished', '{"error": "provider unavailable"}'])
def test_invalid_provider_response_remains_failure(tutor_client, route, provider_text):
    """Do not rescue absent answers, broken JSON or provider error envelopes."""
    client, provider = tutor_client
    provider.content = provider_text
    result = _request(client, route)
    assert result["receipt"]["status"] == "failed"
    if route == "chat":
        assert result["status"] != "suggestion"
    else:
        assert result["success"] is False
