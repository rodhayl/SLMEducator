"""Generation contracts through real prompts/parsers and a final HTTP-only stub."""

import json
import logging
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.exceptions import (
    AIContentValidationError,
    AIResponseParseError,
    AIServiceError,
)
from src.core.models import AIModelConfig, Content, ContentType
from src.core.services.ai_service import AIService


@pytest.fixture
def generation_service():
    """Construct the actual service; replace only the outgoing HTTP client."""
    service = AIService(
        AIModelConfig(provider="ollama", model="synthetic-generation-model"),
        logging.getLogger(__name__),
    )
    client = MagicMock()
    service._client = client

    def respond(content):
        body = content if isinstance(content, str) else json.dumps(content)
        client.post.side_effect = None
        client.post.return_value = httpx.Response(
            200,
            json={"response": body, "prompt_eval_count": 4, "eval_count": 6},
            request=httpx.Request("POST", "http://synthetic.invalid/api/generate"),
        )
        return service

    yield service, respond
    service.close()


def request_body(service):
    """Return the final provider payload for the last real service operation."""
    return service._client.post.call_args.kwargs["json"]


@pytest.mark.parametrize("kind", ["lesson", "topic", "outline"])
def test_source_backed_generation_keeps_exact_fragment_receipt(generation_service, kind):
    service, respond = generation_service
    source = "[page:1]\nA numerator counts selected equal parts."
    result_data = {"title": "Synthetic fractions", "content": "Selected equal parts"}
    respond(result_data)
    if kind == "lesson":
        result = service.generate_lesson(
            "Fractions", "synthetic adult", ["Explain numerator"], 25, source
        )
        expected_tokens = 4000
    elif kind == "topic":
        result = service.generate_topic_content(
            "Math",
            "Fractions",
            "synthetic adult",
            ["Explain numerator"],
            source_material=source,
        )
        expected_tokens = 3000
    else:
        result = service.generate_course_outline("Fractions", "synthetic adult", 3, source)
        expected_tokens = 2000
    usage = result.pop("_source_usage")
    expected = {**result_data, "objectives": ["Explain numerator"]} if kind == "lesson" else result_data
    assert result == expected
    assert usage["source_document_id"] == sha256(source.encode()).hexdigest()
    assert usage["fragment_hash"] == sha256(usage["fragment"].encode()).hexdigest()
    assert usage["source_references"] == ["page:1"]
    assert usage["use_coverage"] == "complete"
    body = request_body(service)
    assert usage["fragment"] in body["prompt"]
    assert "UNTRUSTED SOURCE DATA" in body["prompt"]
    assert "synthetic adult" in body["prompt"]
    assert body["options"]["num_predict"] == expected_tokens
    if kind == "topic":
        assert "Content to generate: lesson, exercise" in body["prompt"]


def test_requested_topic_types_are_sent_without_default_expansion(generation_service):
    service, respond = generation_service
    respond({"vocabulary": [{"term": "Numerator", "definition": "Selected parts"}]})
    result = service.generate_topic_content(
        "Math", "Fractions", "synthetic adult", [], ["vocabulary"]
    )
    assert result["vocabulary"][0]["term"] == "Numerator"
    assert result["_source_usage"]["source_characters"] == 0
    assert "Content to generate: vocabulary" in request_body(service)["prompt"]


@pytest.mark.parametrize("question_types", [None, ["short_answer"]])
def test_question_generation_preserves_keys_and_requested_constraints(
    generation_service, question_types
):
    service, respond = generation_service
    question = {
        "question_text": "What does a numerator count?",
        "question_type": "short_answer",
        "points": 4,
        "correct_answer": "Selected equal parts",
    }
    respond({"questions": [question]})
    assert service.generate_assessment_questions(
        "Fractions", ["Explain numerator"], question_types, 1, "easy"
    ) == [question]
    body = request_body(service)
    assert "Generate 1 assessment questions" in body["prompt"]
    assert "Overall Difficulty: easy" in body["prompt"]
    assert "Explain numerator" in body["prompt"]
    expected = ", ".join(question_types or ["multiple_choice", "true_false", "short_answer"])
    assert f"Question Types: {expected}" in body["prompt"]
    assert body["options"]["num_predict"] == 4000


@pytest.mark.parametrize(
    "operation",
    [
        "plan",
        "exercise",
        "lesson",
        "topic",
        "questions",
        "outline",
        "tutor",
        "content",
        "assessment",
        "grade",
    ],
)
def test_generation_provider_failure_never_becomes_success(generation_service, operation):
    service, _ = generation_service
    service._client.post.side_effect = httpx.ConnectError("synthetic provider offline")
    with pytest.raises(AIServiceError, match="synthetic provider offline"):
        invoke_generation(service, operation)
    assert service._client.post.call_count == 1
    assert not hasattr(service, "last_response")


