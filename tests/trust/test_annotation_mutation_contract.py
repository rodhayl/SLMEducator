"""Annotation mutation follows the same explicit audience as annotation reads."""

import pytest

from src.core.models import Annotation, User, UserRole
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize(
    "actor", ["learner_a", "learner_b", "teacher_a", "teacher_b", "admin"]
)
def test_annotation_delete_requires_owner_or_explicitly_shared_staff_audience(
    scenario, actor, shared
):
    client, db, users, selected, plan, lessons, _ = scenario
    plan.is_public = True
    admin = User(
        username="annotation_admin",
        email="annotation-admin@example.invalid",
        password_hash="synthetic-unused",
        first_name="Synthetic",
        last_name="Administrator",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    users["admin"] = admin
    selected[0] = users["learner_a"]
    response = client.post(
        "/api/annotations/",
        json={
            "content_id": lessons[0].id,
            "annotation_text": "Synthetic personal annotation",
            "is_public": shared,
        },
    )
    assert response.status_code == 200, response.text
    annotation_id = response.json()["id"]
    selected[0] = users[actor]
    allowed = actor == "learner_a" or (shared and actor in {"teacher_a", "admin"})
    response = client.delete(f"/api/annotations/{annotation_id}")
    assert response.status_code == (200 if allowed else 403), response.text
    assert (db.get(Annotation, annotation_id) is None) is allowed
