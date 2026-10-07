"""Canonical staff registration with real authentication and disposable SQLite.

No API, authentication or database dependency is replaced. The shared offline
fixture blocks provider/network activity; these requests never need inference.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from scripts.seed_admin import seed_admin_user
from src.core.models import User, UserRole
from src.core.services.database import DatabaseService


PASSWORD = "SyntheticPass123!"
PASSWORD_ERROR = (
    "Password must be at least 8 characters and contain uppercase, "
    "lowercase, digit, and special character"
)


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Keep the shared fixtures' synthetic database under pytest's basetemp."""
    return tmp_path


@pytest.fixture
def registration_client(db_service: DatabaseService) -> Iterator[TestClient]:
    """Use the real application and its unmodified dependency graph."""
    from src.api.main import app

    assert app.dependency_overrides == {}
    with TestClient(app) as client:
        yield client


def _login(client: TestClient, username: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["username"] == username
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(
    registration_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Bootstrap a synthetic admin, then obtain a token through real login."""
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "admin.demo@example.com")
    assert seed_admin_user() == 0
    return _login(registration_client, "admin")


def _payload(username: str = "docente.demo", **changes: Any) -> dict[str, Any]:
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": PASSWORD,
        "first_name": "Demo",
        "last_name": "Account",
        "role": "teacher",
        **changes,
    }


def _register(
    client: TestClient, headers: dict[str, str], **changes: Any
) -> dict[str, Any]:
    response = client.post("/api/auth/register", headers=headers, json=_payload(**changes))
    assert response.status_code == 200, response.text
    return response.json()


def _assert_no_account(db_service: DatabaseService, payload: dict[str, Any]) -> None:
    with db_service.get_session() as session:
        assert session.query(User).filter_by(username=payload["username"]).count() == 0
        assert session.query(User).filter_by(email=payload["email"]).count() == 0


def _assert_admin_session(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "admin"


def test_admin_creates_teacher_without_replacing_admin_session(
    registration_client: TestClient,
    admin_headers: dict[str, str],
    db_service: DatabaseService,
) -> None:
    """A valid demo email succeeds and leaves the original admin token valid."""
    created = _register(registration_client, admin_headers)
    assert created["email"] == "docente.demo@example.com"
    assert created["role"] == "teacher"
    assert created["teacher_id"] is None
    assert "access_token" not in created
    assert "password" not in created and "password_hash" not in created
    with db_service.get_session() as session:
        teacher = session.get(User, created["id"])
        assert teacher is not None
        assert teacher.username == "docente.demo"
        assert teacher.email == "docente.demo@example.com"
        assert teacher.role == UserRole.TEACHER
        assert session.query(User).count() == 2
    teacher_headers = _login(registration_client, "docente.demo")
    assert registration_client.get("/api/auth/me", headers=teacher_headers).json()["role"] == "teacher"
    _assert_admin_session(registration_client, admin_headers)


@pytest.mark.parametrize("domain", ["example.invalid", "example.test"])
def test_reserved_email_has_structured_422_and_corrected_retry_succeeds(
    registration_client: TestClient,
    admin_headers: dict[str, str],
    db_service: DatabaseService,
    domain: str,
) -> None:
    """Real EmailStr errors identify body.email and never persist a partial user."""
    rejected = _payload(email=f"docente.demo@{domain}")
    response = registration_client.post(
        "/api/auth/register", headers=admin_headers, json=rejected
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, list) and len(detail) == 1
    assert detail[0]["loc"] == ["body", "email"]
    assert detail[0]["type"] == "value_error"
    assert detail[0]["msg"].startswith("value is not a valid email address:")
    assert detail[0]["input"] == rejected["email"]
    _assert_no_account(db_service, rejected)
    _assert_admin_session(registration_client, admin_headers)

    created = _register(registration_client, admin_headers)
    assert created["username"] == rejected["username"]
    assert created["email"] == "docente.demo@example.com"
    with db_service.get_session() as session:
        assert session.query(User).count() == 2
        assert session.query(User).filter_by(email=rejected["email"]).count() == 0
    _assert_admin_session(registration_client, admin_headers)


def test_unauthenticated_registration_is_forbidden(
    registration_client: TestClient, db_service: DatabaseService
) -> None:
    """The public endpoint cannot bootstrap an administrator or self-register."""
    payload = _payload(role="admin")
    response = registration_client.post("/api/auth/register", json=payload)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Account creation requires an administrator or teacher"
    _assert_no_account(db_service, payload)


def test_student_cannot_create_any_account(
    registration_client: TestClient,
    admin_headers: dict[str, str],
    db_service: DatabaseService,
) -> None:
    """A real student session cannot create students, teachers or admins."""
    _register(registration_client, admin_headers, username="learner.demo", role="student")
    student_headers = _login(registration_client, "learner.demo")
    for role in ("student", "teacher", "admin"):
        payload = _payload(username=f"blocked.{role}", role=role)
        response = registration_client.post(
            "/api/auth/register", headers=student_headers, json=payload
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Students cannot create user accounts"
        _assert_no_account(db_service, payload)


@pytest.fixture
def teacher_account(
    registration_client: TestClient, admin_headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Create staff through the canonical admin endpoint and log in as staff."""
    teacher = _register(registration_client, admin_headers)
    return teacher, _login(registration_client, teacher["username"])


@pytest.mark.parametrize("explicit_teacher", [False, True])
def test_teacher_creates_only_own_student(
    registration_client: TestClient,
    teacher_account: tuple[dict[str, Any], dict[str, str]],
    db_service: DatabaseService,
    explicit_teacher: bool,
) -> None:
    """Omitted and explicit self-assignment both persist the authenticated teacher."""
    teacher, headers = teacher_account
    assignment = {"teacher_id": teacher["id"]} if explicit_teacher else {}
    student = _register(
        registration_client, headers, username="learner.demo", role="student", **assignment
    )
    assert student["teacher_id"] == teacher["id"]
    assert student["role"] == "student"
    with db_service.get_session() as session:
        saved = session.get(User, student["id"])
        assert saved is not None
        assert saved.teacher_id == teacher["id"]
        assert saved.role == UserRole.STUDENT


def test_teacher_cannot_assign_student_to_another_teacher(
    registration_client: TestClient,
    admin_headers: dict[str, str],
    teacher_account: tuple[dict[str, Any], dict[str, str]],
    db_service: DatabaseService,
) -> None:
    """An existing active second teacher cannot be selected by the first teacher."""
    _, headers = teacher_account
    other = _register(registration_client, admin_headers, username="other.teacher")
    payload = _payload(username="other.learner", role="student", teacher_id=other["id"])
    response = registration_client.post("/api/auth/register", headers=headers, json=payload)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Teachers can only enroll their own learners"
    _assert_no_account(db_service, payload)


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_teacher_cannot_create_elevated_account(
    registration_client: TestClient,
    teacher_account: tuple[dict[str, Any], dict[str, str]],
    db_service: DatabaseService,
    role: str,
) -> None:
    """A valid teacher token does not grant staff-creation privileges."""
    _, headers = teacher_account
    payload = _payload(username=f"elevated.{role}", role=role)
    response = registration_client.post("/api/auth/register", headers=headers, json=payload)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Teachers can only create student accounts"
    _assert_no_account(db_service, payload)


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("Aa1!aaa", id="under-eight-characters"),
        pytest.param("aaaaaa1!", id="missing-uppercase"),
        pytest.param("AAAAAA1!", id="missing-lowercase"),
        pytest.param("Aaaaaaa!", id="missing-digit"),
        pytest.param("Aaaaaaa1", id="missing-symbol"),
        pytest.param("Aa1!" + "a" * 69, id="over-72-bytes"),
        pytest.param("Aa1!" + "\u00e9" * 35, id="utf8-over-72-bytes"),
    ],
)
def test_registration_password_rejections_are_unchanged(
    registration_client: TestClient,
    admin_headers: dict[str, str],
    db_service: DatabaseService,
    password: str,
) -> None:
    """Registration still applies the existing strength and bcrypt byte limits."""
    payload = _payload(password=password)
    response = registration_client.post(
        "/api/auth/register", headers=admin_headers, json=payload
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == PASSWORD_ERROR
    _assert_no_account(db_service, payload)


@pytest.mark.parametrize("password", ["Aa1!aaaa", "Aa1!" + "a" * 68])
def test_registration_password_boundaries_are_unchanged(
    registration_client: TestClient, admin_headers: dict[str, str], password: str
) -> None:
    """Valid 8- and 72-byte credentials remain accepted and work for real login."""
    created = _register(registration_client, admin_headers, password=password)
    _login(registration_client, created["username"], password)
    _assert_admin_session(registration_client, admin_headers)
