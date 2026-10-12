from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.core.models import User, UserRole, DailyGoal, GamificationSettings
from src.core.security import hash_password
from sqlalchemy import select

MADRID = ZoneInfo("Europe/Madrid")


def madrid_today(instant=None):
    """Day basis for the campaign reference zone, computed from a UTC instant.

    The product contract resolves the goal day under the user's explicit zone
    and never infers the host/browser zone, so the expectation must be derived
    from the same explicit zone instead of the host's ``date.today()``.
    """
    instant = instant or datetime.now(timezone.utc)
    return instant.astimezone(MADRID).date()


def test_daily_goal_full_flow(client, db_service):
    """
    Complete flow test for setting and retrieving daily goals.
    Verifies both API response and Database state.
    """
    # 1. Setup User
    username = "goal_bug_user"
    password = "Password123!"

    # Create user directly in DB with the campaign reference zone set explicitly.
    # The product resolves the goal day under the user's explicit zone, so the
    # test must supply it rather than rely on any host/UTC coincidence.
    user = User(
        username=username,
        email="goal_bug@test.com",
        role=UserRole.STUDENT,
        first_name="Goal",
        last_name="Tester",
        password_hash=hash_password(password),
        settings={"timezone": "Europe/Madrid"},
    )

    # Use a fresh session for setup to ensure commit
    with db_service.get_session() as session:
        session.add(user)
        session.commit()
        # Get ID for later verification
        user_id = user.id

    # 2. Login
    login_res = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n[INFO] User {username} logged in. Token obtained.")

    # 3. Get Initial Goal (Expect generic or empty)
    # The current API implementation returns default goal if none exists
    get_res = client.get("/api/gamification/daily-goal", headers=headers)
    print(f"[INFO] Initial GET response: {get_res.status_code} - {get_res.text}")
    assert get_res.status_code == 200

    # 4. Set Goal
    goal_payload = {"goal_type": "exercises", "target_value": 10}
    print(f"[INFO] Setting goal: {goal_payload}")
    set_res = client.post(
        "/api/gamification/daily-goal", json=goal_payload, headers=headers
    )
    assert set_res.status_code == 200, f"Set goal failed: {set_res.text}"
    set_data = set_res.json()
    assert set_data["target_value"] == 10
    assert set_data["goal_type"] == "exercises"
    print("[INFO] Goal set successfully via API.")

    # 5. Verify Persistence via API
    get_res_2 = client.get("/api/gamification/daily-goal", headers=headers)
    assert get_res_2.status_code == 200
    final_data = get_res_2.json()
    print(f"[INFO] Retrieve after set: {final_data}")

    assert final_data["target_value"] == 10
    assert final_data["goal_type"] == "exercises"
    assert final_data["goal_date"] == str(madrid_today())

    # 6. Verify Persistence in DB
    with db_service.get_session() as session:
        stmt = select(DailyGoal).where(
            DailyGoal.user_id == user_id, DailyGoal.goal_date == madrid_today()
        )
        db_goal = session.execute(stmt).scalar_one_or_none()
        assert db_goal is not None, "Goal not found in database!"
        assert db_goal.target_value == 10
        assert db_goal.goal_type == "exercises"
        print("[INFO] Goal confirmed in Database.")


def test_daily_goal_persistence_settings(client, db_service):
    """
    Test verifying that saving a goal as default persists it for future use.
    """
    # 1. Setup User
    username = "persist_user"
    password = "Password123!"

    user = User(
        username=username,
        email="persist@test.com",
        role=UserRole.STUDENT,
        first_name="Persist",
        last_name="Tester",
        password_hash=hash_password(password),
    )

    with db_service.get_session() as session:
        session.add(user)
        session.commit()
        user_id = user.id

    # 2. Login
    login_res = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Set Goal with Save as Default
    goal_payload = {"goal_type": "minutes", "target_value": 45, "save_as_default": True}
    set_res = client.post(
        "/api/gamification/daily-goal", json=goal_payload, headers=headers
    )
    assert set_res.status_code == 200
    print("[INFO] Goal set with save_as_default=True")

    # 4. Verify GamificationSettings created in DB
    with db_service.get_session() as session:
        stmt = select(GamificationSettings).where(
            GamificationSettings.user_id == user_id
        )
        settings = session.execute(stmt).scalar_one_or_none()
        assert settings is not None, "GamificationSettings not created!"
        assert settings.default_goal_type == "minutes"
        assert settings.default_goal_target == 45
        print("[INFO] GamificationSettings confirmed in Database.")

        # 5. Simulate New Day: Delete today's goal
        # This forces the GET endpoint to look for defaults and create a new goal
        del_stmt = select(DailyGoal).where(DailyGoal.user_id == user_id)
        current_goal = session.execute(del_stmt).scalar_one()
        session.delete(current_goal)
        session.commit()
        print("[INFO] Deleted today's goal to simulate new day/no goal.")

    # 6. Verify Auto-Creation from Defaults
    get_res = client.get("/api/gamification/daily-goal", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    print(f"[INFO] Retrieve after delete: {data}")

    assert data["id"] is not None  # Should be a new real goal
    assert data["goal_type"] == "minutes"  # From default
    assert data["target_value"] == 45  # From default
    print("[INFO] New goal auto-created from defaults successfully.")


def test_daily_goal_follows_madrid_across_utc_midnight(client, db_service, monkeypatch):
    """Regression for SLM-AUTO-016: the goal day follows Europe/Madrid.

    At 23:30 UTC Madrid is already the next civil day. The API must create
    and return the goal dated in Madrid, whatever the host date is.
    """
    from src.core import temporal

    frozen = datetime(2026, 10, 11, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(temporal, "utc_now", lambda: frozen)
    expected = madrid_today(frozen)
    assert str(expected) == "2026-10-12"

    user = User(
        username="madrid_boundary_user",
        email="madrid@test.com",
        role=UserRole.STUDENT,
        first_name="Madrid",
        last_name="Tester",
        password_hash=hash_password("Password123!"),
        settings={"timezone": "Europe/Madrid"},
    )
    with db_service.get_session() as session:
        session.add(user)
        session.commit()
        user_id = user.id

    login_res = client.post(
        "/api/auth/login", data={"username": "madrid_boundary_user", "password": "Password123!"}
    )
    assert login_res.status_code == 200
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    set_res = client.post(
        "/api/gamification/daily-goal",
        json={"goal_type": "lessons", "target_value": 3},
        headers=headers,
    )
    assert set_res.status_code == 200
    assert set_res.json()["goal_date"] == str(expected)

    get_res = client.get("/api/gamification/daily-goal", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["goal_date"] == str(expected)

    with db_service.get_session() as session:
        stmt = select(DailyGoal).where(
            DailyGoal.user_id == user_id, DailyGoal.goal_date == expected
        )
        assert session.execute(stmt).scalar_one_or_none() is not None
