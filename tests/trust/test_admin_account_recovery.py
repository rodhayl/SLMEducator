"""Confirmed administrative recovery revokes sessions and preserves audit history."""

from datetime import datetime, timezone
from sqlalchemy import text

from src.core.models import AuthAttempt, User, UserRole
from src.core.services.auth import get_auth_service
from tests.trust.test_product_journeys import add_admin
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def test_inactive_list_and_status_require_admin_and_confirmed_target(scenario):
    client, db, users, selected, _, _, _ = scenario
    admin = add_admin(db)
    target = users["learner_a"]
    selected[0] = users["teacher_a"]
    assert client.get("/api/auth/users?include_inactive=true").status_code == 403
    assert (
        client.patch(
            f"/api/auth/users/{target.id}/status",
            json={"active": False, "confirm": True},
        ).status_code
        == 403
    )
    selected[0] = admin
    assert (
        client.patch(
            f"/api/auth/users/{target.id}/status", json={"active": False}
        ).status_code
        == 409
    )
    service = get_auth_service()
    token = service._generate_jwt_token(target)
    response = client.patch(
        f"/api/auth/users/{target.id}/status", json={"active": False, "confirm": True}
    )
    assert response.status_code == 200 and response.json() == {
        "id": target.id,
        "active": False,
        "sessions_revoked": True,
    }
    assert service.validate_token(token) is None
    assert target.id not in [
        item["id"] for item in client.get("/api/auth/users").json()
    ]
    assert target.id in [
        item["id"]
        for item in client.get("/api/auth/users?include_inactive=true").json()
    ]
    assert (
        client.patch(
            f"/api/auth/users/{admin.id}/status",
            json={"active": False, "confirm": True},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/auth/users/{target.id}/status",
            json={"active": True, "confirm": True},
        ).status_code
        == 200
    )
    db.refresh(target)
    new_token = service._generate_jwt_token(target)
    # A stale-but-confirmed Activate still truthfully revokes existing sessions.
    assert client.patch(
        f"/api/auth/users/{target.id}/status", json={"active": True, "confirm": True}
    ).json()["sessions_revoked"]
    assert service.validate_token(new_token) is None


def test_password_recovery_revokes_tokens_and_preserves_unknown_history_bytes(scenario):
    client, db, users, selected, _, _, _ = scenario
    admin = add_admin(db)
    target = users["learner_a"]
    service = get_auth_service()
    target.password_hash = service._hash_password("SyntheticOriginal123!")
    for _ in range(6):
        db.add(
            AuthAttempt(
                user_id=target.id,
                username=target.username,
                success=False,
                timestamp=datetime.now(timezone.utc),
            )
        )
    db.commit()
    db.execute(
        text(
            "UPDATE auth_attempts SET timestamp='2018-11-04 01:30:00' WHERE user_id=:id"
        ),
        {"id": target.id},
    )
    db.execute(
        text("UPDATE users SET locked_until='2018-11-04 01:30:00' WHERE id=:id"),
        {"id": target.id},
    )
    db.commit()
    token = service._generate_jwt_token(target)
    preserved = db.execute(
        text("SELECT id,timestamp FROM auth_attempts WHERE user_id=:id ORDER BY id"),
        {"id": target.id},
    ).all()
    password = "SyntheticRecovery789!"
    selected[0] = users["teacher_a"]
    assert (
        client.post(
            f"/api/auth/users/{target.id}/reset-password",
            json={"new_password": password, "confirm": True},
        ).status_code
        == 403
    )
    selected[0] = admin
    assert (
        client.post(
            f"/api/auth/users/{target.id}/reset-password",
            json={"new_password": password},
        ).status_code
        == 409
    )
    result = client.post(
        f"/api/auth/users/{target.id}/reset-password",
        json={"new_password": password, "confirm": True},
    )
    assert result.status_code == 200, result.text
    assert result.json() == {"id": target.id, "reset": True, "sessions_revoked": True}
    assert password not in result.text
    db.expire_all()
    assert db.get(User, target.id).locked_until is None
    assert service.validate_token(token) is None
    assert (
        db.execute(
            text(
                "SELECT id,timestamp FROM auth_attempts WHERE user_id=:id ORDER BY id"
            ),
            {"id": target.id},
        ).all()
        == preserved
    )
    login = client.post(
        "/api/auth/login", data={"username": target.username, "password": password}
    )
    assert login.status_code == 200, login.text


def test_missing_html_is_real_404_without_legacy_gui_fallback(scenario):
    client, *_ = scenario
    response = client.get("/does-not-exist-synthetic.html")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert "<html" not in response.text.lower()
