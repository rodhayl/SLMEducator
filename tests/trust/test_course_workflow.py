"""Teacher-reviewed three-lesson course contract; all people/data are synthetic."""

from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def test_review_publish_assign_freezes_three_lesson_version(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    selected[0] = users["teacher_a"]
    # Remove the fixture assignment: exercise the complete preparation path.
    from src.core.models import StudentStudyPlan

    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    response = client.post(
        f"/api/study-plans/{plan.id}/assign",
        json={"student_ids": [users["learner_a"].id]},
    )
    assert response.status_code == 409
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
        ).status_code
        == 409
    )
    reviewed = client.post(
        f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
    )
    assert reviewed.status_code == 200, reviewed.text
    assert len(reviewed.json()["snapshot"]) == 3
    published = client.post(
        f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
    )
    assert published.json()["version"] == 1
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
        ).json()["version"]
        == 1
    )
    response = client.post(
        f"/api/study-plans/{plan.id}/assign",
        json={"student_ids": [users["learner_a"].id]},
    )
    assert response.status_code == 200, response.text
    assert (
        client.put(
            f"/api/content/{lessons[0].id}", json={"title": "Changed after assignment"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
        ).status_code
        == 409
    )
    assert client.get(f"/api/study-plans/{plan.id}/workflow").json()["read_only"]
    selected[0] = users["learner_a"]
    assert client.get(f"/api/content/{lessons[0].id}").json()["title"] == "Equal parts"
    selected[0] = users["teacher_b"]
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
        ).status_code
        == 403
    )


def test_edit_invalidates_review_and_order_is_keyboard_safe(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    from src.core.models import StudentStudyPlan

    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "review"}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/content/{lessons[0].id}",
            json={"content_data": {"content": "A revised lesson"}},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": "publish"}
        ).status_code
        == 409
    )
    items = [
        {"content_id": lesson.id, "phase_index": 0, "order_index": i}
        for i, lesson in enumerate(reversed(lessons))
    ]
    assert (
        client.put(f"/api/study-plans/{plan.id}/order", json=items).status_code == 200
    )
    assert (
        client.put(f"/api/study-plans/{plan.id}/order", json=[items[0]] * 3).status_code
        == 409
    )
    assert [
        item["id"]
        for item in client.get(f"/api/study-plans/{plan.id}/tree").json()["contents"]
    ] == [x.id for x in reversed(lessons)]