def invoke_generation(service, operation):
    """Exercise each supported public generation entry point consistently."""
    calls = {
        "plan": lambda: service.generate_study_plan(
            SimpleNamespace(id=1), "Fractions", "synthetic adult", ["Compare"], 2
        ),
        "exercise": lambda: service.generate_exercise("Fractions", "easy", "short_answer"),
        "lesson": lambda: service.generate_lesson("Fractions", "synthetic adult", ["Compare"]),
        "topic": lambda: service.generate_topic_content(
            "Math", "Fractions", "synthetic adult", ["Compare"]
        ),
        "questions": lambda: service.generate_assessment_questions("Fractions", ["Compare"]),
        "outline": lambda: service.generate_course_outline("Fractions", "synthetic adult"),
        "tutor": lambda: service.provide_tutoring(
            {"id": 1, "grade_level": "synthetic adult"}, "Explain numerator"
        ),
        "content": lambda: service.generate_content("Explain numerator"),
        "assessment": lambda: service.generate_assessment("Fractions", "easy", ["short_answer"]),
        "grade": lambda: service.grade_answer(
            "Explain numerator", "Selected parts", "short_answer"
        ),
    }
    return calls[operation]()


@pytest.mark.parametrize(
    "operation",
    ["plan", "exercise", "lesson", "topic", "questions", "outline", "tutor"],
)
@pytest.mark.parametrize("content", ["No structured answer is available.", "{broken JSON}"])
def test_structured_generation_rejects_unparseable_model_output(
    generation_service, operation, content
):
    service, respond = generation_service
    respond(content)
    with pytest.raises(AIResponseParseError):
        invoke_generation(service, operation)
    assert service.last_response.content == content


@pytest.mark.parametrize(
    "content,expected",
    [
        (
            '```text\nignored non-JSON note\n```\n```json\n{"content":"Fractions"}\n```',
            {"content": "Fractions"},
        ),
        (
            "Preface {'content': 'Fractions', 'reviewed': true, 'missing': null} End",
            {"content": "Fractions", "reviewed": True, "missing": None},
        ),
        (
            "{'content': 'falsehood, true statements, null set'}",
            {"content": "falsehood, true statements, null set"},
        ),
    ],
)
def test_tolerant_structured_parsing_preserves_text_and_boolean_values(
    generation_service, content, expected
):
    service, respond = generation_service
    respond(content)
    result = service.generate_lesson("Fractions", "synthetic adult", [])
    result.pop("_source_usage")
    assert result == expected


@pytest.mark.parametrize("content", ["{'not-an-object'}", "{'content': str('not executable')}"])
def test_non_object_or_executable_expression_is_rejected(generation_service, content):
    service, respond = generation_service
    respond(content)
    with pytest.raises(AIResponseParseError):
        service.generate_lesson("Fractions", "synthetic adult", [])


@pytest.mark.parametrize("payload", [{"phases": []}, {"items": [{"description": "missing title"}]}])
def test_study_plan_without_a_usable_phase_is_rejected(generation_service, payload):
    service, respond = generation_service
    respond(payload)
    with pytest.raises(AIContentValidationError, match="nonempty phases"):
        invoke_generation(service, "plan")


def test_legacy_named_items_keep_their_actual_learning_sequence(generation_service):
    service, respond = generation_service
    topics = [{"name": "Numerator", "description": "Selected parts"}]
    respond({"title": "Fractions", "items": topics})
    result = invoke_generation(service, "plan")
    assert result["phases"] == [{"title": "Learning sequence", "topics": topics}]
    assert result["items"] == topics


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "Error generating exercise"},
        {"question": "Choose numerator", "type": "multiple_choice", "options": []},
    ],
)
def test_invalid_exercise_content_does_not_pass_normalization(generation_service, payload):
    service, respond = generation_service
    respond(payload)
    with pytest.raises(AIContentValidationError):
        invoke_generation(service, "exercise")


@pytest.mark.parametrize(
    "payload", [{"answer": " "}, {"answer": 123}, {"related_topics": ["fractions"]}]
)
def test_tutoring_requires_nonempty_answer_text(generation_service, payload):
    service, respond = generation_service
    respond(payload)
    with pytest.raises(AIContentValidationError, match="no usable answer"):
        invoke_generation(service, "tutor")


