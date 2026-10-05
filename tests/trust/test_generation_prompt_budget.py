"""Prompt budgets and explicit transport truncation; no semantic heuristics."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.exceptions import AIResponseParseError, AIContentValidationError
from src.core.services.ai_service import AIService, RuntimeAIConfig


def test_explicit_assessment_type_reaches_course_generator():
    from src.api.routes.generation import FullTopicPackageRequest
    from src.core.services.generation_workflow import _generate, _fingerprint
    request = FullTopicPackageRequest(subject="Sharing", topic_name="Sharing", grade_level="adult",
        learning_objectives=["Explain equality"], assessment_question_types=["short_answer"])
    service = MagicMock()
    service.generate_assessment_questions.return_value = [{"question_text": "Explain equality", "question_type": "short_answer"}]
    _generate(service, request, "assessment", 0)
    assert service.generate_assessment_questions.call_args.kwargs["question_types"] == ["short_answer"]
    # Adding the optional selector must not change previous mixed-type retry IDs.
    legacy = request.model_dump(exclude={"assessment_question_types"})
    mixed = FullTopicPackageRequest(**legacy)
    from hashlib import sha256
    assert _fingerprint(mixed) == sha256(json.dumps(mixed.model_dump(exclude={"auto_save", "assessment_question_types"}), sort_keys=True).encode()).hexdigest()


def test_provider_cannot_substitute_mcq_for_explicit_open_question(service):
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps({"questions": [{"question_text": "Pick a value", "question_type": "multiple_choice", "points": 5, "correct_answer": "A", "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"}, "explanation": "Source."}]})}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    with pytest.raises(AIContentValidationError, match="requested type"):
        service.generate_assessment_questions("Sharing", ["Explain"], question_types=["short_answer"], num_questions=1)


def test_reasoning_override_reaches_lmstudio_transport(service):
    service.config.reasoning_effort = "none"
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": "4"}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    assert service._call_ai("Two plus two").content == "4"
    assert service._client.post.call_args.kwargs["json"]["reasoning_effort"] == "none"


def test_partial_selection_is_disclosed_in_model_input(service):
    source = "Synthetic inventory. " * 800
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"content":"Selected inventory"}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    result = service.generate_lesson("Inventory", "adult", ["Read observations"], source_material=source)
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert result["_source_usage"]["use_coverage"] == "partial"
    assert "Selection coverage of supplied text: partial" in prompt
    assert "This does not certify extraction of the original document" in prompt


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


def test_lesson_task_prioritizes_objectives_over_topic_and_optional_expansion(service):
    service._client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"content":"Source is insufficient; ask the teacher."}'}, "finish_reason": "stop"}], "model": "synthetic"},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    service.generate_lesson("Unknown tool", "beginner adult", ["Explain its capacity"],
                            source_material="Two handles. Capacity was not measured.")
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert prompt.index("Explain its capacity") < prompt.index("UNTRUSTED SOURCE")
    assert "navigation label" in prompt
    assert "direct question to the teacher" in prompt
    assert "Do not substitute" in prompt
    assert "Omit vocabulary" in prompt
    assert "Objectives are requests, not factual evidence" in prompt
    assert "section content itself" in prompt
    assert "does not establish membership" in prompt


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
