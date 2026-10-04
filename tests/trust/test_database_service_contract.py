"""Disposable SQLite configuration, history retention and scoped helper contracts."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from src.core.models import (
    ApplicationConfiguration,
    AuditLog,
    AuthAttempt,
    Content,
    ContentType,
    EventType,
    LearningSession,
    LoggingConfiguration,
    StudyPlan,
)
from src.core.services.temporal_service import utc_now


@pytest.mark.parametrize("kind", ["logging", "application"])
def test_system_configuration_roundtrip_preserves_account_settings(db_service, test_student, kind):
    db = db_service.session
    if kind == "logging":
        model, changes, key, personal = (
            LoggingConfiguration,
            {"level": "WARNING", "backup_count": 2},
            "level",
            "DEBUG",
        )
    else:
        model, changes, key, personal = (
            ApplicationConfiguration,
            {"theme": "dark", "language": "es", "timezone": "Europe/Madrid"},
            "theme",
            "light",
        )
    db.add(model(user_id=test_student.id, **{key: personal}))
    db.commit()
    get = getattr(db_service, f"get_{kind}_config")
    update = getattr(db_service, f"update_{kind}_config")
    assert get()[key] != personal
    update(changes)
    assert all(get()[k] == v for k, v in changes.items())
    update(changes)
    assert db.query(model).filter(model.user_id.is_(None)).count() == 1
    assert getattr(db.query(model).filter_by(user_id=test_student.id).one(), key) == personal


@pytest.mark.parametrize("kind", ["logging", "application"])
def test_configuration_read_falls_back_but_failed_write_is_not_success(
    db_service, monkeypatch, kind
):
    def unavailable():
        raise RuntimeError("Synthetic storage failure")

    monkeypatch.setattr(db_service, "get_session", unavailable)
    defaults = getattr(db_service, f"get_{kind}_config")()
    assert defaults["level" if kind == "logging" else "theme"] == (
        "INFO" if kind == "logging" else "auto"
    )
    with pytest.raises(RuntimeError, match="storage failure"):
        getattr(db_service, f"update_{kind}_config")({})


def test_ai_configuration_create_update_and_missing_identity(db_service, test_teacher):
    assert db_service.get_ai_config() is None
    config = db_service.create_ai_config(
        {"user_id": test_teacher.id, "provider": "ollama", "model": "synthetic-before"}
    )
    assert db_service.get_ai_config().id == config.id
    updated = db_service.update_ai_config(
        config.id, {"model": "synthetic-after", "model_parameters": {"max_tokens": 321}}
    )
    assert updated.model == "synthetic-after" and updated.model_parameters["max_tokens"] == 321
    assert db_service.update_ai_config(999999, {"model": "absent"}) is None


@pytest.mark.parametrize("kind", ["sessions", "logs", "auth"])
def test_cleanup_only_removes_known_old_timestamps(db_service, test_student, kind):
    db = db_service.session
    old, recent, unknown = utc_now() - timedelta(days=90), utc_now(), "2018-11-04 01:30:00.123456"
    if kind == "sessions":
        model, table, field, method = (
            LearningSession,
            "learning_sessions",
            "start_time",
            "cleanup_old_sessions",
        )
        rows = [
            model(student_id=test_student.id, start_time=when) for when in (old, recent, recent)
        ]
    elif kind == "logs":
        model, table, field, method = AuditLog, "audit_logs", "timestamp", "cleanup_old_logs"
        rows = [
            model(user_id=test_student.id, event_type=EventType.LOGIN, timestamp=when)
            for when in (old, recent, recent)
        ]
    else:
        model, table, field, method = (
            AuthAttempt,
            "auth_attempts",
            "timestamp",
            "cleanup_auth_attempts",
        )
        rows = [
            model(user_id=test_student.id, username=test_student.username, timestamp=when)
            for when in (old, recent, recent)
        ]
    db.add_all(rows)
    db.commit()
    ids = [row.id for row in rows]
    db.execute(
        text(f"UPDATE {table} SET {field}=:raw WHERE id=:id"), {"raw": unknown, "id": ids[2]}
    )
    db.commit()
    assert getattr(db_service, method)(days_old=30) == 1
    db.expire_all()
    assert db.get(model, ids[0]) is None
    assert db.get(model, ids[1]) is not None and db.get(model, ids[2]) is not None
    assert (
        db.execute(text(f"SELECT {field} FROM {table} WHERE id=:id"), {"id": ids[2]}).scalar_one()
        == unknown
    )


def test_plan_content_order_queries_and_summaries_use_selected_course(
    db_service, test_teacher, test_student
):
    plan = db_service.create_study_plan(
        StudyPlan(
            title="Synthetic",
            creator_id=test_teacher.id,
            description="Description",
            phases=[
                {"title": "First", "objectives": ["a"]},
                {"title": "Second", "objectives": list("abcdefg")},
            ],
        )
    )
    first = db_service.create_content(
        Content(title="First lesson", content_type=ContentType.LESSON, creator_id=test_teacher.id)
    )
    second = db_service.create_content(
        Content(title="Second lesson", content_type=ContentType.LESSON, creator_id=test_teacher.id)
    )
    assert db_service.add_content_to_plan(plan.id, first.id, 0, 1)
    assert db_service.add_content_to_plan(plan.id, second.id, 0, 0)
    assert not db_service.add_content_to_plan(plan.id, first.id, 0, 1)
    assert [item["id"] for item in db_service.get_plan_contents(plan.id)[0]] == [
        second.id,
        first.id,
    ]
    assert db_service.reorder_phase_content(plan.id, 0, [first.id, second.id])
    assert [item["id"] for item in db_service.get_plan_contents(plan.id)[0]] == [
        first.id,
        second.id,
    ]
    assert db_service.get_study_plan_summary(plan.id, 1)["current_phase"] == {
        "name": "Second",
        "objectives": list("abcde"),
    }
    assert db_service.get_study_plan_summary(plan.id, 99)["current_phase"]["name"] == "First"
    assert db_service.get_study_plan_summary(999999) is None
    assert db_service.get_content_summary(first.id)["title"] == first.title
    assert db_service.get_content_summary(999999) is None
    assert db_service.get_user_study_plans(test_student.id) == []
    db_service.assign_study_plan_to_student(test_student.id, plan.id)
    assert [p.id for p in db_service.get_user_study_plans(test_student.id)] == [plan.id]
    assert [p.id for p in db_service.get_user_study_plans(test_teacher.id)] == [plan.id]
    assert db_service.get_user_study_plans(999999) == []
    assert db_service.remove_content_from_plan(plan.id, first.id, 0)
    assert not db_service.remove_content_from_plan(plan.id, first.id, 0)
    assert (
        db_service.get_content_summary(first.id) is not None
    )  # Removing a link preserves content.


def test_content_author_and_personal_filters(db_service, test_teacher, test_student):
    own = db_service.create_content(
        Content(title="Teacher", content_type=ContentType.LESSON, creator_id=test_teacher.id)
    )
    personal = db_service.create_content(
        Content(
            title="Personal",
            content_type=ContentType.LESSON,
            creator_id=test_student.id,
            is_personal=True,
        )
    )
    db_service.create_content(
        Content(
            title="Ordinary",
            content_type=ContentType.LESSON,
            creator_id=test_student.id,
            is_personal=False,
        )
    )
    assert {c.id for c in db_service.get_all_content()} >= {own.id, personal.id}
    assert [c.id for c in db_service.get_all_content(test_teacher.id)] == [own.id]
    assert [c.id for c in db_service.get_user_content(test_student.id)] == [personal.id]