def test_tutor_context_reports_omissions_and_bounds_history(generation_service):
    service, respond = generation_service
    respond({"explanation": "A numerator counts selected parts."})
    history = [{"role": "user", "content": f"history-{index:02d}"} for index in range(12)]
    result = service.provide_tutoring(
        SimpleNamespace(id=1, grade_level="synthetic adult"),
        "Explain numerator",
        context="Use short sentences.",
        study_plan_context={
            "title": "Fractions",
            "description": "Equal parts",
            "current_phase": {"name": "Compare", "objectives": ["Identify", "Explain"]},
        },
        content_context={
            "title": "Reading",
            "content_data": "A" * 6100 + "UNSEEN_END",
            "truncated": True,
        },
        conversation_history=history,
    )
    assert result["explanation"].startswith("A numerator")
    prompt = request_body(service)["prompt"]
    assert "Source coverage: partial" in prompt and "... (truncated)" in prompt
    assert "UNSEEN_END" not in prompt and "A" * 6001 not in prompt
    assert "history-00" not in prompt and "history-01" not in prompt
    assert "history-02" in prompt and "history-11" in prompt
    assert "Learning Objectives: Identify, Explain" in prompt
    assert "Use short sentences." in prompt
    assert request_body(service)["options"]["num_predict"] == 1200


@pytest.mark.parametrize(
    "context,question,system",
    [
        (
            "Explain fractions.\nStudent's question: What is a numerator?",
            "What is a numerator?",
            "Explain fractions.",
        ),
        ("Student's question: What is a numerator?", "What is a numerator?", None),
        ("A plain free-form prompt", "A plain free-form prompt", None),
    ],
)
def test_free_form_generation_separates_supported_system_prefix(
    generation_service, context, question, system
):
    service, respond = generation_service
    respond("A numerator counts selected parts.")
    assert service.generate_content(context, max_tokens=73, temperature=0.4).startswith(
        "A numerator"
    )
    body = request_body(service)
    assert body["prompt"] == question
    assert body.get("system") == system
    assert body["options"] == {"temperature": 0.4, "num_predict": 73}


@pytest.mark.parametrize(
    "kind,phrase",
    [
        ("explanation", "clearer and more detailed"),
        ("examples", "relevant, practical examples"),
        ("simplification", "Simplify the language"),
    ],
)
def test_enhancement_preserves_existing_structured_content_and_receipt(
    generation_service, kind, phrase
):
    service, respond = generation_service
    content = Content(id=41, title="Fractions", content_type=ContentType.LESSON)
    content.set_encrypted_content_data(
        {"content": "Original authored content", "source": "synthetic"}
    )
    respond({"enhanced_content": "Clearer fraction explanation"})
    result = service.enhance_content(content, kind)
    assert result is content
    decrypted = result.decrypted_content_data
    assert decrypted["content"] == "Original authored content"
    assert decrypted["source"] == "synthetic"
    assert decrypted["enhanced_content"] == "Clearer fraction explanation"
    assert decrypted["ai_enhancement"]["enhancement_type"] == kind
    assert decrypted["ai_enhancement"]["tokens_used"] == 10
    assert decrypted["ai_enhancement"]["ai_model"] == "synthetic-generation-model"
    assert result.ai_enhanced is True
    assert phrase in request_body(service)["prompt"]


@pytest.mark.parametrize(
    "raw", ["Plain language explanation", "{Not JSON, but still explanatory text}"]
)
def test_unstructured_enhancement_remains_text(generation_service, raw):
    service, respond = generation_service
    content = Content(
        id=42,
        title="Fractions",
        content_type=ContentType.LESSON,
        content_data="Legacy plain text",
    )
    respond(raw)
    service.enhance_content(content)
    assert content.content_data == raw
    assert getattr(content, "ai_metadata")["tokens_used"] == 10


def test_structured_enhancement_of_legacy_text_is_encrypted(generation_service):
    service, respond = generation_service
    content = Content(
        id=43,
        title="Fractions",
        content_type=ContentType.LESSON,
        content_data="Legacy plain text",
    )
    enhanced = {"paragraphs": ["Selected equal parts"]}
    respond({"enhanced_content": enhanced})
    service.enhance_content(content)
    assert content.decrypted_content_data == {"enhanced_content": enhanced}
    assert isinstance(content.content_data, str)
    assert "Selected equal parts" not in content.content_data


def test_enhancement_failure_does_not_modify_original_content(generation_service):
    service, _ = generation_service
    content = Content(id=44, title="Fractions", content_type=ContentType.LESSON)
    content.set_encrypted_content_data({"content": "Original"})
    original = content.content_data
    service._client.post.side_effect = httpx.ReadTimeout("synthetic offline")
    with pytest.raises(AIServiceError, match="Content enhancement failed"):
        service.enhance_content(content)
    assert content.content_data == original
    assert not getattr(content, "ai_enhanced", False)


