"""Readable learner exports preserve all canonical lesson instruction fields."""

import json

import pytest

from src.core.models import Content, ContentType, StudyPlan, StudyPlanContent, User, UserRole
from src.core.services.content_schema import LESSON_EXTRA_TEXT
from src.core.services.portability_service import export_course, render_handout


@pytest.mark.parametrize("format_name", ["json", "html", "markdown"])
def test_handout_preserves_lesson_instructional_fields(db_session, format_name):
    """Worked examples, prompts and review text survive every learner format."""
    author = User(
        username="handout_author",
        email="handout-author@example.invalid",
        first_name="Synthetic",
        last_name="Instructor",
        role=UserRole.TEACHER,
        password_hash="unused-synthetic",
    )
    db_session.add(author)
    db_session.flush()
    plan = StudyPlan(title="Instructional handout", creator_id=author.id)
    db_session.add(plan)
    db_session.flush()
    instructional_text = {
        "worked_example": "Three of eight equal parts form three eighths.",
        "independent_attempt": "Compare three eighths and five eighths.",
        "feedback": "Equal denominators let us compare numerators.",
        "delayed_review": "Repeat the comparison tomorrow with new fractions.",
        "prerequisite_check": "First count eight equal parts.",
    }
    assert set(instructional_text) == set(LESSON_EXTRA_TEXT)
    discussion = ["Why must the parts be equal?", "How would you explain the comparison?"]
    lesson = Content(
        title="Compare fractions",
        content_type=ContentType.LESSON,
        creator_id=author.id,
        study_plan_id=plan.id,
    )
    lesson.set_encrypted_content_data({
        "content": "Fractions describe equal parts of a whole.",
        **instructional_text,
        "discussion_questions": discussion,
    })
    db_session.add(lesson)
    db_session.flush()
    db_session.add(StudyPlanContent(study_plan_id=plan.id, content_id=lesson.id))
    db_session.commit()
    package = export_course(db_session, author, plan, "learner")
    rendered = (
        json.dumps(package)
        if format_name == "json"
        else render_handout(package, format_name)
    )
    for text in [*instructional_text.values(), *discussion]:
        assert text in rendered
