"""Generation obeys the same graph and current-source boundaries as manual edits."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.api.routes.generation import FullTopicPackageRequest
from src.core.models import Content, StudyPlanContent, StudentStudyPlan
from src.core.services.ai_service import AIProvider
from src.core.services.generation_workflow import generate_package
from src.core.services.source_documents import save_document
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def setup_generation(scenario):
    """Prepare an unassigned synthetic draft and a provider with no network path."""
    client, db, users, selected, plan, _, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    service = SimpleNamespace(
        model="synthetic",
        provider=AIProvider.OLLAMA,
        generate_lesson=MagicMock(return_value={"content": "Generated synthetic text"}),
    )
    request = FullTopicPackageRequest(
        subject="Math", topic_name="Fractions", grade_level="synthetic adult",
        learning_objectives=[], include_exercises=False, include_assessment=False,
        auto_save=True, study_plan_id=plan.id,
    )
    return client, db, users["teacher_a"], plan, service, request


def test_generation_refuses_full_phase_before_provider_or_writes(scenario):
    _, db, teacher, plan, service, request = setup_generation(scenario)
    link = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id).first()
    link.phase_index, link.order_index = 0, 1000
    db.commit()
    before = db.query(Content).count(), plan.content_metadata
    with pytest.raises(ValueError, match="phase is full"):
        generate_package(db, teacher, plan, service, request)
    assert service.generate_lesson.call_count == 0
    assert before == (db.query(Content).count(), plan.content_metadata)


@pytest.mark.parametrize("change", ["text", "metadata"])
def test_source_change_during_generation_cannot_save_mixed_provenance(scenario, change):
    _, db, teacher, plan, service, request = setup_generation(scenario)
    source = {"extracted_text": "Original source", "filename": "original.txt"}
    saved = save_document(db, plan, source)
    db.commit()
    request = request.model_copy(update={"source_document_id": saved["document_id"]})
    before = db.query(Content).count()

    def replace_source(**kwargs):
        replacement = {**source, "filename": "corrected.txt"}
        if change == "text":
            replacement["extracted_text"] = "Replacement source"
        save_document(db, plan, replacement)
        db.commit()
        return {"content": "Old provider answer"}

    service.generate_lesson.side_effect = replace_source
    result = generate_package(db, teacher, plan, service, request)
    assert result["success"] is False
    assert result["saved_content_ids"] == []
    assert db.query(Content).count() == before
    job = plan.decrypted_metadata["generation_jobs"][result["job_key"]]
    assert job["items"]["lesson"]["status"] == "failed"
    if change == "text":
        assert job["obsolete_source"] is True


@pytest.mark.parametrize("route", ["single", "topic", "batch"])
def test_manual_append_skips_unfinished_generation_reservations(scenario, route):
    client, db, _, plan, _, _ = setup_generation(scenario)
    plan.set_encrypted_metadata({
        "workflow": {"status": "draft", "version": 0},
        "generation_jobs": {"synthetic": {
            "phase_index": 0, "item_positions": {"lesson": 1, "exercise-0": 2},
            "items": {"exercise-0": {"status": "failed"}},
        }},
    })
    db.commit()
    from tests.trust.test_content_ingress_contract import create

    response = create(client, plan.id, route, {"content": "Manually authored text"})
    assert response.status_code == 200, response.text
    links = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id, phase_index=0)
    assert sorted(link.order_index for link in links) == [0, 3]


def test_generation_retry_refuses_a_reserved_position_occupied_by_reorder(scenario):
    _, db, teacher, plan, service, request = setup_generation(scenario)
    service.generate_lesson.side_effect = ValueError("Synthetic invalid response")
    first = generate_package(db, teacher, plan, service, request)
    assert first["success"] is False
    job = plan.decrypted_metadata["generation_jobs"][first["job_key"]]
    reserved = job["item_positions"]["lesson"]
    link = db.query(StudyPlanContent).filter_by(study_plan_id=plan.id).first()
    link.phase_index, link.order_index = 0, reserved
    db.commit()
    before = db.query(Content).count()
    service.generate_lesson.side_effect = None
    with pytest.raises(ValueError, match="Reserved course position changed"):
        generate_package(db, teacher, plan, service, request)
    assert service.generate_lesson.call_count == 1
    assert db.query(Content).count() == before