@pytest.mark.parametrize(
    "rubric,correct_answer",
    [
        (None, None),
        (
            {"criteria": [{"name": "Equal parts", "max_points": 4}]},
            "Selected equal parts",
        ),
    ],
)
def test_grading_retains_review_boundary_and_ignores_model_certainty(
    generation_service, rubric, correct_answer
):
    service, respond = generation_service
    respond(
        {
            "points_earned": 3,
            "percentage": 999,
            "feedback": "Explain equal parts",
            "confidence": 1,
            "status": "final",
            "needs_review": False,
        }
    )
    result = service.grade_answer(
        "Explain numerator", "Selected parts", "short_answer", correct_answer, rubric, 4
    )
    assert result["points_earned"] == 3 and result["percentage"] == 75
    assert result["max_points"] == 4
    assert result["status"] == "suggested" and result["needs_review"] is True
    assert result["confidence"] is None
    assert result["improvements"] == result["misconceptions"] == result["strengths"] == []
    body = request_body(service)
    assert body["options"] == {"temperature": 0.2, "num_predict": 1000}
    assert "expert educational grader" in body["system"]
    assert "Equal parts" in body["prompt"] if rubric else "No rubric provided" in body["prompt"]
    assert (correct_answer or "Subjective evaluation required") in body["prompt"]


@pytest.mark.parametrize(
    "change",
    [
        {"feedback": None},
        {"improvements": "Practice"},
        {"misconceptions": [123]},
        {"points_earned": True},
        {"points_earned": 5},
        {"points_earned": -1},
    ],
)
def test_invalid_grade_fields_yield_review_without_a_fabricated_score(generation_service, change):
    service, respond = generation_service
    respond({"points_earned": 3, "feedback": "Explain equal parts", **change})
    result = service.grade_answer(
        "Explain numerator", "Selected parts", "short_answer", max_points=4
    )
    assert result["status"] == "needs_review" and result["needs_review"] is True
    assert result["points_earned"] is None and result["percentage"] is None
    assert result["confidence"] is None and result["is_correct"] is None


def test_comprehensive_assessment_delivers_model_questions_without_inventing_answers(
    generation_service,
):
    service, respond = generation_service
    question = {
        "question_text": "Explain numerator",
        "question_type": "short_answer",
        "correct_answer": "Selected equal parts",
        "points": 100,
    }
    respond({"title": "Fractions", "questions": [question], "total_points": 100})
    result = service.generate_assessment(
        "Fractions", "easy", ["short_answer"], 1, ["Explain numerator"]
    )
    assert result == {
        "title": "Fractions",
        "questions": [question],
        "total_points": 100,
    }
    body = request_body(service)
    assert body["options"] == {"temperature": 0.3, "num_predict": 4000}
    assert "Generate 1 questions total" in body["prompt"]
    assert "Explain numerator" in body["prompt"]
    assert "expert educational assessment creator" in body["system"]


def test_question_envelope_wrong_type_is_actionable_service_error(generation_service):
    service, respond = generation_service
    respond({"questions": None})
    with pytest.raises(AIServiceError, match="Assessment question generation failed"):
        service.generate_assessment_questions("Fractions", [])


def test_progress_provider_failure_with_detached_user_keeps_service_error(generation_service):
    service, respond = generation_service
    service._client.post.side_effect = httpx.ReadTimeout("synthetic timeout")
    user = {"id": 7, "full_name": "Synthetic", "grade_level": "adult"}
    session = SimpleNamespace(duration_minutes=5, completion_status="completed", score=0)
    with pytest.raises(AIServiceError, match="Progress assessment failed"):
        service.assess_progress(user, session)


@pytest.mark.parametrize("body", ["invalid output", "{}", "{'progress_summary': ''}"])
def test_invalid_progress_output_never_fabricates_success(generation_service, body):
    service, respond = generation_service
    respond(body)
    user = {"id": 7, "full_name": "Synthetic", "grade_level": "adult"}
    session = SimpleNamespace(duration_minutes=5, completion_status="completed", score=0)
    with pytest.raises(AIServiceError):
        service.assess_progress(user, session)


def test_zero_score_remains_zero_in_progress_prompt(generation_service):
    service, respond = generation_service
    respond({"progress_summary": "Synthetic feedback, not validated learning evidence"})
    result = service.assess_progress(
        {"id": 7, "full_name": "Synthetic", "grade_level": "adult"},
        SimpleNamespace(duration_minutes=5, completion_status="completed", score=0),
    )
    assert result["progress_summary"].startswith("Synthetic feedback")
    assert "Score: 0" in request_body(service)["prompt"]
