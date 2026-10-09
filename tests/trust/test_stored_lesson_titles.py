"""Read-time lesson normalization never translates or rewrites stored author titles."""

import pytest

from tests.trust.test_resource_contracts import scenario, synthetic_credentials  # noqa: F401,F811


@pytest.mark.parametrize("section_title", ["Lesson", "Lección", "Recuperación independiente", ""])
def test_author_and_learner_reads_preserve_historical_titles_and_storage(scenario, section_title):  # noqa: F811
    client, db, users, selected, _, lessons, _ = scenario
    lesson = lessons[0]
    original_data = {
        "content": "Historical introductory text.",
        "sections": [{"title": section_title, "content": "Historical section text."}],
    }
    lesson.title = "Original Lesson / Lección histórica"
    lesson.set_encrypted_content_data(original_data)
    db.commit()
    stored_ciphertext, stored_updated_at = lesson.content_data, lesson.updated_at

    for role in ("teacher_a", "learner_a"):
        selected[0] = users[role]
        for language in ("es", "en"):
            response = client.get(f"/api/content/{lesson.id}", headers={"Accept-Language": language})
            assert response.status_code == 200, response.text
            content = response.json()
            assert content["title"] == "Original Lesson / Lección histórica"
            assert [section["title"] for section in content["content_data"]["sections"]] == ["", section_title]
            db.refresh(lesson)
            assert lesson.decrypted_content_data == original_data
            assert lesson.content_data == stored_ciphertext
            assert lesson.updated_at == stored_updated_at
