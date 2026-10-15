"""Synthetic JSON newline regressions; no provider calls or personal data."""

import json
import logging

import pytest

from src.core.exceptions import AIContentValidationError, AIResponseParseError
from src.core.services.ai_service import AIService, RuntimeAIConfig


@pytest.fixture
def parser() -> AIService:
    service = object.__new__(AIService)
    service.logger = logging.getLogger(__name__)
    return service


@pytest.mark.parametrize("line_break", ["\n", "\r", "\r\n"])
@pytest.mark.parametrize("fenced", [False, True])
def test_tutor_preserves_literal_line_breaks(
    parser: AIService, line_break: str, fenced: bool,
) -> None:
    explanation = f"1. Divide six into two groups.{line_break}2. Each group has three."
    response = '{"explanation": "' + explanation + '"}'
    if fenced:
        response = f"```json\n{response}\n```"
    assert parser._parse_tutoring_response(response) == {"explanation": explanation}


def test_nested_json_preserves_escaped_quotes_slashes_and_constants(parser: AIService) -> None:
    lesson = {
        "sections": [{"content": 'Say "true" and "null".\nKeep {braces} and [lists].\nPath C:\\notes\\'}],
        "source_review": {"status": "needs_clarification", "issues": []},
        "enabled": True, "optional": None,
    }
    response = json.dumps(lesson, indent=2).replace(r".\n", ".\n")
    assert parser._parse_json_response(response, "lesson") == lesson


@pytest.mark.parametrize("prefix", ['quote "word"', "\\", "\\\\", '\\"', 'ends with "'])
def test_line_break_after_quotes_or_backslashes_keeps_string_boundaries(
    parser: AIService, prefix: str,
) -> None:
    response = json.dumps({"explanation": prefix + "<LF>second"}).replace("<LF>", "\n")
    assert parser._parse_tutoring_response(response) == {"explanation": prefix + "\nsecond"}


@pytest.mark.parametrize("value", [
    "first\nsecond", r"first\nsecond", 'quoted "word"',
    "backslash \\ and line\nbreak", "carriage\r\nreturn", "tab\there",
])
def test_valid_json_escapes_keep_their_original_meaning(parser: AIService, value: str) -> None:
    payload = {"explanation": value}
    assert parser._parse_tutoring_response(json.dumps(payload)) == payload


@pytest.mark.parametrize("response", [
    '{"explanation": "first\nsecond"',
    '{"explanation": "first\nsecond}',
    '{"explanation": "first\nsecond" "other": 1}',
    '{"explanation": "first\nsecond", "other": }',
    '{"explanation": "first\nsecond"} {"explanation": "third"}',
    '{"explanation": "first\nsecond\\q"}',
    '{"explanation": "first\nsecond\tthird"}',
    '{"explanation": "first\nsecond\x00third"}',
    '{"explanation": "first\nsecond\x0bthird"}',
    '{"explanation": "first\nsecond\x1bthird"}',
    "{'explanation': 'first\nsecond'}",
])
def test_newline_recovery_does_not_admit_other_broken_json(
    parser: AIService, response: str,
) -> None:
    with pytest.raises(AIResponseParseError):
        parser._parse_tutoring_response(response)


@pytest.mark.parametrize("response", [
    '{"explanation": "\n\r\n"}',
    '{"explanation": 42, "other": "first\nsecond"}',
    '{"error": "first\nsecond"}',
])
def test_newline_recovery_still_requires_a_usable_tutor_answer(
    parser: AIService, response: str,
) -> None:
    with pytest.raises(AIContentValidationError):
        parser._parse_tutoring_response(response)


def test_newline_recovery_still_requires_valid_structured_fields(parser: AIService) -> None:
    response = '{"description": "first\nsecond"}'
    for method in (
        parser._parse_study_plan_response,
        lambda value: parser._parse_exercise_response(value, "Synthetic topic"),
        parser._parse_progress_assessment_response,
    ):
        with pytest.raises(AIContentValidationError):
            method(response)


def test_recovery_preserves_raw_provider_response(
    parser: AIService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = '{"explanation": "first\nsecond"}'
    parser.config = RuntimeAIConfig(provider="ollama", model="synthetic")
    monkeypatch.setattr(parser, "_call_ollama", lambda *args: {"content": raw})
    response = parser._call_ai("Synthetic question")
    assert parser._parse_tutoring_response(response.content) == {"explanation": "first\nsecond"}
    assert parser.last_response is response
    assert response.content == raw
