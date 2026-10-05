"""Practice options retain supported collections and reject scalar containers."""

import json

import pytest

from src.api.routes import generation
from src.core.models import Content, StudyPlan
from src.core.services.content_schema import normalize_content
from src.core.services.generation_workflow import generate_package
from src.core.exceptions import AIContentValidationError
from tests import test_lesson_generation_contract

lesson_client = test_lesson_generation_contract.lesson_client


@pytest.mark.parametrize("type_field", ["type", "question_type"])
@pytest.mark.parametrize("options", [
    "One, Two", 1, True, None, [], {},
    {"choices": "One, Two"}, {"choices": []}, {"choices": 1},
])
def test_generated_multiple_choice_rejects_invalid_option_containers(
    lesson_client, type_field, options
):
    client, output = lesson_client
    output.update(question="Choose one", options=options, **{type_field: "multiple_choice"})
    response = client.post("/api/generate/exercise", json={
        "topic": "Synthetic options", "difficulty": "easy", "exercise_type": "multiple_choice",
    })
    assert response.status_code == 500


@pytest.mark.parametrize("type_field", ["type", "question_type"])
@pytest.mark.parametrize("options", [
    ["One", "Two"], {"A": "One", "B": "Two"},
    {"choices": ["One", "Two"]}, {"choices": {"A": "One", "B": "Two"}},
])
def test_practice_keeps_renderer_supported_legacy_option_shapes(type_field, options):
    source = {"question": "Choose one", type_field: "multiple_choice", "options": options}
    result = normalize_content("exercise", source)
    assert result["options"] == options
    assert source == {"question": "Choose one", type_field: "multiple_choice", "options": options}


def test_package_rejects_scalar_options_before_saving(lesson_client, db_session, test_teacher):
    client, output = lesson_client
    output.update(question="Choose one", type="multiple_choice", options="One, Two")
    plan = StudyPlan(title="Synthetic option contract", creator_id=test_teacher.id, phases=[])
    db_session.add(plan)
    db_session.commit()
    service = client.app.dependency_overrides[generation.get_ai_service_dependency]()
    request = generation.FullTopicPackageRequest(
        subject="Synthetic options", topic_name="Choose one", grade_level="Adult introductory",
        learning_objectives=[], include_lesson=False, include_exercises=True,
        include_assessment=False, num_exercises=1, auto_save=True, study_plan_id=plan.id,
    )
    result = generate_package(db_session, test_teacher, plan, service, request)
    assert result["success"] is False
    assert result["items"][0]["error_code"] == "content_validation"
    assert result["saved_content_ids"] == []
    assert db_session.query(Content).filter_by(study_plan_id=plan.id).count() == 0


def test_generator_rejects_exact_question_and_options_template_echo(lesson_client):
    client, _ = lesson_client
    service = client.app.dependency_overrides[generation.get_ai_service_dependency]()
    echoed = {"question": "Exercise question/prompt", "type": "multiple_choice",
              "options": ["option1", "option2", "option3", "option4"],
              "correct_answer": "option1"}
    with pytest.raises(AIContentValidationError, match="prompt template"):
        service._parse_exercise_response(json.dumps(echoed), "Synthetic source")
    assert normalize_content("exercise", echoed)["question"] == echoed["question"]


def test_generator_keeps_legitimate_questions_with_placeholder_named_choices(lesson_client):
    client, _ = lesson_client
    service = client.app.dependency_overrides[generation.get_ai_service_dependency]()
    authored = {"question": "Which variable is selected first in this program?",
                "type": "multiple_choice",
                "options": ["option1", "option2", "option3", "option4"],
                "correct_answer": "option1"}
    assert service._parse_exercise_response(json.dumps(authored), "Programming")["options"] == authored["options"]
