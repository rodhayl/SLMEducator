"""Real offline API contracts for the React admin/teacher/student vertical.

All accounts, courses, notes and databases are disposable synthetic fixtures.
No application, database or authentication dependency is replaced. Browser
navigation and presentation remain covered separately by frontend tests.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from scripts.seed_admin import seed_admin_user
from src.core.models import User
from src.core.services.database import DatabaseService

PASSWORD = "SyntheticVertical123!"


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Keep the shared isolated database and logs under this run's basetemp."""
    return tmp_path


@pytest.fixture
def vertical_client(db_service: DatabaseService) -> Iterator[TestClient]:
    """Exercise the real app with the shared disposable database singleton."""
    from src.api.main import app

    assert app.dependency_overrides == {}
    with TestClient(app) as client:
        yield client


def _json(
    client: TestClient, method: str, path: str, headers: dict[str, str],
    payload: Any = None, expected: int = 200,
) -> Any:
    """Check an exact status before using any synthetic response body."""
    response = client.request(method, path, headers=headers, json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def _login(client: TestClient, username: str) -> dict[str, str]:
    """Obtain a real authenticated token for a disposable account."""
    response = client.post(
        "/api/auth/login", data={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["username"] == username
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _account(username: str, role: str, **changes: Any) -> dict[str, Any]:
    """Supply the same canonical registration fields as the frontend."""
    return {
        "username": username, "email": f"{username}@example.com",
        "password": PASSWORD, "first_name": "Synthetic", "last_name": role,
        "role": role, **changes,
    }


def _enroll_class(
    client: TestClient, db: DatabaseService, admin: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prove D3 corrected retry, explicit enrollment and creator identity."""
    payload = _account("vertical.teacher", "teacher", email="teacher@example.invalid")
    invalid = _json(client, "POST", "/api/auth/register", admin, payload, 422)
    assert invalid["detail"][0]["loc"] == ["body", "email"]
    assert invalid["detail"][0]["type"] == "value_error"
    with db.get_session() as session:
        assert session.query(User).filter_by(username=payload["username"]).count() == 0
    payload["email"] = "vertical.teacher@example.com"
    teacher = _json(client, "POST", "/api/auth/register", admin, payload)
    student = _json(
        client, "POST", "/api/auth/register", admin,
        _account("vertical.student", "student", teacher_id=teacher["id"]),
    )
    assert teacher["role"] == "teacher" and student["role"] == "student"
    assert student["teacher_id"] == teacher["id"]
    for account in (teacher, student):
        assert "access_token" not in account and "password_hash" not in account
    creator = _json(client, "GET", "/api/auth/me", admin)
    assert creator["username"] == "admin" and creator["role"] == "admin"
    return teacher, student


def _publish_course(
    client: TestClient, teacher: dict[str, str], student_id: int
) -> tuple[int, int]:
    """Create an independent lesson and explicitly save/review/publish/assign."""
    lesson = _json(client, "POST", "/api/content/", teacher, {
        "title": "Manual motion lesson", "content_type": "lesson",
        "content_data": {"content": "An object's motion changes when a net force acts."},
        "difficulty": 1, "is_personal": False,
    })
    payload = {
        "title": "Synthetic mechanics", "description": "Offline vertical fixture",
        "is_public": False,
        "phases": [{"name": "Motion", "content_ids": [lesson["id"]]}],
    }
    plan = _json(client, "POST", "/api/study-plans/", teacher, payload)
    path = f"/api/study-plans/{plan['id']}"
    assert plan["is_public"] is False
    assert _json(client, "GET", f"{path}/workflow", teacher) == {
        "status": "draft", "version": 0, "read_only": False,
    }
    _json(client, "POST", f"{path}/assign", teacher, {"student_ids": [student_id]}, 409)
    reviewed = _json(client, "POST", f"{path}/workflow", teacher, {"action": "review"})
    assert reviewed["status"] == "reviewed" and reviewed["version"] == 0
    published = _json(client, "POST", f"{path}/workflow", teacher, {
        "action": "publish", "is_public": False,
    })
    assert published["status"] == "published" and published["version"] == 1
    assert published["snapshot"] == reviewed["snapshot"]
    receipt = _json(client, "POST", f"{path}/assign", teacher, {"student_ids": [student_id]})
    assert receipt == {"study_plan_id": plan["id"], "assigned_student_ids": [student_id], "already_assigned_student_ids": []}
    assert _json(client, "GET", f"{path}/workflow", teacher)["read_only"] is True
    _json(client, "PUT", path, teacher, payload, 409)
    return plan["id"], lesson["id"]


def _read_pause_continue(
    client: TestClient, student: dict[str, str], plan_id: int, content_id: int
) -> dict[str, Any]:
    """Pause saves notes without ending or completing; resume preserves identity."""
    course = _json(client, "GET", f"/api/study-plans/{plan_id}/tree", student)
    assert [item["id"] for item in course["contents"]] == [content_id]
    assert _json(client, "GET", "/api/learning/active", student) is None
    start = {"content_id": content_id, "study_plan_id": plan_id}
    session = _json(client, "POST", "/api/learning/start", student, start)
    assert session["status"] == "active"
    assert session["context_revision"]["study_plan_id"] == plan_id
    assert session["context_revision"]["course_version"] == 1
    assert session["content_snapshot"]["id"] == content_id
    notes = "Synthetic note: distinguish force from motion."
    saved = _json(client, "PATCH", f"/api/learning/{session['id']}/notes", student, {"notes": notes})
    assert saved["notes"] == notes and saved["status"] == "active"
    # The existing backend has no pause endpoint. Leaving after saving notes is
    # deliberately not an /end or course-progress request.
    active = _json(client, "GET", "/api/learning/active", student)
    assert active["id"] == session["id"] and active["notes"] == notes
    continued = _json(client, "POST", "/api/learning/start", student, start)
    assert continued["id"] == session["id"] and continued["notes"] == notes
    progress = _json(client, "GET", f"/api/study-plans/{plan_id}/my-progress", student)
    assert progress["completed_content_ids"] == [] and progress["completion_percentage"] == 0
    return continued


def _finish_and_restore(
    client: TestClient, student: dict[str, str], session: dict[str, Any], plan_id: int,
) -> int:
    """End/progress are separate confirmed phases; restored notes stay intact."""
    path = f"/api/learning/{session['id']}"
    ended = _json(client, "POST", f"{path}/end", student, {
        "notes": session["notes"], "difficulty_rating": 3,
    })
    assert ended["status"] == "completed" and ended["notes"] == session["notes"]
    rewarded_xp = _json(client, "GET", "/api/gamification/profile", student)["xp"]
    assert rewarded_xp >= 50  # The first lesson can also earn a configured badge.
    before = _json(client, "GET", f"/api/study-plans/{plan_id}/my-progress", student)
    assert before["completed_content_ids"] == []
    completion = {"completed_content_id": session["content_id"], "current_phase_index": 0, "current_order_index": 0}
    progress = _json(client, "POST", f"/api/study-plans/{plan_id}/progress", student, completion)
    assert progress["completed_content_ids"] == [session["content_id"]]
    assert progress["completion_percentage"] == 100
    history = _json(client, "GET", f"/api/learning/history/{session['content_id']}", student)
    assert len(history) == 1 and history[0]["id"] == session["id"]
    restored = _json(client, "POST", f"{path}/restore", student)
    assert restored["id"] == session["id"] and restored["status"] == "active"
    assert restored["notes"] == session["notes"]
    assert restored["content_snapshot"] == session["content_snapshot"]
    assert restored["context_revision"] == session["context_revision"]
    _json(client, "POST", f"{path}/end", student, {"notes": session["notes"]})
    repeated = _json(client, "POST", f"/api/study-plans/{plan_id}/progress", student, completion)
    assert repeated["completed_content_ids"] == [session["content_id"]]
    assert _json(client, "GET", "/api/gamification/profile", student)["xp"] == rewarded_xp
    return rewarded_xp


def test_real_three_role_manual_learning_vertical(
    vertical_client: TestClient, db_service: DatabaseService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Walk the new UI's concrete real API contracts without providers or servers."""
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "vertical.admin@example.com")
    assert seed_admin_user() == 0
    client = vertical_client
    admin_headers = _login(client, "admin")
    teacher, student = _enroll_class(client, db_service, admin_headers)
    teacher_headers = _login(client, teacher["username"])
    student_headers = _login(client, student["username"])
    roster = _json(client, "GET", "/api/students/", teacher_headers)
    assert [learner["id"] for learner in roster] == [student["id"]]
    assert roster[0]["teacher_id"] == teacher["id"]
    plan_id, content_id = _publish_course(client, teacher_headers, student["id"])
    own_courses = _json(client, "GET", "/api/study-plans/", student_headers)
    assert [course["id"] for course in own_courses] == [plan_id]
    _json(client, "GET", "/api/students/", student_headers, expected=403)
    _json(client, "POST", f"/api/study-plans/{plan_id}/workflow", student_headers, {"action": "review"}, 403)
    session = _read_pause_continue(client, student_headers, plan_id, content_id)
    _json(client, "PATCH", f"/api/learning/{session['id']}/notes", teacher_headers, {"notes": "Unauthorized change"}, 404)
    rewarded_xp = _finish_and_restore(client, student_headers, session, plan_id)
    progress = _json(client, "GET", f"/api/students/{student['id']}/progress", teacher_headers)
    assert progress["lessons_completed"] == 1
    assert progress["assessments_taken"] == 0 and progress["avg_score"] is None
    with db_service.get_session() as db:
        learner = db.get(User, student["id"])
        assert learner is not None and learner.xp == rewarded_xp
    assert _json(client, "GET", "/api/auth/me", admin_headers)["role"] == "admin"


def test_course_provenance_receipts_preserve_public_reuse_and_private_denial(
    vertical_client: TestClient, db_service: DatabaseService, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read capabilities reflect existing author/public policy without widening it."""
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "vertical.admin@example.com")
    assert seed_admin_user() == 0
    client, admin = vertical_client, _login(vertical_client, "admin")
    teacher, student = _enroll_class(client, db_service, admin)
    teacher_auth, student_auth = _login(client, teacher["username"]), _login(client, student["username"])
    body = {"content_type": "lesson", "difficulty": 1, "is_personal": False, "content_data": {"content": "Synthetic provenance explanation."}}
    private = _json(client, "POST", "/api/content/", admin, {**body, "title": "Private admin lesson"})
    shared = _json(client, "POST", "/api/content/", admin, {**body, "title": "Public original lesson"})
    public_source = _json(client, "POST", "/api/study-plans/", admin, {
        "title": "Original source", "phases": [{"name": "Source", "content_ids": [shared["id"]]}],
    })
    source_path = f"/api/study-plans/{public_source['id']}/workflow"
    _json(client, "POST", source_path, admin, {"action": "review"})
    _json(client, "POST", source_path, admin, {"action": "publish", "is_public": True})
    materials = {item["id"]: item for item in _json(client, "GET", "/api/content/", admin)}
    assert materials[private["id"]]["public_reuse"] is False
    assert materials[shared["id"]]["public_reuse"] is True
    assert _json(client, "GET", f"/api/content/{shared['id']}", teacher_auth)["public_reuse"] is True
    _json(client, "GET", f"/api/content/{private['id']}", teacher_auth, expected=403)
    payload = {"title": "Teacher course", "phases": [{"name": "Reuse", "content_ids": [shared["id"]]}]}
    plan = _json(client, "POST", "/api/study-plans/", teacher_auth, payload)
    assert plan["creator_id"] == teacher["id"]
    plan_path = f"/api/study-plans/{plan['id']}"
    assert _json(client, "GET", f"{plan_path}/tree", admin)["creator_id"] == teacher["id"]
    _json(client, "GET", f"{plan_path}/tree", student_auth, expected=403)
    _json(client, "PUT", plan_path, teacher_auth, {
        **payload, "phases": [{"name": "Reuse", "content_ids": [private["id"]]}],
    }, 403)
    _json(client, "POST", f"{plan_path}/workflow", teacher_auth, {"action": "review"})
    _json(client, "POST", f"{plan_path}/workflow", teacher_auth, {"action": "publish"})
    _json(client, "POST", f"{plan_path}/assign", teacher_auth, {"student_ids": [student["id"]]})
    assert _json(client, "GET", f"/api/content/{shared['id']}", student_auth)["id"] == shared["id"]
    _json(client, "GET", f"/api/content/{private['id']}", student_auth, expected=403)
    revision = _json(client, "POST", f"{plan_path}/copy", admin, {"reason": "revision"})
    copied = _json(client, "GET", f"/api/study-plans/{revision['id']}/tree", admin)
    assert copied["creator_id"] == public_source["creator_id"]
    assert copied["id"] != plan["id"] and copied["contents"][0]["id"] != shared["id"]
