"""Deterministic source/failure/resume contracts; no real inference."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from starlette.datastructures import UploadFile, Headers
from tests.trust.test_resource_contracts import scenario, synthetic_credentials
from src.api.dependencies import get_ai_service_dependency
from src.api.main import app
from src.core.models import Content, Assessment, StudentStudyPlan, StudyPlanContent
from src.core.services.file_service import (
    FileProcessingService,
    MAX_SOURCE_BYTES,
    MAX_SOURCE_CHARACTERS,
)
from src.core.services.ai_service import AIService, RuntimeAIConfig, AIProvider
from src.core.exceptions import AIResponseParseError, AIContentValidationError


@pytest.mark.asyncio
async def test_source_limits_provenance_and_unsupported_files():
    doc = await FileProcessingService.extract_document(
        UploadFile(io.BytesIO(b"Fractions explain equal parts."), filename="lesson.txt")
    )
    assert (
        doc["coverage"] == "complete" and doc["sections"][0]["reference"] == "section:1"
    )
    assert len(doc["source_version"]) == 64
    long = await FileProcessingService.extract_document(
        UploadFile(
            io.BytesIO(b"A" * (MAX_SOURCE_CHARACTERS + 1)), filename="lesson.txt"
        )
    )
    assert long["truncated"] and long["coverage"] == "partial"
    with pytest.raises(ValueError, match="10 MiB"):
        await FileProcessingService.extract_document(
            UploadFile(io.BytesIO(b"A" * (MAX_SOURCE_BYTES + 1)), filename="lesson.txt")
        )
    with pytest.raises(ValueError, match="Supported sources"):
        await FileProcessingService.extract_document(
            UploadFile(io.BytesIO(b"not text"), filename="lesson.exe")
        )


def test_parsers_reject_placeholder_success(monkeypatch):
    monkeypatch.setattr(
        AIService, "_setup_client", lambda self: setattr(self, "_client", MagicMock())
    )
    service = AIService(
        RuntimeAIConfig(provider="ollama", model="synthetic"), MagicMock()
    )
    with pytest.raises(AIResponseParseError):
        service._parse_exercise_response("bad JSON", "fractions")
    with pytest.raises(AIContentValidationError):
        service._parse_exercise_response(
            '{"question":"Error generating exercise"}', "fractions"
        )
    with pytest.raises(AIResponseParseError):
        service._parse_study_plan_response("bad JSON")
    with pytest.raises(AIResponseParseError):
        service._parse_tutoring_response("{broken")


def test_generation_retries_failed_item_only_and_preserves_teacher_edits(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    service = MagicMock()
    service.model, service.provider = "synthetic", AIProvider.OLLAMA
    service.generate_lesson.return_value = {
        "title": "Generated fractions",
        "content": "SOURCE: compare numerators.",
    }
    service.generate_exercise.side_effect = [
        AIResponseParseError("synthetic parse"),
        {
            "question": "Which is larger, 3/8 or 5/8?",
            "type": "short_answer",
            "correct_answer": "5/8",
        },
    ]
    service.generate_assessment_questions.return_value = [
        {
            "question_text": "Explain 3/8",
            "question_type": "short_answer",
            "points": 10,
            "correct_answer": "Three equal parts out of eight",
            "rubric": {
                "name": "Reason",
                "criteria": [{"name": "Equal parts", "max_points": 10}],
            },
        }
    ]
    app.dependency_overrides[get_ai_service_dependency] = lambda: service
    payload = {
        "subject": "Fractions",
        "topic_name": "Compare",
        "grade_level": "adult synthetic",
        "learning_objectives": ["Compare fractions"],
        "include_lesson": True,
        "include_exercises": True,
        "num_exercises": 1,
        "include_assessment": True,
        "auto_save": True,
        "study_plan_id": plan.id,
        "source_material": "Synthetic SOURCE material.",
        "phase_index": 2,
    }
    first = client.post("/api/generate/full-topic-package", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["success"] is False
    assert first.json()["items"][1]["error_code"] == "parse_failure"
    lesson_id = first.json()["items"][0]["content_id"]
    assert (
        client.put(
            f"/api/content/{lesson_id}",
            json={"content_data": {"content": "Teacher revised source"}},
        ).status_code
        == 200
    )
    second = client.post("/api/generate/full-topic-package", json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["success"] is True
    assert second.json()["lesson"]["content"] == "Teacher revised source"
    assert service.generate_lesson.call_count == 1
    assert service.generate_exercise.call_count == 2
    assert service.generate_assessment_questions.call_count == 1
    assert len(set(second.json()["saved_content_ids"])) == 3
    generated_ids = second.json()["saved_content_ids"]
    ordered = (
        db.query(StudyPlanContent)
        .filter(StudyPlanContent.content_id.in_(generated_ids))
        .order_by(StudyPlanContent.phase_index, StudyPlanContent.order_index)
        .all()
    )
    assert [link.content_id for link in ordered] == generated_ids
    assert len({link.order_index for link in ordered}) == 3
    assessment = db.query(Assessment).one()
    assert not assessment.is_published and len(assessment.questions) == 1
    assert assessment.questions[0].rubrics[0].criteria[0].max_points == 10
    jobs = client.get(f"/api/generate/courses/{plan.id}/jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[second.json()["job_key"]]["items"]["exercise-0"]["status"] == "ready"
    app.dependency_overrides.pop(get_ai_service_dependency, None)


def test_empty_lesson_cannot_be_published_or_claimed_as_grounding():
    from src.core.services.content_schema import normalize_content
    from src.core.services.learning_context import source_context
    from src.core.models import ContentType

    with pytest.raises(ValueError, match="nonempty"):
        normalize_content("lesson", {"sections": [{"title": "Empty", "content": ""}]})
    with pytest.raises(ValueError, match="no readable"):
        source_context(
            SimpleNamespace(
                id=1,
                title="Empty",
                content_type=ContentType.LESSON,
                content_data=None,
                decrypted_content_data={},
            )
        )


def test_cancel_preserves_ready_item_and_explicit_retry_resumes(scenario):
    client, db, users, selected, plan, _, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    service = MagicMock()
    service.model = "synthetic"
    service.provider = AIProvider.OLLAMA

    def lesson_then_cancel(**kwargs):
        jobs = client.get(f"/api/generate/courses/{plan.id}/jobs").json()["jobs"]
        key = next(iter(jobs))
        assert (
            client.post(
                f"/api/generate/courses/{plan.id}/jobs/{key}/cancel"
            ).status_code
            == 200
        )
        return {"content": "The in-flight synthetic lesson finishes safely."}

    service.generate_lesson.side_effect = lesson_then_cancel
    service.generate_exercise.return_value = {
        "question": "Compare 2/5 and 3/5",
        "type": "short_answer",
    }
    app.dependency_overrides[get_ai_service_dependency] = lambda: service
    payload = {
        "subject": "Fractions",
        "topic_name": "Cancellation",
        "grade_level": "synthetic adult",
        "learning_objectives": [],
        "include_lesson": True,
        "include_exercises": True,
        "num_exercises": 1,
        "include_assessment": False,
        "auto_save": True,
        "study_plan_id": plan.id,
    }
    first = client.post("/api/generate/full-topic-package", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["success"] is False
    assert [item["status"] for item in first.json()["items"]] == ["ready", "cancelled"]
    assert service.generate_exercise.call_count == 0
    jobs = client.get(f"/api/generate/courses/{plan.id}/jobs").json()["jobs"]
    assert jobs[first.json()["job_key"]]["items"]["exercise-0"]["status"] == "cancelled"
    retry = client.post("/api/generate/full-topic-package", json=payload)
    assert retry.status_code == 200 and retry.json()["success"] is True, retry.text
    assert (
        service.generate_lesson.call_count == 1
        and service.generate_exercise.call_count == 1
    )
