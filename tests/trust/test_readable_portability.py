"""Readable handouts and versioned portable graphs keep pedagogical data safely."""

from copy import deepcopy
import json
import pytest

from src.core.services.portability_service import (
    export_course,
    import_course,
    validate_package,
)
from tests.integration.test_portability_recovery import course


def test_readable_formats_are_inert_and_do_not_include_teacher_assets(course):
    course.lesson.set_encrypted_content_data(
        {
            "content": "<script>alert('synthetic')</script> Instruction",
            "vocabulary": [{"term": "numerator", "definition": "top value"}],
        }
    )
    course.db.commit()
    course.user = course.reader
    for name, media in (
        ("html", "text/html"),
        ("markdown", "text/markdown"),
        ("json", "application/json"),
    ):
        response = course.client.get(
            f"/api/portability/plans/{course.plan.id}/export?audience=learner&format={name}"
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(media)
        assert "numerator" in response.text and "top value" in response.text
        assert (
            "SYNTHETIC-ASSESSMENT-KEY" not in response.text
            and "SYNTHETIC-RUBRIC" not in response.text
        )
        if name != "json":
            assert "<script>" not in response.text and "&lt;script&gt;" in response.text
    course.user = course.author
    assert (
        course.client.get(
            f"/api/portability/plans/{course.plan.id}/export?audience=teacher&format=html"
        ).status_code
        == 422
    )


def test_v1_is_explicitly_supported_and_v2_graph_has_a_validated_manifest(course):
    package = export_course(course.db, course.author, course.plan, "teacher")
    assert package["version"] == 2
    assert package["manifest"]["ordered_content_ids"] == [
        course.lesson.id,
        course.exercise.id,
    ]
    copied = deepcopy(package)
    copied["version"] = 1
    copied.pop("manifest")
    imported = import_course(course.db, course.recipient, copied)
    course.db.commit()
    assert imported.decrypted_metadata["import_lineage"]["package_version"] == 1
    for mutation in ("future", "wrong_order", "inconsistent_phase"):
        invalid = deepcopy(package)
        if mutation == "future":
            invalid["version"] = 999
        elif mutation == "wrong_order":
            invalid["manifest"]["ordered_content_ids"].reverse()
        else:
            invalid["study_plan"]["phases"][0]["content_ids"] = [course.exercise.id]
        with pytest.raises(ValueError):
            validate_package(invalid)
