"""Personal learner Q&A keeps its lifecycle separate from assigned material."""

from typing import Any

import pytest

from src.core.models import Content, ContentType, StudyPlanContent, StudentStudyPlan
from src.core.services.course_workflow import assert_content_editable, invalidate_reviews
from tests.trust import test_resource_contracts as fixtures

scenario = fixtures.scenario
synthetic_credentials = fixtures.synthetic_credentials


@pytest.fixture
def published_course(scenario: tuple[Any, ...]) -> tuple[Any, ...]:
    """Publish and assign a disposable course through the ordinary teacher API."""
    client, db, users, selected, plan, _, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    for action in ("review", "publish"):
        response = client.post(
            f"/api/study-plans/{plan.id}/workflow",
            json={"action": action, "is_public": True},
        )
        assert response.status_code == 200, response.text
    response = client.post(
        f"/api/study-plans/{plan.id}/assign",
        json={"student_ids": [users["learner_a"].id]},
    )
    assert response.status_code == 200, response.text
    selected[0] = users["learner_a"]
    return scenario


def create_question(world: tuple[Any, ...], context: str, shared: bool = False) -> int:
    """Save owned Q&A with optional course context and teacher sharing."""
    client, db, _, _, plan, _, _ = world
    response = client.post(
        "/api/content/",
        json={
            "title": "Synthetic learner question",
            "content_type": "qa",
            "content_data": {"question": "How do equal parts work?"},
            "study_plan_id": None if context == "standalone" else plan.id,
            "shared_with_teacher": shared,
        },
    )
    assert response.status_code == 200, response.text
    content_id = response.json()["id"]
    assert response.json()["is_personal"] is True
    assert db.query(StudyPlanContent).filter_by(content_id=content_id).count() == 0
    if context == "formerly_assigned":
        db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
        db.commit()
    return content_id


def course_state(world: tuple[Any, ...]) -> tuple[Any, ...]:
    """Capture publication, canonical items and assigned snapshots unchanged."""
    _, db, _, _, plan, _, _ = world
    db.refresh(plan)
    links = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id)
    assignments = db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id)
    return (
        plan.content_metadata,
        plan.is_public,
        [(row.id, row.content_id, row.phase_index, row.order_index) for row in links],
        [(row.student_id, row.progress) for row in assignments],
    )


@pytest.mark.parametrize("context", ["assigned", "formerly_assigned", "standalone"])
@pytest.mark.parametrize("operation", ["edit", "share", "unshare", "delete"])
def test_owner_qa_lifecycle_preserves_course(
    published_course: tuple[Any, ...], context: str, operation: str
) -> None:
    """Edit/sharing/deletion changes personal work without changing its course."""
    client, db, users, selected, _, _, _ = published_course
    content_id = create_question(published_course, context, shared=operation == "unshare")
    before = course_state(published_course)
    path = f"/api/content/{content_id}"
    if operation == "delete":
        response = client.delete(path)
    else:
        changes = (
            {"title": "Updated question", "content_data": {"question": "Why equal parts?", "answer": "They use the same unit."}}
            if operation == "edit"
            else {"shared_with_teacher": operation == "share"}
        )
        response = client.put(path, json=changes)
    assert response.status_code == 200, response.text
    assert course_state(published_course) == before
    if operation == "delete":
        assert db.get(Content, content_id) is None
        assert client.get(path).status_code == 404
        return
    saved = client.get(path)
    assert saved.status_code == 200, saved.text
    assert saved.json()["can_edit"] is True
    assert saved.json()["is_personal"] is True
    if operation == "edit":
        assert saved.json()["title"] == changes["title"]
        assert saved.json()["content_data"] == {
            **changes["content_data"], "schema_version": 1, "kind": "qa"
        }
    else:
        assert saved.json()["shared_with_teacher"] is (operation == "share")
        selected[0] = users["teacher_a"]
        expected = 200 if operation == "share" else 403
        assert client.get(path).status_code == expected
        visible = {row["id"] for row in client.get("/api/content/?content_type=qa").json()}
        assert (content_id in visible) is (operation == "share")


@pytest.mark.parametrize("context", ["assigned", "formerly_assigned", "standalone"])
def test_owner_qa_editability_receipts(
    published_course: tuple[Any, ...], context: str
) -> None:
    """Detail and list correctly report an owner's editable personal question."""
    client, _, _, _, _, _, _ = published_course
    content_id = create_question(published_course, context)
    assert client.get(f"/api/content/{content_id}").json()["can_edit"] is True
    rows = client.get("/api/content/?content_type=qa").json()
    assert next(row for row in rows if row["id"] == content_id)["can_edit"] is True


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("viewer", ["teacher_a", "teacher_b", "learner_b"])
def test_course_context_preserves_qa_owner_and_sharing_boundaries(
    published_course: tuple[Any, ...], shared: bool, viewer: str
) -> None:
    """Only the owner can change Q&A; sharing grants their teacher read access."""
    client, db, users, selected, _, _, _ = published_course
    content_id = create_question(published_course, "assigned", shared=shared)
    before = course_state(published_course)
    record = db.get(Content, content_id)
    original = record.title, record.content_data, record.shared_with_teacher
    selected[0] = users[viewer]
    path = f"/api/content/{content_id}"
    readable = shared and viewer == "teacher_a"
    result = client.get(path)
    assert result.status_code == (200 if readable else 403), result.text
    if readable:
        assert result.json()["can_edit"] is False
    rows = client.get("/api/content/?content_type=qa").json()
    assert (content_id in {row["id"] for row in rows}) is readable
    assert client.put(path, json={"title": "Other user's edit"}).status_code == 403
    assert client.put(path, json={"shared_with_teacher": False}).status_code == 403
    assert client.delete(path).status_code == 403
    db.refresh(record)
    assert (record.title, record.content_data, record.shared_with_teacher) == original
    assert course_state(published_course) == before


@pytest.mark.parametrize("personal", [False, True])
@pytest.mark.parametrize("canonical", [False, True])
def test_material_dependencies_keep_assignment_and_review_guards(
    published_course: tuple[Any, ...], personal: bool, canonical: bool
) -> None:
    """Canonical links win even when an existing item is marked personal."""
    _, db, users, _, plan, _, _ = published_course
    record = Content(
        title="Synthetic stored Q&A",
        content_type=ContentType.QA,
        creator_id=users["teacher_a"].id,
        study_plan_id=plan.id,
        is_personal=personal,
    )
    record.set_encrypted_content_data({"question": "Compare equal parts."})
    db.add(record)
    db.flush()
    if canonical:
        db.add(StudyPlanContent(
            study_plan_id=plan.id, content_id=record.id, phase_index=0, order_index=1
        ))
    db.commit()
    material = canonical or not personal
    if material:
        with pytest.raises(ValueError, match="belongs to an assigned course"):
            assert_content_editable(db, record)
    else:
        assert_content_editable(db, record)

    # Once unassigned, changes to real material still invalidate publication.
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    before = course_state(published_course)
    assert_content_editable(db, record)
    invalidate_reviews(db, record)
    db.commit()
    if material:
        db.refresh(plan)
        assert plan.decrypted_metadata["workflow"]["status"] == "draft"
        assert plan.is_public is False
    else:
        assert course_state(published_course) == before
