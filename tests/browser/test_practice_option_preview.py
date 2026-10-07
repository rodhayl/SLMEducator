"""React option editors and retries with explicitly synthetic generation HTTP."""

import os

import pytest
from playwright.sync_api import expect

from tests.browser.support import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def test_teacher_previews_supported_options_and_retries_failure(
    live_page, browser_world
):
    """Generation modes retain setup; mapped keys and good proposals survive failure."""
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.goto(world.base_url + "/generar")
    mode = page.get_by_label("Generation mode", exact=True)
    page.get_by_label("Subject", exact=True).fill("Arithmetic")
    page.get_by_label("Grade or learning level", exact=True).fill("Adult beginner")
    page.get_by_label("Topic", exact=True).fill("Synthetic option preview")
    page.get_by_label("Learning objectives (one per line)", exact=True).fill(
        "Compare equal parts"
    )
    for value in ("plan", "outline", "package", "lesson", "exercise"):
        mode.select_option(value)
        expect(
            page.get_by_role("button", name="Generate with AI", exact=True)
        ).to_be_visible()
        expect(page.get_by_label("Subject", exact=True)).to_have_value("Arithmetic")
        if value in ("plan", "outline"):
            expect(page.get_by_label("Duration (weeks)", exact=True)).to_be_visible()
            expect(page.get_by_label("Topic", exact=True)).to_have_count(0)
        else:
            expect(page.get_by_label("Topic", exact=True)).to_have_value(
                "Synthetic option preview"
            )
    options = [
        ["One", "Two"],
        {"first": "One", "second": "Two"},
        {"choices": ["One", "Two"]},
        {"choices": {"first": "One", "second": "Two"}},
    ]
    pending = []

    def provider_fixture(route):
        status, data = pending.pop(0)
        route.fulfill(status=status, json=data)

    page.route("**/api/generate/exercise", provider_fixture)
    generate = page.get_by_role("button", name="Generate with AI", exact=True)
    for index, choices in enumerate(options):
        pending.append(
            (
                200,
                {
                    "question": "Synthetic: choose two",
                    "type": "multiple_choice",
                    "options": choices,
                    "correct_answer": "B" if index % 2 == 0 else "second",
                },
            )
        )
        generate.click()
        expect(page.get_by_label("Question", exact=True)).to_have_count(index + 1)
        expect(page.get_by_label("Choice 1 text", exact=True).nth(index)).to_have_value(
            "One"
        )
        expect(page.get_by_label("Choice 2 text", exact=True).nth(index)).to_have_value(
            "Two"
        )
        expect(
            page.get_by_label("Correct answer", exact=True).nth(index)
        ).to_have_value("B" if index % 2 == 0 else "second")
    screenshot(page, "practice-mapped-options.png")
    pending.append(
        (500, {"detail": "Synthetic invalid option container; retry your request."})
    )
    generate.click()
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page.get_by_label("Question", exact=True)).to_have_count(4)
    expect(page.get_by_label("Topic", exact=True)).to_have_value(
        "Synthetic option preview"
    )
    expect(generate).to_be_enabled()
    screenshot(page, "practice-generation-failure.png")
    pending.append(
        (
            200,
            {
                "question": "Synthetic retry: choose two",
                "type": "multiple_choice",
                "options": options[1],
                "correct_answer": "second",
            },
        )
    )
    # The explicit retry confirms the saved original request, not an automatic replay.
    page.get_by_role("button", name="Retry the captured request", exact=True).click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Retry the captured request", exact=True
    ).click()
    expect(page.get_by_label("Question", exact=True)).to_have_count(5)
    expect(page.get_by_label("Question", exact=True).last).to_have_value(
        "Synthetic retry: choose two"
    )
    expect(page.get_by_label("Choice 2 text", exact=True).last).to_have_value("Two")
    assert pending == []
