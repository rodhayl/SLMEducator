"""Synthetic compatibility and author-asset round-trip, with no provider calls."""
from types import SimpleNamespace

import pytest

from tests.integration.test_trustworthy_scoring_sessions import world as scoring_world, create_quiz, attempt
from src.core.models import Assessment, QuestionResponse
from src.core.services.generation_workflow import _draft_assessment

world = scoring_world


@pytest.mark.parametrize("options,key,answer,supported,score", [
    ({"choices": ["3", "4"]}, "4", "4", True, 10),
    ({"choices": ["3", "4"]}, "B", "4", False, 0),
    ({"A": "three", "B": "four"}, "four", "four", True, 10),
    ({"A": "three", "B": "four"}, "B", "four", False, 0),
    ({"choices": {"A": "three", "B": "four"}}, "B", "B", True, 10),
])
def test_legacy_and_canonical_choice_values_keep_actual_grading_semantics(
    world, options, key, answer, supported, score,
):
    """Do not reinterpret a historical letter as an array index or prose label."""
    quiz_id, questions = create_quiz(world, questions=[{
        "question_text": "Synthetic choice", "question_type": "multiple_choice",
        "points": 10, "options": options, "correct_answer": key,
    }])
    learner = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert learner["questions"][0]["options_supported"] is supported
    assert learner["questions"][0]["correct_answer"] is None
    assert learner["questions"][0]["content_metadata"] is None
    assert learner["questions"][0]["rubrics"] == []
    # Characterize the existing backend comparison without changing its meaning.
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": answer}])
    assert result["score"] == score
    response = world.db.query(QuestionResponse).filter_by(submission_id=result["id"]).one()
    assert response.get_decrypted_response() == answer
    assert response.question.get_decrypted_correct_answer() == key


def generated_assessment(world):
    """Exercise the real generator persistence boundary using fixed local material."""
    created = _draft_assessment(world.db, world.owner, SimpleNamespace(
        topic_name="Synthetic generated reasoning", study_plan_id=None,
    ), {"title": "Generated assessment", "questions": [{
        "question_text": "Explain your evidence", "question_type": "short_answer", "points": 10,
        "correct_answer": "Private answer", "explanation": "Private explanation", "hints": ["Private hint"],
        "rubric": {"name": "Evidence rubric", "criteria": [
            {"name": "Reasoning", "description": "Private grading guidance", "max_points": 6},
            {"name": "Evidence", "description": "Cite the source", "max_points": 4},
        ]},
    }]})
    world.db.commit()
    world.db.refresh(created)
    created.questions[0].content_metadata = {**created.questions[0].content_metadata,
        "unknown_future_asset": {"version": 2, "values": [0, False, None, "untouched"]}}
    world.db.commit()
    return created.id


def author_payload(detail):
    """Mirror the client allowlist while retaining opaque metadata in its own field."""
    return {"title": detail["title"] + " edited", "description": detail["description"],
        "questions": [{key: question[key] for key in (
            "question_text", "question_type", "points", "options", "correct_answer", "content_metadata", "rubrics"
        )} for question in detail["questions"]], "rubric": detail["rubric"]}


def assert_assets(detail, metadata, rubrics):
    assert detail["questions"][0]["content_metadata"] == metadata
    assert detail["questions"][0]["rubrics"] == rubrics
    assert detail["questions"][0]["correct_answer"] == "Private answer"
    assert detail["rubric"] is None


def test_generated_question_assets_survive_read_edit_copy_and_remain_private(world):
    quiz_id = generated_assessment(world)
    original = world.client.get(f"/api/assessments/{quiz_id}").json()
    question = original["questions"][0]
    metadata, rubrics = question["content_metadata"], question["rubrics"]
    assert rubrics[0]["criteria"][0]["max_points"] == 6
    assert original["rubric"] is None  # Never mislabel a per-question rubric as global.

    saved = world.client.put(f"/api/assessments/{quiz_id}", json=author_payload(original))
    assert saved.status_code == 200, saved.text
    edited = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert_assets(edited, metadata, rubrics)

    copied = world.client.post("/api/assessments/", json=author_payload(edited))
    assert copied.status_code == 200, copied.text
    new_id = copied.json()["id"]
    assert new_id != quiz_id
    assert_assets(world.client.get(f"/api/assessments/{new_id}").json(), metadata, rubrics)
    for assessment_id in (quiz_id, new_id):
        assert world.client.post(f"/api/assessments/{assessment_id}/publish").status_code == 200
    world.user = world.learner
    for assessment_id in (quiz_id, new_id):
        learner = world.client.get(f"/api/assessments/{assessment_id}").json()
        assert learner["rubric"] is None
        assert learner["questions"][0]["rubrics"] == []
        assert learner["questions"][0]["content_metadata"] is None
        assert learner["questions"][0]["correct_answer"] is None
        assert "Private" not in str(learner)


def test_old_client_cannot_silently_replace_rich_questions_without_assets(world):
    quiz_id = generated_assessment(world)
    before = world.client.get(f"/api/assessments/{quiz_id}").json()
    rejected = world.client.put(f"/api/assessments/{quiz_id}", json={"questions": [{
        "question_text": "Lossy edit", "question_type": "short_answer", "points": 10,
    }]})
    assert rejected.status_code == 409
    assert world.client.get(f"/api/assessments/{quiz_id}").json() == before
    assert world.db.get(Assessment, quiz_id).questions[0].rubrics
