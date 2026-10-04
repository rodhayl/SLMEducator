"""Canonical learner-facing content without discarding legacy author fields."""

from copy import deepcopy
from typing import Any

SCHEMA_VERSION = 1


def normalize_content(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    """Validate useful content and provide consistent lesson/practice fields."""
    if not isinstance(value, dict) or value.get("error"):
        raise ValueError("Content must be a valid object without a generation error")
    data = deepcopy(value)
    data["schema_version"] = SCHEMA_VERSION
    data["kind"] = kind
    if kind == "lesson":
        body = data.get("content") or data.get("text") or data.get("body")
        sections = data.get("sections") or []
        if not body and not sections:
            raise ValueError("A lesson needs explanatory text or sections")
        if body and not isinstance(body, str):
            raise ValueError("Lesson text must be a string")
        if not isinstance(sections, list) or any(
            not isinstance(item, dict) for item in sections
        ):
            raise ValueError("Lesson sections must be objects")
        if body and not sections:
            data["sections"] = [{"title": "Lesson", "content": body}]
        if not (isinstance(body, str) and body.strip()) and not any(
            isinstance(section.get("content"), str) and section["content"].strip()
            for section in sections
        ):
            raise ValueError("A lesson needs nonempty explanatory text")
        for section in data.get("sections", []):
            if not isinstance(section.get("content", ""), str):
                raise ValueError("Section content must be text")
    elif kind == "exercise":
        question = data.get("question") or data.get("question_text")
        if (
            not isinstance(question, str)
            or not question.strip()
            or question == "Error generating exercise"
        ):
            raise ValueError("Practice needs a meaningful question")
        data["question"] = question
        if data.get("type") == "multiple_choice" and not data.get("options"):
            raise ValueError("Multiple-choice practice needs options")
    elif kind == "assessment":
        if not data.get("assessment_id") and not data.get("questions"):
            raise ValueError(
                "An assessment needs questions or a linked executable draft"
            )
    elif kind == "qa":
        if not (data.get("question") or data.get("content") or data.get("answer")):
            raise ValueError("Q&A needs a question or content")
    return data
