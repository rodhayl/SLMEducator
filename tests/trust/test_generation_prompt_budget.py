"""Prompt budgets and explicit transport truncation; no semantic heuristics."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.exceptions import AIResponseParseError
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(AIService, "_setup_client", lambda self: setattr(self, "_client", MagicMock()))
    instance = AIService(RuntimeAIConfig("lm_studio", "synthetic", max_tokens=1200), MagicMock())
    yield instance
    instance.close()


def test_lesson_prompt_has_budget_and_no_copyable_example(service):
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"content":"Actual explanation"}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    service.generate_lesson("Fractions", "beginner", ["Count parts"], source_material="Equal parts.")
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert "1200" in prompt
    assert "definition1" not in prompt
    assert "comprehensive" not in prompt
    assert "insufficient" in prompt


def test_exercise_prompt_uses_types_instead_of_sample_answers(service):
    prompt = service._build_exercise_prompt("Fractions", "easy", "multiple_choice")
    assert "option1" not in prompt
    assert "Exercise question/prompt" not in prompt
    assert "insufficient" in prompt
    assert "exactly" in prompt


@pytest.mark.parametrize("operation", ["outline", "topic", "study_plan"])
def test_planning_prompts_share_bounded_noncopyable_contract(service, operation):
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"title":"Actual plan","description":"Draft","phases":[],"units":[]}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    if operation == "outline":
        service.generate_course_outline("Synthetic topic", "beginner", source_material="Known source fact.")
    elif operation == "topic":
        service.generate_topic_content("Synthetic subject", "Synthetic topic", "beginner", ["Read"], source_material="Known source fact.")
    else:
        prompt = service._build_study_plan_prompt("Synthetic subject", "beginner", ["Read"], 4)
        assert "1200" in prompt and "objective1" not in prompt and "comprehensive" not in prompt
        return
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert "1200" in prompt and "insufficient" in prompt
    assert "obj1" not in prompt and "point1" not in prompt and "Educational content text" not in prompt


def test_exercise_preserves_objectives_level_and_source_receipt(service):
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"question":"Compute water","type":"short_answer"}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    result = service.generate_exercise("Water", "easy", "short_answer", source_material="[section:1]\nTwo cups per unit.", grade_level="beginner adult", learning_objectives=["Multiply by three"])
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert "beginner adult" in prompt and "Multiply by three" in prompt
    assert result["_source_usage"]["fragment"] in prompt
    assert result["_source_usage"]["use_coverage"] == "complete"


def test_assessment_sources_reach_prompt_without_becoming_logged_topic(service):
    marker = "Synthetic private source marker"
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"questions":[]}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    service.generate_assessment_questions("Sharing", ["Explain equal amounts"],
        source_material=marker, grade_level="beginner adult")
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert marker in prompt and "beginner adult" in prompt
    assert marker not in repr(service.logger.mock_calls)


@pytest.mark.parametrize("provider", ["lm_studio", "openai", "openrouter", "ollama"])
def test_explicit_length_stop_is_failure_even_when_json_is_complete(service, provider):
    service.config.provider = provider
    service.config.api_key = "synthetic-not-a-real-key"
    body = {"choices": [{"message": {"content": json.dumps({"content": "Incomplete lesson"})}, "finish_reason": "length"}], "model": "synthetic"}
    if provider == "ollama":
        body = {"response": '{"content":"Incomplete lesson"}', "done": True, "done_reason": "length"}
    service._client.post.return_value = httpx.Response(200, json=body, request=httpx.Request("POST", "http://synthetic.invalid"))
    with pytest.raises(AIResponseParseError, match="output limit"):
        service._call_ai("Synthetic instruction")
