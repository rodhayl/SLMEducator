"""Real-token account deep links retain the existing bounded-directory scope."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from scripts.seed_admin import seed_admin_user
from src.api.routes.auth import UserListResponse
from src.core.models import User, UserRole
from src.core.services.database import DatabaseService


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Keep all data in pytest's disposable test directory."""
    return tmp_path


@pytest.fixture
def client(db_service: DatabaseService) -> Iterator[TestClient]:
    """Use real application dependencies, authentication, and SQLite."""
    from src.api.main import app

    assert not app.dependency_overrides
    with TestClient(app) as instance:
        yield instance


def login(client: TestClient, username: str) -> dict[str, str]:
    """Obtain a real access token for a synthetic account."""
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "SyntheticDetail123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def staff(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, str], dict[str, Any]]:
    """Bootstrap one administrator and create a teacher with the real API."""
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", "SyntheticDetail123!")
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "admin.detail@example.com")
    assert seed_admin_user() == 0
    headers = login(client, "admin")
    return headers, register(client, headers, "teacher.detail", "teacher")


def register(
    client: TestClient,
    headers: dict[str, str],
    username: str,
    role: str,
    **extra: Any,
) -> dict[str, Any]:
    """Create only disposable synthetic accounts via the supported endpoint."""
    response = client.post(
        "/api/auth/register",
        headers=headers,
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SyntheticDetail123!",
            "first_name": username,
            "last_name": "Example",
            "role": role,
            **extra,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_admin_detail_has_only_directory_fields_including_self_and_inactive(
    client: TestClient, staff: tuple[dict[str, str], dict[str, Any]]
) -> None:
    """Admin detail is independent of list exclusion and preserves field scope."""
    headers, teacher = staff
    own = client.get("/api/auth/me", headers=headers).json()
    for identifier in (own["id"], teacher["id"]):
        response = client.get(f"/api/auth/users/{identifier}", headers=headers)
        assert response.status_code == 200
        assert set(response.json()) == set(UserListResponse.model_fields)
        assert response.json()["id"] == identifier
    assert client.patch(
        f"/api/auth/users/{teacher['id']}/status",
        headers=headers,
        json={"active": False, "confirm": True},
    ).status_code == 200
    detail = client.get(f"/api/auth/users/{teacher['id']}", headers=headers)
    assert detail.status_code == 200 and detail.json()["active"] is False


def test_teacher_deep_link_requires_active_assigned_student(
    client: TestClient, staff: tuple[dict[str, str], dict[str, Any]]
) -> None:
    """Hidden staff controls cannot be bypassed with a guessed direct URL."""
    admin, teacher = staff
    teacher_headers = login(client, teacher["username"])
    student = register(client, teacher_headers, "own.detail", "student")
    other = register(client, admin, "unassigned.detail", "student")
    for identifier in (teacher["id"], other["id"], 999999):
        response = client.get(f"/api/auth/users/{identifier}", headers=teacher_headers)
        assert response.status_code == 404
        assert response.json() == {"detail": "Account not available"}
    detail = client.get(f"/api/auth/users/{student['id']}", headers=teacher_headers)
    assert detail.status_code == 200 and detail.json()["teacher_id"] == teacher["id"]
    assert client.patch(
        f"/api/auth/users/{student['id']}/status",
        headers=admin,
        json={"active": False, "confirm": True},
    ).status_code == 200
    assert client.get(
        f"/api/auth/users/{student['id']}", headers=teacher_headers
    ).status_code == 404


def test_explicit_reassignment_revokes_old_teacher_detail_and_keeps_notes_private(
    client: TestClient, staff: tuple[dict[str, str], dict[str, Any]]
) -> None:
    """Responsible teacher and note author remain separate identities."""
    admin, teacher_a = staff
    teacher_b = register(client, admin, "teacher.other", "teacher")
    headers_a = login(client, teacher_a["username"])
    headers_b = login(client, teacher_b["username"])
    student = register(client, headers_a, "reassigned.detail", "student")
    path = f"/api/students/{student['id']}"
    assert client.post(
        f"{path}/notes", headers=headers_a, json={"notes": "Synthetic private note A"}
    ).status_code == 200
    enrollment = client.put(
        f"{path}/teacher", headers=admin, json={"teacher_id": teacher_b["id"]}
    )
    assert enrollment.status_code == 200
    assert enrollment.json()["existing_assignments_preserved"] is True
    detail_path = f"/api/auth/users/{student['id']}"
    assert client.get(detail_path, headers=headers_a).status_code == 404
    assert client.get(detail_path, headers=headers_b).status_code == 200
    assert client.get(f"{path}/notes", headers=headers_a).status_code == 403
    assert client.get(f"{path}/notes", headers=headers_b).json() == {"notes": ""}
    assert client.get(f"{path}/notes", headers=admin).json() == {"notes": ""}


def test_student_and_anonymous_cannot_read_accounts(
    client: TestClient, staff: tuple[dict[str, str], dict[str, Any]]
) -> None:
    """A learner has no directory/detail capability, including their own URL."""
    admin, teacher = staff
    student = register(client, admin, "student.detail", "student")
    headers = login(client, student["username"])
    for identifier in (student["id"], teacher["id"], 999999):
        path = f"/api/auth/users/{identifier}"
        assert client.get(path, headers=headers).status_code == 403
        assert client.get(path).status_code == 401


@pytest.mark.parametrize("identifier", ["0", "-1", "1.2", "not-an-id", "99999999999999999999999"])
def test_detail_requires_positive_integer(
    client: TestClient,
    staff: tuple[dict[str, str], dict[str, Any]],
    identifier: str,
) -> None:
    """Malformed identifiers never reach the account lookup."""
    admin, _ = staff
    assert client.get(f"/api/auth/users/{identifier}", headers=admin).status_code == 422


def test_detail_resolves_beyond_directory_limit(
    client: TestClient,
    staff: tuple[dict[str, str], dict[str, Any]],
    db_service: DatabaseService,
) -> None:
    """A valid direct link does not depend on the first 500 sorted accounts."""
    admin, _ = staff
    with db_service.get_session() as session:
        for index in range(501):
            session.add(User(
                username=f"synthetic.bulk.{index}",
                email=f"synthetic.bulk.{index}@example.com",
                password_hash="not-a-login-credential",
                first_name=f"AAA{index:04d}",
                last_name="Synthetic",
                role=UserRole.STUDENT,
            ))
        target = User(
            username="synthetic.last", email="synthetic.last@example.com",
            password_hash="not-a-login-credential", first_name="ZZZ",
            last_name="Synthetic", role=UserRole.STUDENT,
        )
        session.add(target)
        session.commit()
        identifier = target.id
    directory = client.get("/api/auth/users?limit=500", headers=admin).json()
    assert len(directory) == 500
    assert identifier not in {item["id"] for item in directory}
    response = client.get(f"/api/auth/users/{identifier}", headers=admin)
    assert response.status_code == 200 and response.json()["id"] == identifier
