"""All authoring routes preserve canonical content and bounded course order."""

import pytest

from src.core.models import Content, StudyPlanContent, StudentStudyPlan
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def prepare(scenario):
    """Use the existing isolated two-teacher/two-learner fixture as a draft."""
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    return client, db, plan, lessons


def create(client, plan_id, route, data=None, **extra):
    """Submit the same authored item through each public ingress."""
    item = {"title": "New synthetic lesson", "content_type": "lesson"}
    if data is not None:
        item["content_data"] = data
    if route == "single":
        return client.post(
            "/api/content/", json={**item, "study_plan_id": plan_id, **extra}
        )
    if route == "topic":
        return client.post(
            f"/api/study-plans/{plan_id}/topics", json={**item, **extra}
        )
    return client.post(
        "/api/content/batch",
        json={"items": [item], "study_plan_id": plan_id, **extra},
    )


@pytest.mark.parametrize("route", ["single", "topic", "batch"])
@pytest.mark.parametrize("data", [None, {}, {"sections": []}, {"sections": 1}])
def test_empty_or_malformed_content_is_rejected_before_writes(scenario, route, data):
    client, db, plan, _ = prepare(scenario)
    before = db.query(Content).count(), db.query(StudyPlanContent).count()
    response = create(client, plan.id, route, data)
    assert response.status_code in {400, 422}, response.text
    assert before == (db.query(Content).count(), db.query(StudyPlanContent).count())


@pytest.mark.parametrize("route", ["topic", "batch"])
@pytest.mark.parametrize("phase", [-1, 101])
def test_alternate_ingress_rejects_out_of_range_phase(scenario, route, phase):
    client, db, plan, _ = prepare(scenario)
    before = db.query(Content).count()
    response = create(client, plan.id, route, {"content": "Text"}, phase_index=phase)
    assert response.status_code == 422, response.text
    assert db.query(Content).count() == before


@pytest.mark.parametrize("route", ["single", "topic", "batch"])
def test_sparse_course_appends_after_maximum_and_invalidates_review(scenario, route):
    client, db, plan, _ = prepare(scenario)
    links = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id).all()
    for link, position in zip(links, [0, 2, 5]):
        link.phase_index, link.order_index = 0, position
    for action in ("review", "publish"):
        response = client.post(
            f"/api/study-plans/{plan.id}/workflow",
            json={"action": action, "is_public": True},
        )
        assert response.status_code == 200, response.text
    response = create(client, plan.id, route, {"content": "Valid new text"})
    assert response.status_code == 200, response.text
    positions = [
        link.order_index
        for link in db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan.id, phase_index=0)
        .order_by(StudyPlanContent.order_index)
    ]
    assert positions == [0, 2, 5, 6]
    db.refresh(plan)
    assert plan.decrypted_metadata["workflow"]["status"] == "draft"
    assert not plan.is_public
    assert client.post(
        f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
    ).status_code == 200


@pytest.mark.parametrize("route", ["single", "topic", "batch"])
def test_full_course_phase_rejects_append_atomically(scenario, route):
    client, db, plan, _ = prepare(scenario)
    link = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id).first()
    link.phase_index, link.order_index = 0, 1000
    db.commit()
    before = db.query(Content).count(), db.query(StudyPlanContent).count()
    response = create(client, plan.id, route, {"content": "Valid new text"})
    assert response.status_code in {400, 422}, response.text
    assert "phase is full" in response.json()["detail"]
    assert before == (db.query(Content).count(), db.query(StudyPlanContent).count())


def test_batch_validates_all_items_before_persisting_or_changing_review(scenario):
    client, db, plan, _ = prepare(scenario)
    plan.set_encrypted_metadata({"workflow": {"status": "reviewed", "version": 2}})
    db.commit()
    before = db.query(Content).count(), plan.content_metadata
    response = client.post(
        "/api/content/batch",
        json={
            "study_plan_id": plan.id,
            "items": [
                {"title": "Valid", "content_data": {"content": "Synthetic text"}},
                {"title": "Missing content"},
            ],
        },
    )
    assert response.status_code == 422, response.text
    db.refresh(plan)
    assert before == (db.query(Content).count(), plan.content_metadata)


def test_created_course_order_is_relative_to_each_phase(scenario):
    client, db, plan, lessons = prepare(scenario)
    response = client.post(
        "/api/study-plans/",
        json={
            "title": "New course",
            "phases": [
                {"name": str(index), "content_ids": [lesson.id]}
                for index, lesson in enumerate(lessons)
            ],
        },
    )
    assert response.status_code == 200, response.text
    links = db.query(StudyPlanContent).filter_by(study_plan_id=response.json()["id"])
    assert [(link.phase_index, link.order_index) for link in links] == [
        (0, 0), (1, 0), (2, 0)
    ]


def test_content_deletion_invalidates_an_unassigned_published_course(scenario):
    client, db, plan, lessons = prepare(scenario)
    for action in ("review", "publish"):
        assert client.post(
            f"/api/study-plans/{plan.id}/workflow",
            json={"action": action, "is_public": True},
        ).status_code == 200
    response = client.delete(f"/api/content/{lessons[0].id}")
    assert response.status_code == 200, response.text
    db.refresh(plan)
    assert plan.decrypted_metadata["workflow"]["status"] == "draft"
    assert not plan.is_public
