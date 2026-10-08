"""Teacher lesson fields remain visible and canonical without private assets."""
from types import SimpleNamespace

import pytest

from src.core.models import ContentType
from src.core.services.content_schema import learner_content, normalize_content
from src.core.services.learning_context import source_context


def test_teacher_examples_questions_and_review_are_shared_with_tutor_source():
    data = {
        "body": "Eight equal parts.",
        "worked_example": "Three parts form 3/8.",
        "independent_attempt": "Compare 3/8 and 5/8.",
        "feedback": "Compare numerators for equal denominators.",
        "delayed_review": "Try again tomorrow.",
        "prerequisite_check": "Count eight parts.",
        "discussion_questions": ["What makes parts equal?"],
        "rubric": {"secret": "Teacher-only criterion"},
        "generation": {"private": "Private source input"},
    }
    visible = learner_content("lesson", normalize_content("lesson", data))
    assert "rubric" not in visible and "generation" not in visible
    assert visible["worked_example"] == data["worked_example"]
    content = SimpleNamespace(id=1, title="Synthetic lesson", content_type=ContentType.LESSON,
                              decrypted_content_data=data, content_data="encrypted")
    context = source_context(content)
    assert "Three parts form 3/8" in context.content_data
    assert "What makes parts equal?" in context.content_data
    assert "Teacher-only" not in context.content_data and "Private source input" not in context.content_data


@pytest.mark.parametrize("key", ["worked_example", "independent_attempt", "feedback", "delayed_review", "prerequisite_check"])
def test_new_visible_fields_cannot_serialize_nested_teacher_assets(key):
    data = {"body": "Explanation", key: {"rubric": "Private criterion"}}
    with pytest.raises(ValueError, match="must be text"):
        normalize_content("lesson", data)
    assert key not in learner_content("lesson", data)


def test_discussion_questions_accept_only_instructional_text():
    with pytest.raises(ValueError, match="list of text"):
        normalize_content("lesson", {"body": "Explanation", "discussion_questions": [{"rubric": "private"}]})
    assert learner_content("lesson", {"discussion_questions": ["Explain", {"rubric": "private"}]}) == {"discussion_questions": ["Explain"]}


@pytest.mark.parametrize("body_key", ["content", "body", "text"])
def test_body_only_lesson_does_not_invent_an_english_section_title(body_key):
    """Inline lesson normalization keeps the body without storing a UI label."""
    result = normalize_content("lesson", {body_key: "Texto del docente"})
    assert result["sections"] == [{"title": "", "content": "Texto del docente"}]
    assert normalize_content("lesson", result) == result
    assert learner_content("lesson", result)["sections"] == result["sections"]


def test_distinct_body_has_no_invented_heading_and_authored_titles_are_preserved():
    """Do not translate or replace an author-provided title, even 'Lesson'."""
    value = {"body": "Introducción", "sections": [{"title": "Lesson", "content": "Written title"}]}
    result = normalize_content("lesson", value)
    assert result["sections"][0] == {"title": "", "content": "Introducción"}
    assert result["sections"][1] == value["sections"][0]
