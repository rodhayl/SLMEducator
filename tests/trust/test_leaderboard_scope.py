"""Participation XP never expands the classroom's enrollment directory."""

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.dependencies import get_db
from src.api.routes.gamification import router
from src.api.security import get_current_user
from src.core.models import (
    LeaderboardEntry,
    StudentStudyPlan,
    StudyPlan,
    User,
    UserRole,
)


@pytest.fixture
def leaderboard(db_session):
    """Private synthetic cohorts with legacy assignment and stale cache edges."""
    specs = [
        ("admin", UserRole.ADMIN, 300),
        ("teacher", UserRole.TEACHER, 400),
        ("other_teacher", UserRole.TEACHER, 500),
        ("learner", UserRole.STUDENT, 100),
        ("classmate", UserRole.STUDENT, 200),
        ("outsider", UserRole.STUDENT, 900),
        ("legacy", UserRole.STUDENT, 150),
        ("unassigned", UserRole.STUDENT, 800),
        ("inactive", UserRole.STUDENT, 1000),
    ]
    users = {}
    for name, role, xp in specs:
        user = User(
            username=name,
            email=f"{name}@example.invalid",
            first_name=name,
            last_name="Synthetic",
            role=role,
            xp=xp,
            password_hash="synthetic-unusable-hash",
        )
        db_session.add(user)
        users[name] = user
    db_session.flush()
    for name in ("learner", "classmate", "inactive"):
        users[name].teacher_id = users["teacher"].id
    users["outsider"].teacher_id = users["other_teacher"].id
    users["inactive"].active = False
    plan = StudyPlan(title="Legacy assignment", creator_id=users["teacher"].id)
    db_session.add(plan)
    db_session.flush()
    # An old assignment cannot override somebody else's explicit enrollment.
    for name in ("legacy", "outsider"):
        db_session.add(
            StudentStudyPlan(student_id=users[name].id, study_plan_id=plan.id)
        )
    db_session.commit()
    app = FastAPI()
    app.include_router(router)
    state = SimpleNamespace(db=db_session, users=users, current=users["learner"])
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: state.current
    with TestClient(app) as client:
        state.client = client
        yield state


def cache_rows(state):
    """A cache contains global ranks which must not be returned outside scope."""
    for rank, user in enumerate(
        sorted(state.users.values(), key=lambda user: -user.xp), 7
    ):
        state.db.add(
            LeaderboardEntry(
                user_id=user.id, period="weekly", xp=user.xp + 10, rank=rank
            )
        )
    state.db.add(LeaderboardEntry(user_id=999999, period="weekly", xp=5000, rank=1))
    state.db.commit()


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("viewer", ["learner", "teacher", "admin"])
def test_scope_applies_to_live_and_cached_rows(leaderboard, cached, viewer):
    if cached:
        cache_rows(leaderboard)
    leaderboard.current = leaderboard.users[viewer]
    response = leaderboard.client.get("/api/gamification/leaderboard?limit=100")
    assert response.status_code == 200, response.text
    rows = response.json()
    expected = (
        {"learner"}
        if viewer == "learner"
        else (
            {"learner", "classmate", "legacy"}
            if viewer == "teacher"
            else set(leaderboard.users) - {"inactive"}
        )
    )
    assert {row["username"] for row in rows} == expected
    assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
    assert all(
        row["metric_type"] == "participation" and row["rank_scope"] == "visible_users"
        for row in rows
    )
    assert all(
        row["xp"] == leaderboard.users[row["username"]].xp + (10 if cached else 0)
        for row in rows
    )


@pytest.mark.parametrize("cached", [False, True])
def test_authorized_scope_is_applied_before_limit(leaderboard, cached):
    if cached:
        cache_rows(leaderboard)
    leaderboard.current = leaderboard.users["teacher"]
    response = leaderboard.client.get("/api/gamification/leaderboard?limit=1")
    assert response.status_code == 200
    assert [(row["username"], row["rank"]) for row in response.json()] == [
        ("classmate", 1)
    ]


def test_foreign_cache_rows_do_not_escape_through_fallback(leaderboard):
    outsider = leaderboard.users["outsider"]
    leaderboard.db.add(
        LeaderboardEntry(user_id=outsider.id, period="weekly", xp=9999, rank=1)
    )
    leaderboard.db.commit()
    response = leaderboard.client.get("/api/gamification/leaderboard")
    assert response.status_code == 200
    assert [(row["username"], row["xp"]) for row in response.json()] == [
        ("learner", 100)
    ]


@pytest.mark.parametrize("limit", [0, -1, 101, 999999, "invalid"])
def test_leaderboard_limit_is_bounded(leaderboard, limit):
    assert (
        leaderboard.client.get(
            f"/api/gamification/leaderboard?limit={limit}"
        ).status_code
        == 422
    )
