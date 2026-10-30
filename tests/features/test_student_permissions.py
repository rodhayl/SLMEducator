from datetime import datetime


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_student_cannot_create_content(client, student_token):
    resp = client.post(
        "/api/content",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={"title": "Nope", "content_type": "lesson", "content_data": {"body": "x"}},
    )
    assert resp.status_code == 403, resp.text


def test_student_can_create_personal_qa_and_only_they_can_see_it_by_default(
    client, student_token
):
    create_resp = client.post(
        "/api/content",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={
            "title": "Question: limits",
            "content_type": "qa",
            "content_data": {"question": "What is a limit?", "notes": "personal"},
            "shared_with_teacher": False,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created_id = create_resp.json()["id"]

    # Owner can view
    get_resp = client.get(
        f"/api/content/{created_id}", headers=_auth_headers(student_token)
    )
    assert get_resp.status_code == 200, get_resp.text


def test_student_cannot_batch_create_content(client, student_token):
    resp = client.post(
        "/api/content/batch",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={
            "items": [
                {"title": "x", "content_type": "lesson", "content_data": {"body": "x"}}
            ]
        },
    )
    assert resp.status_code == 403, resp.text


def test_student_cannot_create_assessment(client, student_token):
    resp = client.post(
        "/api/assessments/",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={"title": "Nope", "description": "x", "questions": []},
    )
    assert resp.status_code == 403, resp.text


def test_student_cannot_create_study_plan(client, student_token):
    resp = client.post(
        "/api/study-plans/",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={"title": "Nope", "description": "x", "is_public": False, "phases": []},
    )
    assert resp.status_code == 403, resp.text


def test_dashboard_activity_shows_percent_when_total_points_present(
    client, db_service, test_teacher, test_student, student_token
):
    from core.models import (
        Assessment,
        AssessmentSubmission,
        SubmissionStatus,
        GradingMode,
    )

    assessment = Assessment(
        title="Percent Test",
        description="",
        total_points=10,
        is_published=True,
        created_by_id=test_teacher.id,
        grading_mode=GradingMode.AI_ASSISTED,
    )
    db_service.session.add(assessment)
    db_service.session.commit()
    db_service.session.refresh(assessment)

    sub = AssessmentSubmission(
        assessment_id=assessment.id,
        student_id=test_student.id,
        status=SubmissionStatus.SUBMITTED,
        score=10,
        total_points=10,
        submitted_at=datetime.now(),
    )
    db_service.session.add(sub)
    db_service.session.commit()

    resp = client.get("/api/dashboard/activity", headers=_auth_headers(student_token))
    assert resp.status_code == 200, resp.text
    activities = resp.json()
    assert any(
        "Scored 10/10 (100%)" in a.get("text", "") for a in activities
    ), activities


def test_teacher_can_see_student_shared_qa_when_student_assigned_to_teachers_plan(
    client, db_service, test_teacher, test_student, teacher_token, student_token
):
    from core.models import StudyPlan

    plan = StudyPlan(
        title="Teacher Plan",
        description="",
        creator_id=test_teacher.id,
        is_public=False,
        phases=[],
    )
    db_service.session.add(plan)
    db_service.session.commit()
    db_service.session.refresh(plan)

    assign_resp = client.post(
        f"/api/study-plans/{plan.id}/assign",
        headers={**_auth_headers(teacher_token), "Content-Type": "application/json"},
        json={"student_ids": [test_student.id]},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    create_resp = client.post(
        "/api/content",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={
            "title": "Shared question",
            "content_type": "qa",
            "content_data": {"question": "Why?", "notes": "shared"},
            "shared_with_teacher": True,
            "study_plan_id": plan.id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text

    list_resp = client.get("/api/content", headers=_auth_headers(teacher_token))
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()
    shared = next((i for i in items if i.get("title") == "Shared question"), None)
    assert shared is not None, items
    assert shared.get("creator_id") == test_student.id
    assert shared.get("creator_username") == test_student.username


def test_student_cannot_self_assign_via_progress_endpoints(
    client, db_service, test_teacher, test_student, student_token
):
    from core.models import StudyPlan, Content, ContentType, StudyPlanContent

    plan = StudyPlan(
        title="Private Teacher Plan",
        description="",
        creator_id=test_teacher.id,
        is_public=False,
        phases=[],
    )
    db_service.session.add(plan)
    db_service.session.commit()
    db_service.session.refresh(plan)

    content = Content(
        title="Topic 1",
        content_type=ContentType.LESSON,
        difficulty=1,
        creator_id=test_teacher.id,
        created_at=datetime.now(),
    )
    db_service.session.add(content)
    db_service.session.commit()
    db_service.session.refresh(content)

    db_service.session.add(
        StudyPlanContent(
            study_plan_id=plan.id, content_id=content.id, phase_index=0, order_index=0
        )
    )
    db_service.session.commit()

    # Not assigned, not public => forbidden
    resp = client.get(
        f"/api/study-plans/{plan.id}/my-progress", headers=_auth_headers(student_token)
    )
    assert resp.status_code == 403, resp.text

    resp = client.post(
        f"/api/study-plans/{plan.id}/progress",
        headers={**_auth_headers(student_token), "Content-Type": "application/json"},
        json={"completed_content_id": content.id},
    )
    assert resp.status_code == 403, resp.text
