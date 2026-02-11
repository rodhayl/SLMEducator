from datetime import date
from src.core.models import User, UserRole, DailyGoal, GamificationSettings
from src.core.security import hash_password
from sqlalchemy import select


def test_daily_goal_full_flow(client, db_service):
    """
    Complete flow test for setting and retrieving daily goals.
    Verifies both API response and Database state.
    """
    # 1. Setup User
    username = "goal_bug_user"
    password = "Password123!"

    # Create user directly in DB
    user = User(
        username=username,
        email="goal_bug@test.com",
        role=UserRole.STUDENT,
        first_name="Goal",
        last_name="Tester",
        password_hash=hash_password(password),
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
    assert final_data["goal_date"] == str(date.today())

    # 6. Verify Persistence in DB
    with db_service.get_session() as session:
        stmt = select(DailyGoal).where(
            DailyGoal.user_id == user_id, DailyGoal.goal_date == date.today()
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
