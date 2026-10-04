"""Content storage preserves encryption, filters, and rollback on failed writes."""

import pytest
from sqlalchemy import text

from src.core.models import Content, ContentType, StudyPlan
from src.core.services.content_service import ContentService


def test_content_storage_roundtrip_filters_and_link_preservation(
    db_service, test_teacher, test_student
):
    service = ContentService()
    plan = StudyPlan(title="Synthetic", creator_id=test_teacher.id)
    db_service.session.add(plan)
    db_service.session.commit()
    lesson = service.create_content(
        "Synthetic fractions",
        ContentType.LESSON,
        test_teacher.id,
        {"content": "Private synthetic text"},
        plan.id,
    )
    practice = service.create_content(
        "Synthetic practice",
        ContentType.EXERCISE,
        test_student.id,
        {"question": "One plus one?", "answer": "2"},
    )
    assert lesson is not None and practice is not None
    stored = db_service.session.execute(
        text("SELECT content_data FROM contents WHERE id=:id"), {"id": lesson.id}
    ).scalar_one()
    assert "Private synthetic text" not in stored
    assert service.get_content(lesson.id).decrypted_content_data == {
        "content": "Private synthetic text"
    }
    assert [
        c.id
        for c in service.list_content(
            creator_id=test_teacher.id, study_plan_id=plan.id, content_type=ContentType.LESSON
        )
    ] == [lesson.id]
    assert [c.id for c in service.search_content("fractions")] == [lesson.id]
    changed = service.update_content(
        lesson.id, {"title": "Revised fractions", "content_data": {"content": "New synthetic text"}}
    )
    assert changed.title == "Revised fractions"
    assert service.get_content(lesson.id).decrypted_content_data == {
        "content": "New synthetic text"
    }
    assert service.delete_content(practice.id)
    assert service.get_content(practice.id) is None
    assert service.get_content(lesson.id) is not None


def test_failed_content_write_rolls_back_existing_record(db_service, test_teacher):
    service = ContentService()
    content = service.create_content(
        "Keep original", ContentType.LESSON, test_teacher.id, {"content": "Keep body"}
    )
    assert service.update_content(content.id, {"title": None}) is None
    assert service.get_content(content.id).title == "Keep original"
    before = db_service.session.query(Content).count()
    assert (
        service.create_content(None, ContentType.LESSON, test_teacher.id, {"content": "No write"})
        is None
    )
    assert db_service.session.query(Content).count() == before


def test_missing_content_operations_do_not_claim_success(db_service):
    service = ContentService()
    assert service.get_content(999999) is None
    assert service.update_content(999999, {"title": "Absent"}) is None
    assert service.delete_content(999999) is False


@pytest.mark.parametrize(
    "action,args,expected",
    [
        ("get_content", (1,), None),
        ("update_content", (1, {"title": "Keep"}), None),
        ("delete_content", (1,), False),
        ("list_content", (), []),
        ("search_content", ("query",), []),
    ],
)
def test_storage_failure_remains_failure(db_service, monkeypatch, action, args, expected):
    service = ContentService()

    def unavailable():
        raise RuntimeError("Synthetic database unavailable")

    monkeypatch.setattr(service.db, "get_session", unavailable)
    assert getattr(service, action)(*args) == expected
