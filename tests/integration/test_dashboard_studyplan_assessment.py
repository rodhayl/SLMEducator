import os
import sys
import uuid
from datetime import datetime, UTC

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.models import AssessmentSubmission, SubmissionStatus
from src.api.dependencies import get_db_service

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

client = TestClient(app)


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register_user(username: str, role: str):
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "User",
        "role": role,
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _login_user(username: str, password: str = "Password123!") -> str:
    resp = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_submission(
    assessment_id: int, student_id: int, status: SubmissionStatus
) -> int:
    db = get_db_service()
    session = db.get_session()
    try:
        submission = AssessmentSubmission(
            assessment_id=assessment_id,
            student_id=student_id,
            status=status,
            submitted_at=datetime.now(UTC),
            total_points=10,
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)
        return submission.id
    finally:
        session.close()


def test_dashboard_stats_include_total_content():
    username = _unique_username("teacher")
    _register_user(username, "teacher")
    token = _login_user(username)

    for idx in range(2):
        resp = client.post(
            "/api/content",
            json={
                "title": f"Content {idx}",
                "content_type": "lesson",
                "content_data": {"body": "Sample content"},
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

    stats_resp = client.get("/api/dashboard/stats", headers=_auth_headers(token))
    assert stats_resp.status_code == 200, stats_resp.text
    stats = stats_resp.json()
    assert stats.get("total_content") == 2


def test_student_study_plan_listing_includes_assignments():
    teacher_username = _unique_username("teacher")
    student_username = _unique_username("student")
    _register_user(teacher_username, "teacher")
    student = _register_user(student_username, "student")

    teacher_token = _login_user(teacher_username)
    student_token = _login_user(student_username)

    content_resp = client.post(
        "/api/content",
        json={
            "title": "Plan Lesson",
            "content_type": "lesson",
            "content_data": {"body": "Plan content"},
        },
        headers=_auth_headers(teacher_token),
    )
    assert content_resp.status_code == 200, content_resp.text
    content_id = content_resp.json()["id"]

    plan_resp = client.post(
        "/api/study-plans",
        json={
            "title": "Assigned Plan",
            "description": "Study plan for assignments",
            "phases": [{"name": "Phase 1", "content_ids": [content_id]}],
        },
        headers=_auth_headers(teacher_token),
    )
    assert plan_resp.status_code == 200, plan_resp.text
    plan_id = plan_resp.json()["id"]

    assign_resp = client.post(
        f"/api/study-plans/{plan_id}/assign",
        json={"student_ids": [student["id"]]},
        headers=_auth_headers(teacher_token),
    )
    assert assign_resp.status_code == 200, assign_resp.text

    progress_resp = client.post(
        f"/api/study-plans/{plan_id}/progress",
        json={"completed_content_id": content_id},
        headers=_auth_headers(student_token),
    )
    assert progress_resp.status_code == 200, progress_resp.text

    list_resp = client.get("/api/study-plans/", headers=_auth_headers(student_token))
    assert list_resp.status_code == 200, list_resp.text
    plan_ids = {plan["id"] for plan in list_resp.json()}
    assert plan_id in plan_ids


def test_assessment_create_with_rubric():
    username = _unique_username("teacher")
    _register_user(username, "teacher")
    token = _login_user(username)

    payload = {
        "title": "Rubric Assessment",
        "description": "Assessment with rubric criteria",
        "passing_score": 70,
        "grading_mode": "manual",
        "questions": [
            {
                "question_text": "What is 2+2?",
                "question_type": "multiple_choice",
                "points": 5,
                "correct_answer": "4",
                "options": {"choices": ["3", "4"]},
            }
        ],
        "rubric": {
            "name": "Clarity Rubric",
            "description": "Basic rubric",
            "criteria": [
                {"name": "Accuracy", "description": "Correct answer", "max_points": 5}
            ],
        },
    }

    resp = client.post("/api/assessments/", json=payload, headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["question_count"] == 1


def test_list_submissions_accepts_multiple_status_filters():
    teacher_username = _unique_username("teacher")
    student_username = _unique_username("student")
    _register_user(teacher_username, "teacher")
    student = _register_user(student_username, "student")

    teacher_token = _login_user(teacher_username)

    assessment_resp = client.post(
        "/api/assessments/",
        json={
            "title": "Status Assessment",
            "description": "Status filter coverage",
            "passing_score": 70,
            "grading_mode": "manual",
            "questions": [
                {
                    "question_text": "Explain gravity.",
                    "question_type": "short_answer",
                    "points": 10,
                }
            ],
        },
        headers=_auth_headers(teacher_token),
    )
    assert assessment_resp.status_code == 200, assessment_resp.text
    assessment_id = assessment_resp.json()["id"]

    _create_submission(assessment_id, student["id"], SubmissionStatus.SUBMITTED)
    _create_submission(assessment_id, student["id"], SubmissionStatus.AI_GRADED)

    list_resp = client.get(
        "/api/assessments/submissions?status=submitted&status=ai_graded",
        headers=_auth_headers(teacher_token),
    )
    assert list_resp.status_code == 200, list_resp.text
    statuses = {item["status"] for item in list_resp.json()}
    assert "submitted" in statuses
    assert "ai_graded" in statuses
