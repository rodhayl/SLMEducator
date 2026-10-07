"""Synthetic endpoint regressions for generation, immutable exams and handouts."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from src.api.dependencies import get_ai_service_dependency
from src.api.routes import assessment, generation
from src.core.models import (
    Assessment,
    Content,
    ContentType,
    QuestionResponse,
    StudentStudyPlan,
    StudyPlan,
    StudyPlanContent,
    Submission,
)
from src.core.services.ai_service import AIProvider
from src.core.services.course_workflow import transition
from src.core.services.generation_workflow import _generated_choices
from src.core.services.portability_service import _learner_options
from tests.integration.test_portability_recovery import course as export_course_fixture
from tests.integration.test_trustworthy_scoring_sessions import (
    attempt,
    create_quiz,
)
from tests.integration.test_trustworthy_scoring_sessions import (
    world as scoring_world,
)

world = scoring_world
course = export_course_fixture


def generate_exam(world, options, answer):
    """Exercise auto-save through its real endpoint with a transport-free provider."""
    world.client.app.include_router(generation.router)
    provider = Mock(model="synthetic", provider=AIProvider.OLLAMA)
    provider.generate_assessment_questions.return_value = [{
        "question_text": "Choose four", "question_type": "multiple_choice",
        "points": 10, "options": deepcopy(options), "correct_answer": answer,
    }]
    world.client.app.dependency_overrides[get_ai_service_dependency] = lambda: provider
    response = world.client.post("/api/generate/full-topic-package", json={
        "subject": "Math", "topic_name": "Fresh choices", "grade_level": "Synthetic adult",
        "learning_objectives": [], "include_lesson": False, "include_exercises": False,
        "include_assessment": True, "num_assessment_questions": 1,
        "auto_save": True, "study_plan_id": world.content.study_plan_id,
    })
    assert response.status_code == 200, response.text
    provider.close.assert_called_once()
    return response.json()


@pytest.mark.parametrize("options,answer,canonical", [
    ({"A": "three", "B": "four"}, "B", "B"),
    ({"A": "three", "B": "four"}, " four ", "B"),
    ({"A": "three", "B": "four"}, " b ", "B"),
    ({"choices": {"A": "three", "B": "four"}}, "four", "B"),
    (["three", "four"], "four", "2"),
    (["three", "four"], "2", "2"),
    ({"choices": ["three", "four"]}, "four", "2"),
    ({"a": "a", "b": "b"}, "b", "b"),
    ({"A": "weiß", "B": "weiss"}, "weiss", "B"),
    ({"A": "3", "B": "4"}, 4, "B"),
    ({"A": "3", "B": "4"}, 4.0, "B"),
    ({"A": "false", "B": "true"}, True, "B"),
    ({"choices": {"A": "three", "B": "four"}, "correct_answer": "HIDDEN"}, "B", "B"),
])
def test_generated_choices_save_publish_and_score_canonical_value(world, options, answer, canonical):
    original = deepcopy(options)
    generated = generate_exam(world, options, answer)
    assert generated["success"] is True
    quiz_id = generated["items"][0]["assessment_id"]
    saved = world.db.get(Assessment, quiz_id)
    assert saved.is_published is False  # Provider output still requires teacher publication.
    question = saved.questions[0]
    labels = options.get("choices", options) if isinstance(options, dict) else options
    expected_choices = labels if isinstance(labels, dict) else {
        str(index + 1): label for index, label in enumerate(labels)
    }
    assert question.options == {"choices": expected_choices}
    assert question.get_decrypted_correct_answer() == canonical
    assert options == original
    assert world.client.post(f"/api/assessments/{quiz_id}/publish").status_code == 200
    plan = world.db.get(StudyPlan, world.content.study_plan_id)
    transition(world.db, plan, "review", world.owner.id)
    transition(world.db, plan, "publish", world.owner.id, public=True)
    world.db.commit()
    world.user = world.learner
    response = world.client.get(f"/api/assessments/{quiz_id}")
    assert response.status_code == 200, response.text
    learner = response.json()["questions"][0]
    assert learner["options_supported"] is True
    assert learner["options"] == {"choices": expected_choices}
    assert learner["correct_answer"] is None
    result, _ = attempt(world, quiz_id, [{
        "question_id": question.id, "response_text": canonical,
    }])
    assert result["score"] == 10 and result["status"] == "graded"
    stored = world.db.query(QuestionResponse).filter_by(submission_id=result["id"]).one()
    assert stored.get_decrypted_response() == canonical


@pytest.mark.parametrize("options,answer", [
    ({"A": "three", "B": "four"}, "C"),
    ({"A": "three", "B": "four"}, None),
    ({"A": "same", "B": "same"}, "same"),
    ({"A": "B", "B": "other"}, "B"),
    ({"A": "three", " a ": "four"}, "A"),
    ({"": "three", "B": "four"}, "B"),
    ({"A": "three", "B": " "}, "A"),
    ({"A": {"text": "three", "is_correct": True}, "B": "four"}, "B"),
    ({"A": "three"}, "A"),
    (["2", "four"], "2"),
    (None, "A"),
    ({"ß": "three", "ss": "four"}, "ss"),
    ({"ẞ": "three", "ss": "four"}, "ss"),
    ({"σ": "three", "ς": "four"}, "σ"),
    ({"ı": "three", "i": "four"}, "i"),
    ({"A": "three", "B": "four"}, []),
])
def test_invalid_generated_choices_fail_transactionally_without_inventing_key(world, options, answer):
    before = world.db.query(Content).count(), world.db.query(StudyPlanContent).count()
    result = generate_exam(world, options, answer)
    assert result["success"] is False
    assert result["saved_content_ids"] == [] and result["assessment"] is None
    assert result["items"] == [{
        "key": "assessment", "status": "failed", "error_code": "content_validation",
    }]
    assert world.db.query(Assessment).count() == 0
    assert before == (world.db.query(Content).count(), world.db.query(StudyPlanContent).count())


def test_assigned_published_delete_and_edits_keep_course_pointer_and_definition(world):
    plan_id = world.content.study_plan_id
    quiz_id, _ = create_quiz(world, study_plan_id=plan_id)
    pointer = Content(title="Exam pointer", creator_id=world.owner.id,
                      study_plan_id=plan_id, content_type=ContentType.ASSESSMENT)
    pointer.set_encrypted_content_data({"assessment_id": quiz_id})
    world.db.add(pointer)
    world.db.flush()
    link = StudyPlanContent(study_plan_id=plan_id, content_id=pointer.id, order_index=1)
    world.db.add_all([link, StudentStudyPlan(student_id=world.learner.id, study_plan_id=plan_id)])
    world.db.commit()
    world.user = world.owner
    before = world.client.get(f"/api/assessments/{quiz_id}").json()
    pointer_before = pointer.content_data
    assert world.db.query(Submission).count() == 0
    for method, payload in (("delete", None), ("put", {"title": "Changed"}),
                            ("put", {"is_published": False})):
        response = world.client.request(method, f"/api/assessments/{quiz_id}", json=payload)
        assert response.status_code == 409, response.text
    assert world.client.get(f"/api/assessments/{quiz_id}").json() == before
    world.db.refresh(pointer)
    assert pointer.content_data == pointer_before
    assert pointer.decrypted_content_data == {"assessment_id": quiz_id}
    assert world.db.get(StudyPlanContent, link.id) is not None
    assert world.db.get(Assessment, quiz_id) is not None


def test_unassigned_draft_without_attempts_can_still_be_deleted(world):
    response = world.client.post("/api/assessments/", json={
        "title": "Disposable draft", "study_plan_id": world.content.study_plan_id,
        "questions": [{"question_text": "Explain", "question_type": "short_answer", "points": 10}],
    })
    assert response.status_code == 200, response.text
    quiz_id = response.json()["id"]
    assert world.client.delete(f"/api/assessments/{quiz_id}").status_code == 200
    assert world.db.get(Assessment, quiz_id) is None


def test_existing_attempt_still_prevents_deleting_unassigned_assessment(world):
    quiz_id, _ = create_quiz(world)
    response = world.client.post(f"/api/assessments/{quiz_id}/start")
    assert response.status_code == 200
    world.user = world.owner
    assert world.client.delete(f"/api/assessments/{quiz_id}").status_code == 409
    assert world.db.get(Assessment, quiz_id) is not None
    assert world.db.get(Submission, response.json()["id"]) is not None


@pytest.mark.parametrize("global_rubric", [False, True])
def test_question_rubric_overrides_global_and_unrelated_criteria_never_fall_back(
    world, monkeypatch, global_rubric,
):
    local = {"name": "Algebra only", "criteria": [{"name": "Algebra", "max_points": 10}]}
    common = {"name": "Global reasoning", "criteria": [{"name": "Reasoning", "max_points": 10}]}
    quiz_id, questions = create_quiz(world, questions=[
        {"question_text": "Explain algebra", "question_type": "short_answer", "points": 10, "rubrics": [local]},
        {"question_text": "Explain poetry", "question_type": "short_answer", "points": 10},
    ], **({"rubric": common} if global_rubric else {}))
    provider = Mock()
    provider.grade_answer.return_value = {"points_earned": 8, "feedback": "Synthetic suggestion"}
    monkeypatch.setattr(assessment, "get_ai_service_dependency", lambda user, db: provider)
    result, _ = attempt(world, quiz_id, [
        {"question_id": question["id"], "response_text": "Synthetic response"} for question in questions
    ])
    first, second = [call.kwargs["rubric"] for call in provider.grade_answer.call_args_list]
    assert [item["name"] for item in first["rubrics"]] == ["Algebra only"]
    if global_rubric:
        assert [item["name"] for item in second["rubrics"]] == ["Global reasoning"]
    else:
        assert second is None
    assert result["status"] == "ai_graded" and result["score"] is None and result["needs_review"]
    stored = world.db.query(QuestionResponse).filter_by(submission_id=result["id"]).all()
    assert all(item.score is None and item.ai_suggested_score == 8 for item in stored)


@pytest.mark.parametrize("export_format,media", [
    ("json", "application/json"), ("html", "text/html"), ("markdown", "text/markdown"),
])
def test_learner_exports_preserve_practice_and_exam_choices_without_hidden_metadata(course, export_format, media):
    practice = {"choices": {"P1": "Practice three", "P2": "Practice four"},
                "correct_answer": "HIDDEN-OPTION-KEY", "rubric": "HIDDEN-OPTION-RUBRIC"}
    exam = {"choices": {"A": "Exam three", "B": "Exam four",
                        "correctness": "HIDDEN-CORRECTNESS", "answer_key": "HIDDEN-NESTED-KEY"},
            "correct_answer": "HIDDEN-EXAM-KEY", "grading_metadata": "HIDDEN-GRADING"}
    course.exercise.set_encrypted_content_data({
        "type": "multiple_choice", "question": "Practice choice?", "options": practice,
        "answer": "HIDDEN-PRACTICE-ANSWER", "solution": "HIDDEN-SOLUTION",
    })
    course.assessment.questions[0].options = exam
    course.db.commit()
    course.user = course.reader
    response = course.client.get(
        f"/api/portability/plans/{course.plan.id}/export?audience=learner&format={export_format}"
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(media)
    for label in ("Practice three", "Practice four", "Exam three", "Exam four", "P1", "P2"):
        assert label in response.text
    for hidden in ("HIDDEN-", "SYNTHETIC-ASSESSMENT-KEY", "SYNTHETIC-RUBRIC"):
        assert hidden not in response.text
    if export_format == "json":
        payload = response.json()
        practice_data = next(item for item in payload["contents"] if item["source_id"] == course.exercise.id)
        assert practice_data["content_data"]["options"] == {"choices": practice["choices"]}
        question = payload["assessments"][0]["questions"][0]
        assert question["options"] == {"choices": {"A": "Exam three", "B": "Exam four"}}
        assert question["correct_answer"] is None and question["content_metadata"] == {}
        assert payload["assessments"][0]["rubrics"] == []
    # Export sanitation is read-only; teacher originals and grading keys survive.
    course.db.refresh(course.assessment.questions[0])
    assert course.assessment.questions[0].options == exam
    assert course.assessment.questions[0].get_decrypted_correct_answer() == "SYNTHETIC-ASSESSMENT-KEY"


def test_learner_choice_arrays_keep_labels_but_never_nested_grading_fields():
    assert _learner_options({"choices": [
        "First", {"id": 2, "text": "Second", "is_correct": True, "rubric": "HIDDEN"},
        {"id": {"answer": "HIDDEN"}, "label": {"answer": "HIDDEN"}},
    ], "correct_answer": "HIDDEN"}) == {"choices": ["First", {"id": 2, "text": "Second"}, {}]}


@pytest.mark.parametrize("wrapper", [None, "choices", "options"])
def test_learner_choice_maps_strip_known_metadata_variants_without_mutating_original(wrapper):
    choices = {"A": "three", "B": "four", "correctAnswer": "HIDDEN", "answer_key": "HIDDEN",
               "isCorrect": "HIDDEN", "rubric-metadata": "HIDDEN", "grading_metadata": "HIDDEN"}
    value = choices if wrapper is None else {wrapper: choices, "feedback": "HIDDEN"}
    original = deepcopy(value)
    expected = {"A": "three", "B": "four"}
    assert _learner_options(value) == (expected if wrapper is None else {wrapper: expected})
    assert value == original


@pytest.mark.parametrize("answer,label", [
    (False, "false"), (-0.0, "0"), (0.000001, "0.000001"), (1e-7, "1e-7"),
    (1e20, "100000000000000000000"), (1e21, "1e+21"), (0.30000000000000004, "0.30000000000000004"),
])
def test_fresh_numeric_and_boolean_answers_match_browser_scalar_format(answer, label):
    assert _generated_choices({"A": "other", "B": label}, answer) == (
        {"choices": {"A": "other", "B": label}}, "B",
    )


@pytest.mark.parametrize("answer", [float("inf"), float("nan"), {}, []])
def test_nonfinite_or_structured_generated_answers_are_rejected(answer):
    with pytest.raises(ValueError):
        _generated_choices({"A": "three", "B": "four"}, answer)
