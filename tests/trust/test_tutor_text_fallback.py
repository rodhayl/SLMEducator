"""Tutor-only text compatibility; no inference and no structured-output salvage."""

import logging

import pytest

from src.core.exceptions import AIContentValidationError, AIResponseParseError
from src.core.services.ai_service import AIService


@pytest.fixture
def parser():
    service = object.__new__(AIService)
    service.logger = logging.getLogger(__name__)
    return service


@pytest.mark.parametrize("text", [
    "The error is dividing by zero. Divide six objects into two equal groups instead.",
    "## Try it yourself\n\nCount **three** objects in each group.",
    "True or false questions can have explanations.",
    "42 divided by six gives seven.",
])
def test_tutor_accepts_plain_prose_without_claiming_verification(parser, text):
    assert parser._parse_tutoring_response(text) == {"answer": text}


@pytest.mark.parametrize("text", [
    "", "   ", '{"answer": "unfinished',
    '{"answer": "first"} {"answer": "second"}',
    '{"answer": "first",',
    'Here is JSON: {"answer": "unfinished',
    '```json\n{"answer": "unfinished\n```',
    '["an answer"]', '{"answer": ""}', '{"error": "provider failed"}',
    '{"error": {"message": "provider unavailable"}}',
    "null", "true", "false", "42", "-3.14", "1e3",
    "true false", "42 43", "1e", "null,",
])
def test_tutor_does_not_turn_failed_structured_responses_into_prose(parser, text):
    with pytest.raises((AIResponseParseError, AIContentValidationError)):
        parser._parse_tutoring_response(text)


def test_structured_authoring_and_feedback_remain_strict(parser):
    text = "Useful-looking text without the required structured fields."
    for method in [parser._parse_study_plan_response,
                   lambda value: parser._parse_exercise_response(value, "Synthetic topic"),
                   parser._parse_progress_assessment_response]:
        with pytest.raises((AIResponseParseError, AIContentValidationError)):
            method(text)


def test_tutor_preserves_existing_valid_object(parser):
    assert parser._parse_tutoring_response('{"answer":"Three","explanation":"Six divided by two"}') == {
        "answer": "Three", "explanation": "Six divided by two"
    }
