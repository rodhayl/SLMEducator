"""One complete synthetic teacher-to-reviewed-feedback API journey."""

from tests.trust.test_resource_contracts import scenario, synthetic_credentials
from src.core.models import StudentStudyPlan


def test_three_lessons_notes_attempt_review_and_portability(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    for action in ("review", "publish"):
        response = client.post(
            f"/api/study-plans/{plan.id}/workflow", json={"action": action}
        )
        assert response.status_code == 200, response.text
    response = client.post(
        f"/api/study-plans/{plan.id}/assign",
        json={"student_ids": [users["learner_a"].id]},
    )
    assert response.status_code == 200
    assessment = client.post(
        "/api/assessments/",
        json={
            "title": "Reviewed fraction explanation",
            "study_plan_id": plan.id,
            "topic_id": lessons[2].id,
            "grading_mode": "manual",
            "questions": [
                {
                    "question_text": "Compare 3/8 and 5/8. Explain.",
                    "question_type": "short_answer",
                    "points": 10,
                    "correct_answer": "5/8: five equal eighths exceed three.",
                }
            ],
            "rubric": {
                "name": "Choice and reason",
                "criteria": [
                    {"name": "Choice", "max_points": 4},
                    {"name": "Equal parts reasoning", "max_points": 6},
                ],
            },
        },
    )
    assert assessment.status_code == 200, assessment.text
    assessment_id = assessment.json()["id"]
    assert client.post(f"/api/assessments/{assessment_id}/publish").status_code == 200
    selected[0] = users["learner_a"]
    for lesson in lessons:
        session = client.post(
            "/api/learning/start", json={"content_id": lesson.id}
        ).json()
        notes = f"My synthetic note for {lesson.title}"
        assert (
            client.patch(
                f'/api/learning/{session["id"]}/notes', json={"notes": notes}
            ).status_code
            == 200
        )
        resumed = client.post(
            "/api/learning/start", json={"content_id": lesson.id}
        ).json()
        assert resumed["id"] == session["id"] and resumed["notes"] == notes
        assert (
            client.post(
                f'/api/learning/{session["id"]}/end',
                json={"notes": notes, "difficulty_rating": 4},
            ).status_code
            == 200
        )
        progress = client.post(
            f"/api/study-plans/{plan.id}/progress",
            json={"completed_content_id": lesson.id},
        )
        assert progress.status_code == 200, progress.text
    assert (
        client.get(f"/api/study-plans/{plan.id}/my-progress").json()[
            "completion_percentage"
        ]
        == 100
    )
    detail = client.get(f"/api/assessments/{assessment_id}").json()
    assert detail["questions"][0]["correct_answer"] is None
    attempt = client.post(f"/api/assessments/{assessment_id}/start").json()
    payload = {
        "submission_id": attempt["id"],
        "answers": [
            {
                "question_id": detail["questions"][0]["id"],
                "response_text": "5/8 because both count equal eighths and five exceeds three.",
            }
        ],
    }
    submitted = client.post(f"/api/assessments/{assessment_id}/submit", json=payload)
    assert submitted.status_code == 200, submitted.text
    submission = submitted.json()
    assert submission["needs_review"] and submission["score"] is None
    assert (
        client.post(f"/api/assessments/{assessment_id}/submit", json=payload).json()[
            "id"
        ]
        == submission["id"]
    )
    selected[0] = users["teacher_b"]
    assert (
        client.post(
            f'/api/assessments/submissions/{submission["id"]}/grade', json={"score": 10}
        ).status_code
        == 403
    )
    selected[0] = users["teacher_a"]
    assert (
        client.post(
            f'/api/assessments/submissions/{submission["id"]}/grade',
            json={
                "score": 10,
                "feedback": "Correct choice and clear equal-parts reasoning.",
            },
        ).status_code
        == 200
    )
    selected[0] = users["learner_a"]
    feedback = client.get(f'/api/assessments/submissions/{submission["id"]}').json()
    assert feedback["status"] == "graded" and feedback["score"] == 10
    assert "equal-parts" in feedback["feedback"]
    evidence = client.get("/api/mastery/evidence").json()["items"]
    assessed = next(item for item in evidence if item["content_id"] == lessons[2].id)
    assert assessed["assessment_percent"] == 100 and assessed["self_confidence"] == 4
    handout = client.get(f"/api/portability/plans/{plan.id}/export?audience=learner")
    assert (
        handout.status_code == 200
        and "five equal eighths exceed three" not in handout.text
    )
    selected[0] = users["teacher_a"]
    exported = client.get(f"/api/portability/plans/{plan.id}/export?audience=teacher")
    assert exported.status_code == 200
    selected[0] = users["teacher_b"]
    preview = client.post(
        "/api/portability/import/preview", json={"package": exported.json()}
    )
    assert preview.status_code == 200
    imported = client.post(
        "/api/portability/import", json={"package": exported.json(), "confirm": True}
    )
    assert imported.status_code == 200, imported.text
    assert (
        imported.json()["status"] == "draft"
        and imported.json()["study_plan_id"] != plan.id
    )
