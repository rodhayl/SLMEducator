"""Real Chromium option-preview integration with explicitly synthetic HTTP."""

import json
import os

import pytest
from playwright.sync_api import expect

from test_live_journeys import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def test_teacher_previews_supported_options_and_retries_failure(live_page, browser_world):
    """Check real asset loading, accepted shapes and form preservation on failure."""
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.locator('[data-view="create"]').click()
    for mode, visible in [("study_plan", "study-plan-mode-fields"), ("topic", "topic-mode-fields"),
                          ("exercise", "exercise-mode-fields"), ("topic", "topic-mode-fields")]:
        page.locator(f'[name="generation_mode"][value="{mode}"]').check()
        expect(page.locator(f"#{visible}")).to_be_visible()
        expect(page.locator("#generate-btn")).to_be_visible()
        if mode == "study_plan":
            expect(page.locator("#save-options-section")).to_be_hidden()
        else:
            expect(page.locator("#save-options-section")).to_be_visible()
        assert page.locator('[name="learning_objectives"]').evaluate("node => node.required") is (mode == "topic")
        if mode != "topic":
            assert page.locator("#create-ai-content-form").evaluate("form => form.checkValidity()")
    page.locator("#mode-exercise").check()
    page.locator('[name="exercise_topic"]').fill("Synthetic option preview")
    options = [
        ["One", "Two"],
        {"first": "One", "second": "Two"},
        {"choices": ["One", "Two"]},
        {"choices": {"first": "One", "second": "Two"}},
    ]
    pending = []

    def provider_fixture(route):
        status, data = pending.pop(0)
        route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

    page.route("**/api/generate/exercise", provider_fixture)
    for index, choices in enumerate(options):
        pending.append((200, {"question": "Synthetic: choose two", "type": "multiple_choice",
                              "options": choices, "correct_answer": "B" if index % 2 == 0 else "second"}))
        page.locator("#generate-btn").click()
        expect(page.locator("#ai-content-generation-result")).to_be_visible()
        expect(page.locator("#generated-items-list li")).to_have_count(2)
        expect(page.locator("#generated-items-list li").nth(0)).to_contain_text("One")
        expect(page.locator("#generated-items-list li").nth(1)).to_contain_text("Two")
    screenshot(page, "practice-mapped-options.png")
    pending.append((500, {"detail": "Synthetic invalid option container; retry your request."}))
    page.locator("#generate-btn").click()
    expect(page.locator("#ai-content-generation-result")).to_be_hidden()
    expect(page.locator('[name="exercise_topic"]')).to_have_value("Synthetic option preview")
    expect(page.locator("#generate-btn")).to_be_enabled()
    expect(page.get_by_text("Generation failed: Synthetic invalid option container; retry your request.", exact=True)).to_be_visible()
    screenshot(page, "practice-generation-failure.png")
    pending.append((200, {"question": "Synthetic retry: choose two", "type": "multiple_choice",
                          "options": options[1], "correct_answer": "second"}))
    page.locator("#generate-btn").click()
    expect(page.locator("#generated-items-list")).to_contain_text("Synthetic retry: choose two")
    expect(page.locator("#generated-items-list li")).to_have_count(2)
    assert pending == []
