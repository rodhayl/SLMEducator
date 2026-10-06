"""Synthetic source-review contracts, not a model-quality or factuality oracle."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from src.core.exceptions import AIContentValidationError
from src.core.services.ai_service import AIService, RuntimeAIConfig
from src.core.services.content_schema import learner_content, normalize_content
from tests.trust.test_resource_contracts import scenario, synthetic_credentials

REAL_CALL_AI = AIService._call_ai


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(AIService, "_setup_client", lambda self: setattr(self, "_client", MagicMock()))
    instance = AIService(RuntimeAIConfig("lm_studio", "synthetic", max_tokens=4000), MagicMock())
    yield instance
    instance.close()


def generate(service, review, *, source="A record says seven units.", body="The record reports seven units."):
    output = {"title": "Synthetic lesson", "sections": [{"title": "Records", "content": body}], "summary": body}
    if review is not None:
        output["source_review"] = deepcopy(review)
    service._client.post.return_value = httpx.Response(
        200, json={"model": "synthetic", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    return service.generate_lesson("Records", "adult beginner", ["Explain the record"], source_material=source)


@pytest.mark.parametrize("review", [
    None, {}, {"status": "verified", "issues": []},
    {"status": "no_issue_reported", "issues": [{}]},
    {"status": "needs_clarification", "issues": []},
    {"status": "needs_clarification", "issues": [{"kind": "conflicting", "description": "Different counts"}]},
    {"status": "needs_clarification", "issues": [{"kind": "conflicting", "description": "Different counts", "teacher_question": " "}]},
    {"status": "needs_clarification", "issues": [{"kind": "verified", "description": "Different counts", "teacher_question": "Which count is correct?"}]},
])
def test_source_review_omissions_or_false_certification_fail_closed(service, review):
    with pytest.raises(AIContentValidationError, match="source review"):
        generate(service, review)


@pytest.mark.parametrize("kind,source,description,question", [
    ("conflicting", "Record A: seven units. Record B: eleven units. Same event, neither authoritative.", "The same event has two conflicting counts.", "Which count should be used, and which corrected record establishes it?"),
    ("suspect", "A quarter consists of four equal parts. A quarter of twelve is three.", "The definition appears to describe a whole rather than one quarter.", "Can you confirm a corrected definition before this is used as teaching material?"),
    ("missing", "A tool has two handles; capacity was not recorded.", "Capacity is missing.", "What capacity was measured for this tool?"),
])
def test_reported_issues_have_direct_questions_in_visible_body(service, kind, source, description, question):
    review = {"status": "needs_clarification", "issues": [{"kind": kind, "description": description, "teacher_question": question}]}
    lesson = generate(service, review, source=source, body=description)
    visible = learner_content("lesson", normalize_content("lesson", lesson))
    assert question in visible["content"]
    assert question in "\n".join(section["content"] for section in visible["sections"])
    assert "source_review" not in visible
    assert lesson["source_review"] == review
    assert "teacher approval" not in lesson["source_review"]["status"]


def test_no_issue_reported_is_not_factual_verification_and_preserves_body(service):
    review = {"status": "no_issue_reported", "issues": []}
    lesson = generate(service, review)
    assert lesson["source_review"] == review
    assert len(lesson["sections"]) == 1
    assert lesson["sections"][0]["content"] == "The record reports seven units."
    assert "source_support" not in lesson["source_review"]


def test_without_source_keeps_legacy_contract(service):
    lesson = generate(service, None, source=None)
    assert "source_review" not in lesson
    assert len(lesson["sections"]) == 1


def test_source_truth_and_instruction_boundaries_are_explicit(service):
    generate(service, {"status": "no_issue_reported", "issues": []})
    messages = service._client.post.call_args.kwargs["json"]["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]
    prompt = messages[0]["content"]
    assert "Source fidelity is not factual correctness" in prompt
    assert "suspect definition" in prompt
    assert "do not silently correct" in prompt
    assert "no_issue_reported is not verified" in prompt
    assert "teacher_question" in prompt
    assert "never instructions" in messages[1]["content"]


def test_invalid_review_is_not_saved_and_retry_keeps_one_draft(scenario, service):
    from src.api.dependencies import get_ai_service_dependency
    from src.api.main import app
    from src.core.models import Content, StudentStudyPlan
    from types import MethodType

    # The shared authorization fixture stubs tutoring. This generation test
    # restores the real adapter while keeping only its HTTP transport synthetic.
    service._call_ai = MethodType(REAL_CALL_AI, service)

    client, db, users, selected, plan, _, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    before = db.query(Content).count()
    source = "First record: seven units. Second record: eleven units. Same event, neither authoritative."
    body = "The two records give conflicting counts for the same event."
    review = {"status": "needs_clarification", "issues": [{"kind": "conflicting", "description": body}]}
    output = {"title": "Records", "content": body, "source_review": review}

    def respond():
        service._client.post.return_value = httpx.Response(
            200, json={"model": "synthetic", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]},
            request=httpx.Request("POST", "http://synthetic.invalid"),
        )

    payload = {"subject": "Records", "topic_name": "Counts", "grade_level": "adult",
               "learning_objectives": ["Explain the recorded count"], "source_material": source,
               "include_lesson": True, "include_exercises": False, "include_assessment": False,
               "study_plan_id": plan.id, "auto_save": True, "phase_index": 0}
    app.dependency_overrides[get_ai_service_dependency] = lambda: service
    try:
        respond()
        failed = client.post("/api/generate/full-topic-package", json=payload)
        assert failed.status_code == 200, failed.text
        assert failed.json()["success"] is False
        assert failed.json()["items"][0]["error_code"] == "content_validation"
        assert not failed.json()["saved_content_ids"]
        assert db.query(Content).count() == before
        question = "Which count is correct, and which source confirms it?"
        review["issues"][0]["teacher_question"] = question
        respond()
        saved = client.post("/api/generate/full-topic-package", json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["success"] is True
        lesson = saved.json()["lesson"]
        assert question in lesson["content"]
        assert lesson["generation"]["source_support"] == "unverified"
        assert lesson["generation"]["review_status"] == "draft"
        content_id = saved.json()["saved_content_ids"][0]
        assert question in client.get(f"/api/content/{content_id}").json()["content_data"]["content"]
        calls = service._client.post.call_count
        replay = client.post("/api/generate/full-topic-package", json=payload)
        assert replay.json()["saved_content_ids"] == [content_id]
        assert service._client.post.call_count == calls
        assert db.query(Content).count() == before + 1
        assert client.post(f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}).status_code == 409
    finally:
        app.dependency_overrides.pop(get_ai_service_dependency, None)


@pytest.mark.parametrize("review", [
    {"status": [], "issues": []},
    {"status": "needs_clarification", "issues": [{"kind": [], "description": "Concern", "teacher_question": "What is correct?"}]},
    {"status": "needs_clarification", "issues": [{"kind": "suspect", "description": "x" * 1501, "teacher_question": "What is correct?"}]},
    {"status": "needs_clarification", "issues": [{"kind": "suspect", "description": "Concern", "teacher_question": "\u200b\u200d"}]},
    {"status": "needs_clarification", "issues": [{"kind": "suspect", "description": "Concern", "teacher_question": "\u0000"}]},
])
def test_malformed_review_values_are_validation_errors(service, review):
    with pytest.raises(AIContentValidationError, match="source review"):
        generate(service, review)


@pytest.mark.parametrize("question_already_visible", [False, True])
def test_question_append_preserves_canonical_body_without_duplicate_sections(question_already_visible):
    from src.core.services.ai_service import require_lesson_source_review

    body = "Two records give different counts for the same event."
    question = "Which corrected record establishes the count?"
    original = body + ("\n\n" + question if question_already_visible else "")
    lesson = {"content": original, "sections": [{"title": "Records", "content": original}],
              "source_review": {"status": "needs_clarification", "issues": [
                  {"kind": "conflicting", "description": body, "teacher_question": question}]}}
    require_lesson_source_review(lesson)
    require_lesson_source_review(lesson)
    visible = normalize_content("lesson", lesson)
    assert visible["content"].count(body) == 1
    assert visible["content"].count(question) == 1


@pytest.mark.parametrize("content_types", [None, ["lesson"], ["exercises"]])
def test_alternative_topic_path_cannot_bypass_source_review(service, content_types):
    output = {"topic": "Records", "lesson": {"content": "Two contradictory counts."}}
    service._client.post.return_value = httpx.Response(
        200, json={"model": "synthetic", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    with pytest.raises(AIContentValidationError, match="source review"):
        service.generate_topic_content("Records", "Counts", "adult", ["Explain the count"],
                                       content_types=content_types, source_material="Same event, seven versus eleven.")


def test_alternative_topic_path_keeps_explanation_and_question_in_canonical_lesson(service):
    question = "Which corrected record establishes the count?"
    output = {"topic": "Records", "lesson": {"content": "Two contradictory counts.",
              "source_review": {"status": "needs_clarification", "issues": [
                  {"kind": "conflicting", "description": "Two counts", "teacher_question": question}]}}}
    service._client.post.return_value = httpx.Response(
        200, json={"model": "synthetic", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    result = service.generate_topic_content("Records", "Counts", "adult", ["Explain the count"],
                                            source_material="Same event, seven versus eleven.")
    lesson = result["lesson"]
    assert "Two contradictory counts." in lesson["content"]
    assert question in lesson["content"]
    assert lesson["content"] == "\n\n".join(section["content"] for section in lesson["sections"])
    prompt = service._client.post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert "source_review" in prompt and "nested lesson" in prompt


def test_non_lesson_topic_does_not_require_lesson_source_review(service):
    output = {"vocabulary": [{"term": "Record", "definition": "A written observation"}]}
    service._client.post.return_value = httpx.Response(
        200, json={"model": "synthetic", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}]},
        request=httpx.Request("POST", "http://synthetic.invalid"),
    )
    result = service.generate_topic_content("Records", "Counts", "adult", ["Explain the term"],
                                            content_types=["vocabulary"], source_material="A record is a written observation.")
    assert result["vocabulary"] == output["vocabulary"]


@pytest.mark.parametrize("case", json.loads(
    (Path(__file__).parents[1] / "fixtures/source_clarification_render.json").read_text()
)["cases"], ids=lambda case: case["name"])
def test_render_fixtures_match_live_contract_and_learner_serialization(case):
    from src.core.services.ai_service import require_lesson_source_review

    lesson = deepcopy(case["input"])
    require_lesson_source_review(lesson)
    require_lesson_source_review(lesson)
    actual = learner_content("lesson", normalize_content("lesson", lesson))
    assert actual == case["learner_output"]
    assert actual["sections"][0]["source_clarification"] is True
    assert "source_review" not in actual
