def _assert_role_string(role):
    assert isinstance(role, str), f"role must be string, got {type(role)}: {role!r}"
    assert role == role.lower(), f"role must be lowercase, got {role!r}"
    assert role in {"student", "teacher", "admin"}, f"unexpected role: {role!r}"


def test_login_returns_role_string_teacher(client, test_teacher):
    resp = client.post(
        "/api/auth/login",
        data={"username": test_teacher.username, "password": "Password123!"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "user" in payload
    _assert_role_string(payload["user"].get("role"))
    assert payload["user"]["role"] == "teacher"


def test_login_returns_role_string_student(client, test_student):
    resp = client.post(
        "/api/auth/login",
        data={"username": test_student.username, "password": "Password123!"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "user" in payload
    _assert_role_string(payload["user"].get("role"))
    assert payload["user"]["role"] == "student"


def test_me_returns_role_string(client, teacher_token):
    resp = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    _assert_role_string(payload.get("role"))
    assert payload["role"] == "teacher"


def test_token_without_exp_is_rejected(client, test_teacher):
    import jwt
    from datetime import datetime, timezone
    from core.services.auth import AuthService

    auth_service = AuthService()
    token = jwt.encode(
        {
            "user_id": test_teacher.id,
            "username": test_teacher.username,
            "role": "teacher",
            "iat": datetime.now(timezone.utc),
        },
        auth_service.jwt_secret,
        algorithm=auth_service.jwt_algorithm,
    )

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, resp.text
