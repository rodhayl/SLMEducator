"""Canonical learner-facing content without discarding legacy author fields."""

from copy import deepcopy
from typing import Any

SCHEMA_VERSION = 1
LESSON_EXTRA_TEXT = (
    "worked_example", "independent_attempt", "feedback", "delayed_review",
    "prerequisite_check",
)


def normalize_content(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    """Validate useful content and provide consistent lesson/practice fields."""
    if not isinstance(value, dict) or value.get("error"):
        raise ValueError("Content must be a valid object without a generation error")
    if kind not in {"lesson", "exercise", "assessment", "qa"}:
        raise ValueError("Unsupported learning content kind")
    data = deepcopy(value)
    data["schema_version"] = SCHEMA_VERSION
    data["kind"] = kind
    if kind == "lesson":
        for key in LESSON_EXTRA_TEXT:
            if key in data and not isinstance(data[key], str):
                raise ValueError(f"Lesson {key} must be text")
        if "discussion_questions" in data and (
            not isinstance(data["discussion_questions"], list)
            or any(not isinstance(item, str) for item in data["discussion_questions"])
        ):
            raise ValueError("Discussion questions must be a list of text")
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
        if not (isinstance(body, str) and body.strip()) and not any(
            isinstance(section.get("content"), str) and section["content"].strip()
            for section in sections
        ):
            raise ValueError("A lesson needs nonempty explanatory text")
        for section in sections:
            if not isinstance(section.get("content", ""), str):
                raise ValueError("Section content must be text")
        joined = "\n\n".join(section.get("content", "") for section in sections)
        if isinstance(body, str) and body.strip() and body.strip() != joined.strip():
            sections = [{"title": "Overview" if sections else "Lesson", "content": body}] + sections
        data["sections"] = sections
        data["content"] = "\n\n".join(section.get("content", "") for section in sections)
        data.pop("text", None)
        data.pop("body", None)
    elif kind == "exercise":
        question = data.get("question") or data.get("question_text")
        if (
            not isinstance(question, str)
            or not question.strip()
            or question == "Error generating exercise"
        ):
            raise ValueError("Practice needs a meaningful question")
        data["question"] = question
        if (data.get("type") or data.get("question_type")) == "multiple_choice":
            options = data.get("options")
            if isinstance(options, dict) and "choices" in options:
                options = options["choices"]
            if not isinstance(options, (list, dict)) or not options:
                raise ValueError("Multiple-choice practice needs nonempty list or mapped options")
    elif kind == "assessment":
        if type(data.get("assessment_id")) is not int or data["assessment_id"] <= 0:
            raise ValueError(
                "Assessment content must link an executable assessment_id; import questions and rubrics in the assessments collection"
            )
        if any(
            key in data
            for key in (
                "questions",
                "correct_answer",
                "answer",
                "rubric",
                "rubrics",
                "solution",
            )
        ):
            raise ValueError(
                "Inline assessment questions, keys and rubrics are not allowed in content"
            )
    elif kind == "qa":
        if not (data.get("question") or data.get("content") or data.get("answer")):
            raise ValueError("Q&A needs a question or content")
    return data


def learner_content(
    kind: str, value: dict[str, Any], *, handout: bool = False
) -> dict[str, Any]:
    """Serialize explicit instructional fields; hidden assessment assets never cross."""
    allowed = {
        "lesson": {
            "title",
            "content",
            "text",
            "body",
            "sections",
            "summary",
            "objectives",
            "key_concepts",
            "vocabulary",
        },
        "exercise": {
            "question",
            "question_text",
            "type",
            "question_type",
            "options",
            "points",
            "hint",
        },
        "assessment": {"assessment_id", "title", "instructions"},
        "qa": {"question", "answer", "content"},
    }.get(kind, set())
    if kind == "lesson":
        allowed |= set(LESSON_EXTRA_TEXT) | {"discussion_questions"}
    # Independent practice intentionally supports learner self-checks. A printable
    # handout has a different purpose and omits its answer/solution keys.
    if kind == "exercise" and not handout:
        allowed |= {"answer", "correct_answer", "solution", "explanation", "hints"}
    result = {key: deepcopy(item) for key, item in value.items() if key in allowed}
    if kind == "lesson":
        for key in LESSON_EXTRA_TEXT:
            if key in result and not isinstance(result[key], str):
                result.pop(key)
        if "discussion_questions" in result:
            questions = result["discussion_questions"]
            result["discussion_questions"] = (
                [item for item in questions if isinstance(item, str)]
                if isinstance(questions, list) else []
            )
    if "sections" in result:
        sections = result["sections"]
        result["sections"] = (
            [
                {
                    key: item[key]
                    for key in ("title", "content", "text")
                    if isinstance(item.get(key), str)
                }
                for item in sections
                if isinstance(item, dict)
            ]
            if isinstance(sections, list)
            else []
        )
    if "vocabulary" in result:
        vocabulary = result["vocabulary"]
        result["vocabulary"] = (
            [
                {
                    key: item[key]
                    for key in ("term", "definition")
                    if isinstance(item.get(key), str)
                }
                for item in vocabulary
                if isinstance(item, dict)
            ]
            if isinstance(vocabulary, list)
            else []
        )
    return result
