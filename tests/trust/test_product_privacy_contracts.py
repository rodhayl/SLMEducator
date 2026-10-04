"""Correct-behavior regressions converted from the independent product audit."""

import json
import pytest

from src.core.models import (
    Assessment,
    Content,
    ContentType,
    Question,
    QuestionType,
    StudyPlan,
    StudyPlanContent,
    StudentStudyPlan,
    User,
    UserRole,
)
from src.core.services.course_workflow import course_snapshot
from src.core.services.portability_service import (
    export_course,
    import_course,
    preview_package,
    validate_package,
)
from tests.integration.test_portability_recovery import course
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def test_shared_annotation_reaches_only_owner_enrolled_teacher_and_admin(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    plan.is_public = True  # Every actor can read the lesson; audience still differs.
    admin = User(
        username="audience_admin",
        email="audience@example.invalid",
        first_name="Synthetic",
        last_name="Admin",
        password_hash="unused",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    selected[0] = users["learner_a"]
    for text, shared in (("private-marker", False), ("teacher-marker", True)):
        response = client.post(
            "/api/annotations/",
            json={
                "content_id": lessons[0].id,
                "annotation_text": text,
                "is_public": shared,
            },
        )
        assert response.status_code == 200
    for user, expected in (
        (users["learner_a"], {"private-marker", "teacher-marker"}),
        (users["teacher_a"], {"teacher-marker"}),
        (admin, {"teacher-marker"}),
        (users["learner_b"], set()),
        (users["teacher_b"], set()),
    ):
        selected[0] = user
        response = client.get("/api/annotations/", params={"content_id": lessons[0].id})
        assert response.status_code == 200
        assert {item["annotation_text"] for item in response.json()} == expected


def test_inline_assessment_import_is_rejected_before_writes_and_legacy_read_is_safe(
    scenario,
):
    client, db, users, selected, plan, lessons, _ = scenario
    payload = {
        "questions": [
            {"question": "Two plus two?", "correct_answer": "HIDDEN_EXAM_KEY"}
        ],
        "rubric": {"name": "HIDDEN_RUBRIC"},
    }
    package = {
        "format": "slmeducator-course",
        "version": 1,
        "audience": "teacher",
        "exported_at": "2026-10-04T00:00:00Z",
        "study_plan": {"title": "Unsafe inline"},
        "contents": [
            {
                "source_id": 999,
                "title": "Exam",
                "kind": "assessment",
                "content_data": payload,
                "links": [{"phase_index": 0, "order_index": 0}],
            }
        ],
    }
    selected[0] = users["teacher_a"]
    before = db.query(StudyPlan).count(), db.query(Content).count()
    for route, body in (
        ("preview", {"package": package}),
        ("", {"package": package, "confirm": True}),
    ):
        response = client.post(
            "/api/portability/import" + ("/" + route if route else ""), json=body
        )
        assert response.status_code == 422, response.text
    assert before == (db.query(StudyPlan).count(), db.query(Content).count())
    # Historical invalid rows remain recoverable by their author, but never leak.
    legacy = Content(
        title="Historical exam",
        creator_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        content_type=ContentType.ASSESSMENT,
    )
    legacy.set_encrypted_content_data(payload)
    db.add(legacy)
    db.flush()
    db.add(
        StudyPlanContent(
            study_plan_id=plan.id, content_id=legacy.id, phase_index=3, order_index=0
        )
    )
    db.commit()
    selected[0] = users["learner_a"]
    response = client.get(f"/api/content/{legacy.id}")
    assert response.status_code == 200
    assert (
        "HIDDEN_EXAM_KEY" not in response.text and "HIDDEN_RUBRIC" not in response.text
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_phase",
        "malformed_reference",
        "invalid_sections",
        "duplicate_position",
        "phase_out_of_range",
    ],
)
def test_package_graph_errors_are_422_and_atomic(course, mutation):
    package = export_course(course.db, course.author, course.plan, "teacher")
    if mutation == "unknown_phase":
        package["study_plan"]["phases"] = [{"content_ids": [999999]}]
    elif mutation == "malformed_reference":
        package["contents"][0]["content_data"]["content_id"] = []
    elif mutation == "invalid_sections":
        package["contents"][0]["content_data"] = {"sections": 1}
    elif mutation == "duplicate_position":
        for item in package["contents"]:
            item["links"] = [{"phase_index": 0, "order_index": 0}]
    else:
        package["contents"][0]["links"][0]["phase_index"] = 2000
    before = course.db.query(StudyPlan).count(), course.db.query(Content).count()
    response = course.client.post(
        "/api/portability/import/preview", json={"package": package}
    )
    assert response.status_code == 422, response.text
    with pytest.raises(ValueError):
        import_course(course.db, course.recipient, package)
    assert before == (
        course.db.query(StudyPlan).count(),
        course.db.query(Content).count(),
    )


def test_learner_export_omits_draft_pointer_and_preserves_vocabulary(course):
    course.lesson.set_encrypted_content_data(
        {
            "sections": [{"title": "Lesson", "content": "Text"}],
            "vocabulary": [{"term": "numerator", "definition": "top value"}],
        }
    )
    course.assessment.is_published = False
    pointer = Content(
        title="Draft exam",
        content_type=ContentType.ASSESSMENT,
        creator_id=course.author.id,
        study_plan_id=course.plan.id,
    )
    pointer.set_encrypted_content_data({"assessment_id": course.assessment.id})
    course.db.add(pointer)
    course.db.flush()
    course.db.add(
        StudyPlanContent(
            study_plan_id=course.plan.id,
            content_id=pointer.id,
            phase_index=1,
            order_index=1,
        )
    )
    course.db.commit()
    package = export_course(course.db, course.reader, course.plan, "learner")
    assert package["assessments"] == []
    assert all(item["source_id"] != pointer.id for item in package["contents"])
    assert (
        package["contents"][0]["content_data"]["vocabulary"][0]["term"] == "numerator"
    )
    assert preview_package(package)["counts"]["contents"] == 2


def test_course_publication_requires_owned_published_executable_assessment(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    draft = Assessment(
        title="Draft exam",
        created_by_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        is_published=False,
    )
    db.add(draft)
    db.flush()
    db.add(
        Question(
            assessment_id=draft.id,
            question_text="Explain",
            question_type=QuestionType.SHORT_ANSWER,
            points=10,
        )
    )
    pointer = Content(
        title="Exam",
        creator_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        content_type=ContentType.ASSESSMENT,
    )
    pointer.set_encrypted_content_data({"assessment_id": draft.id})
    db.add(pointer)
    db.flush()
    db.add(
        StudyPlanContent(
            study_plan_id=plan.id, content_id=pointer.id, phase_index=3, order_index=0
        )
    )
    db.commit()
    selected[0] = users["teacher_a"]
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
        ).status_code
        == 409
    )
    assert client.post(f"/api/assessments/{draft.id}/publish").status_code == 200
    # Publishing changes the reviewed definition; the author must review again.
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
        ).status_code
        == 409
    )
    for action in ("review", "publish"):
        response = client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": action}
        )
        assert response.status_code == 200, response.text
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/assign",
            json={"student_ids": [users["learner_a"].id]},
        ).status_code
        == 200
    )


def test_review_digest_tracks_assessment_definition_without_disclosing_key(course):
    before = course_snapshot(course.db, course.plan)
    course.assessment.questions[0].question_text = "Changed assessment question"
    course.db.flush()
    after = course_snapshot(course.db, course.plan)
    assert after != before
    assert "SYNTHETIC-ASSESSMENT-KEY" not in json.dumps(after)
