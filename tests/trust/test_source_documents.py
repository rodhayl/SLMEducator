"""Durable owned extraction and exact bounded prompt provenance, without inference."""

import io
import json
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from starlette.datastructures import UploadFile

from src.core.models import Content, StudentStudyPlan
from src.core.services.ai_service import AIService, AIProvider
from src.core.services.file_service import FileProcessingService
from src.core.services.generation_workflow import generate_package
from src.core.services.portability_service import export_course, import_course
from src.api.routes.generation import FullTopicPackageRequest
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def document(text="Synthetic source"):
    return {
        "filename": "synthetic.txt",
        "extracted_text": "[section:1]\n" + text,
        "sections": [{"reference": "section:1", "text": text}],
        "coverage": "complete",
        "source_version": sha256(text.encode()).hexdigest(),
        "parser": "utf8-text-v1",
    }


def prepare(scenario):
    client, db, users, selected, plan, lessons, _ = scenario
    db.query(StudentStudyPlan).filter_by(study_plan_id=plan.id).delete()
    db.commit()
    selected[0] = users["teacher_a"]
    return client, db, users, selected, plan


def test_source_is_owned_durable_and_teacher_roundtrip_preserves_extraction(scenario):
    client, db, users, selected, plan = prepare(scenario)
    source = document()
    response = client.put(f"/api/study-plans/{plan.id}/source", json=source)
    assert response.status_code == 200, response.text
    document_id = response.json()["document_id"]
    db.expire_all()
    assert (
        client.get(f"/api/study-plans/{plan.id}/source").json()["source"]["document_id"]
        == document_id
    )
    stored = plan.decrypted_metadata["source_document"]
    assert stored["original_bytes_hash"] == source["source_version"]
    assert (
        stored["extraction_coverage"] == "complete"
        and not stored["original_binary_included"]
    )
    package = export_course(db, selected[0], plan, "teacher")
    copied = import_course(db, users["teacher_b"], package)
    db.commit()
    assert copied.decrypted_metadata["source_document"] == stored
    selected[0] = users["teacher_b"]
    assert client.get(f"/api/study-plans/{plan.id}/source").status_code == 403
    selected[0] = users["learner_a"]
    assert client.get(f"/api/study-plans/{plan.id}/source").status_code == 403


def test_source_section_mismatch_is_rejected_without_metadata_change(scenario):
    client, db, users, selected, plan = prepare(scenario)
    before = plan.decrypted_metadata
    invalid = document()
    invalid["sections"][0]["text"] = "Different from preview"
    assert (
        client.put(f"/api/study-plans/{plan.id}/source", json=invalid).status_code
        == 409
    )
    db.refresh(plan)
    assert plan.decrypted_metadata == before


def test_generation_records_used_fragment_and_rejects_old_source_after_replacement(
    scenario,
):
    client, db, users, selected, plan = prepare(scenario)
    source = document("earlier " * 1500 + "LATE_NUMERATOR_MARKER useful ending")
    saved = client.put(f"/api/study-plans/{plan.id}/source", json=source).json()
    service = SimpleNamespace(
        model="synthetic",
        provider=AIProvider.OLLAMA,
        generate_lesson=MagicMock(
            return_value={"content": "Reviewed later synthetic lesson"}
        ),
    )
    request = FullTopicPackageRequest(
        subject="Math",
        topic_name="LATE_NUMERATOR_MARKER",
        grade_level="synthetic adult",
        learning_objectives=["Read ending"],
        include_exercises=False,
        include_assessment=False,
        auto_save=True,
        study_plan_id=plan.id,
        source_document_id=saved["document_id"],
    )
    result = generate_package(db, users["teacher_a"], plan, service, request)
    assert result["success"]
    content = db.get(Content, result["saved_content_ids"][0])
    provenance = content.decrypted_content_data["generation"]
    assert provenance["source_document_id"] == saved["document_id"]
    assert provenance["extraction_coverage"] == "complete"
    assert provenance["source_usage"]["use_coverage"] == "partial"
    assert "LATE_NUMERATOR_MARKER" in provenance["source_usage"]["fragment"]
    assert (
        provenance["source_usage"]["fragment_hash"]
        == sha256(provenance["source_usage"]["fragment"].encode()).hexdigest()
    )
    replacement = client.put(
        f"/api/study-plans/{plan.id}/source", json=document("Replacement")
    )
    assert replacement.status_code == 200
    assert plan.decrypted_metadata["generation_jobs"][result["job_key"]][
        "obsolete_source"
    ]
    with pytest.raises(ValueError, match="revision changed"):
        generate_package(db, users["teacher_a"], plan, service, request)
    assert service.generate_lesson.call_count == 1
    assert db.get(Content, content.id) is not None


@pytest.mark.asyncio
async def test_maximum_source_including_reference_labels_fits_generation_contract():
    extracted = await FileProcessingService.extract_document(
        UploadFile(io.BytesIO(b"A" * 100000), filename="large.txt")
    )
    assert len(extracted["extracted_text"]) <= 100000
    assert extracted["coverage"] == "partial" and extracted["truncated"]
    FullTopicPackageRequest(
        subject="Synthetic",
        topic_name="Text",
        grade_level="synthetic adult",
        learning_objectives=[],
        source_material=extracted["extracted_text"],
    )


def test_lesson_prompt_includes_relevant_late_text_and_explicit_usage():
    service = AIService.__new__(AIService)
    service.logger = MagicMock()
    captured = []

    def call(prompt, **kwargs):
        captured.append(prompt)
        return SimpleNamespace(content='{"content":"synthetic"}')

    service._call_ai = call
    service._parse_json_response = lambda text, kind: json.loads(text)
    result = service.generate_lesson(
        "LATE_MARKER",
        "synthetic",
        ["Find LATE_MARKER"],
        source_material="prefix " * 2000 + "LATE_MARKER: numerator",
    )
    assert "LATE_MARKER: numerator" in captured[0]
    assert "UNTRUSTED SOURCE DATA" in captured[0]
    usage = result["_source_usage"]
    assert usage["fragment"] in captured[0] and usage["use_coverage"] == "partial"
    assert usage["included_characters"] <= 6000


def test_same_text_metadata_correction_preserves_prior_provenance(scenario):
    client, db, users, selected, plan = prepare(scenario)
    original = document()
    first = client.put(f"/api/study-plans/{plan.id}/source", json=original).json()[
        "source"
    ]
    corrected = {
        **original,
        "filename": "renamed.txt",
        "parser": "utf8-text-v2",
        "coverage": "partial",
    }
    second = client.put(f"/api/study-plans/{plan.id}/source", json=corrected).json()[
        "source"
    ]
    assert second["document_id"] == first["document_id"]
    assert second["metadata_revision"] != first["metadata_revision"]
    assert (
        second["filename"] == "renamed.txt"
        and second["extraction_coverage"] == "partial"
    )
    assert plan.decrypted_metadata["source_history"][-1] == first
    assert (
        client.put(f"/api/study-plans/{plan.id}/source", json=corrected).json()[
            "source"
        ]
        == second
    )
