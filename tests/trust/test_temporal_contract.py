"""Synthetic UTC persistence, unknown legacy and explicit local-day contracts."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text

from src.api.routes import timezone as timezone_routes
from src.api.routes.dashboard import _format_relative_time
from src.core import temporal
from src.core.models import AuthAttempt, LearningSession, MasteryNode, Submission, User
from src.core.services.auth import AuthService, AuthenticationError
from tests.integration.test_trustworthy_scoring_sessions import (
    world,
    create_quiz,
)  # noqa: F401


def test_new_defaults_retain_offset_and_legacy_reads_preserve_bytes(world):
    user = world.owner
    world.db.refresh(user)
    assert temporal.known_instant(user.created_at)
    raw = world.db.execute(
        text("SELECT created_at FROM users WHERE id=:id"), {"id": user.id}
    ).scalar_one()
    assert raw.endswith("+00:00")
    legacy = "2018-11-04 01:30:00.123000"
    world.db.execute(
        text("UPDATE users SET created_at=:raw WHERE id=:id"),
        {"raw": legacy, "id": user.id},
    )
    world.db.commit()
    world.db.refresh(user)
    assert user.created_at.tzinfo is None
    user.first_name = "Changed profile only"
    world.db.commit()
    assert (
        world.db.execute(
            text("SELECT created_at FROM users WHERE id=:id"), {"id": user.id}
        ).scalar_one()
        == legacy
    )


def test_all_model_timestamp_defaults_are_utc():
    from src.core.models import Base
    from sqlalchemy import DateTime

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, temporal.UTCDateTime):
                if column.default:
                    assert temporal.known_instant(column.default.arg(None)), str(column)
            else:
                assert not isinstance(column.type, DateTime), str(column)


def test_mixed_offsets_compare_as_instants_and_unknown_is_excluded(world):
    ids = [world.owner.id, world.other.id, world.learner.id, world.outsider.id]
    raw_values = [
        "2026-01-01 00:00:00",
        "2026-01-01 03:00:00+03:00",
        "2025-12-31 22:00:00-03:00",
        "2026-01-01 02:00:00+00:00",
    ]
    for ident, raw in zip(ids, raw_values):
        world.db.execute(
            text("UPDATE users SET created_at=:raw WHERE id=:id"),
            {"raw": raw, "id": ident},
        )
    world.db.commit()
    boundary = datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)
    before = world.db.scalars(
        select(User.id).where(temporal.known_before(User.created_at, boundary))
    ).all()
    after = world.db.scalars(
        select(User.id).where(temporal.known_after(User.created_at, boundary))
    ).all()
    assert before == [ids[1]]
    assert set(after) == set(ids[2:])


def test_timezone_setting_is_explicit_and_preserves_unrelated_settings(
    world, monkeypatch
):
    world.client.app.include_router(timezone_routes.router)
    world.user = world.learner
    world.learner.settings = {
        "assessment_assistance_policies": {"1": "disabled"},
        "notes": "keep",
    }
    world.db.commit()
    monkeypatch.setattr(
        temporal, "utc_now", lambda: datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc)
    )
    default = world.client.get("/api/settings/timezone").json()
    assert default["timezone"] == "UTC" and default["timezone_source"] == "default"
    assert default["local_date"] == "2026-01-02"
    invalid = world.client.put(
        "/api/settings/timezone", json={"timezone": "Mars/Fictional"}
    )
    assert invalid.status_code == 422
    changed = world.client.put(
        "/api/settings/timezone", json={"timezone": "America/Los_Angeles"}
    ).json()
    assert changed["local_date"] == "2026-01-01"
    assert world.learner.settings["notes"] == "keep"
    assert world.learner.settings["assessment_assistance_policies"] == {"1": "disabled"}


def test_timezone_persists_for_detached_authenticated_user_after_reopen(
    client, teacher_token, test_teacher, db_service
):
    from sqlalchemy.orm import Session

    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = client.put(
        "/api/settings/timezone", headers=headers, json={"timezone": "Asia/Tokyo"}
    )
    assert response.status_code == 200, response.text
    # Independent ORM session reads committed persistence, not dependency state.
    with Session(db_service.engine) as reopened:
        assert reopened.get(User, test_teacher.id).settings["timezone"] == "Asia/Tokyo"
    again = client.get("/api/settings/timezone", headers=headers)
    assert again.json()["timezone"] == "Asia/Tokyo"
    assert (
        client.put("/api/settings/timezone", json={"timezone": "UTC"}).status_code
        == 401
    )


@pytest.mark.parametrize(
    "zone,instant,expected",
    [
        ("America/New_York", "2026-03-08T06:59:00+00:00", "2026-03-08"),
        ("America/New_York", "2026-03-08T07:01:00+00:00", "2026-03-08"),
        ("America/New_York", "2026-11-01T05:30:00+00:00", "2026-11-01"),
        ("America/New_York", "2026-11-01T06:30:00+00:00", "2026-11-01"),
        ("Pacific/Kiritimati", "2026-01-01T12:00:00+00:00", "2026-01-02"),
    ],
)
def test_local_day_is_unambiguous_from_utc(zone, instant, expected):
    assert (
        str(
            temporal.local_date(
                SimpleNamespace(settings={"timezone": zone}),
                datetime.fromisoformat(instant),
            )
        )
        == expected
    )


def test_local_day_rejects_naive_input():
    with pytest.raises(ValueError, match="unknown"):
        temporal.local_date(SimpleNamespace(settings={}), datetime(2026, 1, 1))


def test_pinned_tzdata_resolves_zones_without_system_database(monkeypatch):
    import zoneinfo
    import tzdata

    assert tzdata.__version__ == "2026.5"
    prior = zoneinfo.TZPATH
    try:
        zoneinfo.reset_tzpath(())
        zoneinfo.ZoneInfo.clear_cache()
        assert temporal.validate_timezone("Europe/Madrid") == "Europe/Madrid"
        assert (
            temporal.local_date(
                SimpleNamespace(settings={"timezone": "Asia/Tokyo"}),
                datetime(2026, 1, 1, 18, tzinfo=timezone.utc),
            ).isoformat()
            == "2026-01-02"
        )
    finally:
        zoneinfo.reset_tzpath(prior)
        zoneinfo.ZoneInfo.clear_cache()


def test_legacy_timed_attempt_preserves_answers_for_manual_review(world):
    quiz, questions = create_quiz(world, time_limit_minutes=45)
    attempt = world.client.post(f"/api/assessments/{quiz}/start").json()
    world.db.execute(
        text("UPDATE assessment_submissions SET started_at=:old WHERE id=:id"),
        {"old": "2020-01-01 12:00:00.000000", "id": attempt["id"]},
    )
    world.db.commit()
    world.db.expire_all()
    replay = world.client.post(f"/api/assessments/{quiz}/start").json()
    assert (
        replay["expires_at"] is None and replay["timing_provenance"] == "legacy_unknown"
    )
    payload = {
        "submission_id": attempt["id"],
        "answers": [{"question_id": questions[0]["id"], "response_text": "A"}],
    }
    result = world.client.post(f"/api/assessments/{quiz}/submit", json=payload).json()
    assert result["score"] is None and result["status"] == "submitted"
    assert result["time_spent_minutes"] is None
    assert (
        world.db.get(Submission, attempt["id"]).responses[0].get_decrypted_response()
        == "A"
    )
    assert (
        world.client.post(f"/api/assessments/{quiz}/submit", json=payload).json()
        == result
    )


def test_legacy_session_end_is_safe_without_fabricated_duration(world):
    world.user = world.learner
    created = world.client.post(
        "/api/learning/start", json={"content_id": world.content.id}
    ).json()
    assert created["start_time"].endswith(("Z", "+00:00"))
    legacy = "2020-01-01 12:00:00.000000"
    world.db.execute(
        text("UPDATE learning_sessions SET start_time=:old WHERE id=:id"),
        {"old": legacy, "id": created["id"]},
    )
    world.db.commit()
    world.db.expire_all()
    result = world.client.post(
        f"/api/learning/{created['id']}/end", json={"notes": "Keep this work"}
    ).json()
    assert result["status"] == "completed" and result["notes"] == "Keep this work"
    assert result["duration_minutes"] is None and result["duration_known"] is False
    assert result["timestamp_provenance"] == "legacy_unknown"
    assert (
        world.db.execute(
            text("SELECT start_time FROM learning_sessions WHERE id=:id"),
            {"id": created["id"]},
        ).scalar_one()
        == legacy
    )


def test_daily_goal_and_streak_follow_user_day_and_retries(world, monkeypatch):
    world.user = world.learner
    world.learner.settings = {"timezone": "America/Los_Angeles"}
    world.db.commit()
    moment = datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(temporal, "utc_now", lambda: moment)
    goal = world.client.post(
        "/api/gamification/daily-goal", json={"goal_type": "lessons", "target_value": 3}
    ).json()
    assert (
        goal["goal_date"] == "2026-01-01"
        and goal["day_timezone"] == "America/Los_Angeles"
    )
    session = world.client.post(
        "/api/learning/start", json={"content_id": world.content.id}
    ).json()
    endpoint = f"/api/learning/{session['id']}/end"
    assert world.client.post(endpoint, json={}).status_code == 200
    assert world.client.post(endpoint, json={}).status_code == 200
    world.db.refresh(world.learner)
    assert world.learner.last_activity_date.isoformat() == "2026-01-01"
    assert world.learner.current_streak == 1
    assert world.client.get("/api/gamification/daily-goal").json()["current_value"] == 1
    # Switching policy does not reinterpret a bare historic date or erase it.
    world.learner.settings = {**world.learner.settings, "timezone": "UTC"}
    temporal.record_activity_day(world.learner)
    assert world.learner.current_streak == 1


def test_unknown_lockout_fails_closed_and_aware_lockout_never_type_errors(world):
    service = AuthService()
    world.learner.locked_until = datetime(1999, 1, 1)
    world.db.commit()
    assert service._is_account_locked(world.db, world.learner.id)
    world.learner.locked_until = temporal.utc_now() - timedelta(seconds=1)
    world.db.commit()
    assert not service._is_account_locked(world.db, world.learner.id)
    world.learner.locked_until = temporal.utc_now() + timedelta(minutes=1)
    world.db.commit()
    world.db.refresh(world.learner)
    assert service._is_account_locked(world.db, world.learner.id)


def test_legacy_auth_attempts_are_not_assumed_expired(world):
    attempt = AuthAttempt(
        username=world.learner.username,
        user_id=world.learner.id,
        success=False,
        timestamp=datetime(1999, 1, 1),
    )
    world.db.add(attempt)
    world.db.commit()
    service = AuthService()
    service.rate_limit_max_attempts = 1
    with pytest.raises(AuthenticationError, match="unknown timezone"):
        service._check_rate_limit(
            world.db,
            user_id=world.learner.id,
            username=world.learner.username,
            ip_address=None,
        )


def test_unknown_relative_time_is_not_invented():
    assert _format_relative_time(datetime(1999, 1, 1)) == "Unknown timezone"


def test_dashboard_totals_exclude_unknown_duration_history(world):
    from src.api.routes import dashboard
    from src.core.models import SessionStatus

    world.client.app.include_router(dashboard.router)
    world.user = world.learner
    now = temporal.utc_now()
    world.db.add_all(
        [
            LearningSession(
                student_id=world.learner.id,
                content_id=world.content.id,
                start_time=now - timedelta(minutes=10),
                end_time=now,
                duration_minutes=10,
                status=SessionStatus.COMPLETED,
            ),
            LearningSession(
                student_id=world.learner.id,
                content_id=world.content.id,
                start_time=datetime(2026, 1, 1, 12),
                end_time=datetime(2026, 1, 1, 13),
                duration_minutes=60,
                status=SessionStatus.COMPLETED,
            ),
        ]
    )
    world.db.commit()
    response = world.client.get("/api/dashboard/stats").json()
    assert response["completed_lessons"] == 2
    assert response["total_study_time_minutes"] == 10
    assert response["unknown_duration_sessions"] == 1


def test_review_overview_excludes_unknown_due_time(world):
    from src.core.services.spaced_repetition_service import SpacedRepetitionService
    from contextlib import nullcontext

    world.db.add(
        MasteryNode(
            student_id=world.learner.id,
            content_id=world.content.id,
            next_review_due=datetime(1999, 1, 1),
            mastery_level=50,
        )
    )
    world.db.commit()
    service = SpacedRepetitionService(
        SimpleNamespace(get_session=lambda: nullcontext(world.db))
    )
    assert service.get_due_reviews(world.learner.id) == []
    overview = service.get_student_mastery_overview(world.learner.id)
    assert (
        overview["items_due_review"] == 0 and overview["items_unknown_review_time"] == 1
    )
