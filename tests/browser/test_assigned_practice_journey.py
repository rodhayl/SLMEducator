"""Exercise assigned practice in an isolated synthetic learner session."""

import os
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.browser.support import login, screenshot, start_material

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def test_assigned_practice_feedback_and_local_draft_recovery(
    live_page: Page, browser_world: Any
) -> None:
    """Check honest self-feedback and browser-only recovery, not grading."""
    page, world = live_page, browser_world
    question = "Choose the number of equal groups"
    exercise = world.api(
        "POST",
        "/api/content/",
        json={
            "title": "Synthetic assigned practice",
            "content_type": "exercise",
            "content_data": {
                "question": question,
                "type": "multiple_choice",
                "options": {"A": "One", "B": "Two"},
                "correct_answer": "B",
                "explanation": "There are two equal groups.",
            },
        },
    ).json()
    plan = world.api(
        "POST",
        "/api/study-plans/",
        json={
            "title": "Synthetic practice assignment",
            "phases": [{"name": "Practice", "content_ids": [exercise["id"]]}],
        },
    ).json()
    for action in ("review", "publish"):
        world.api(
            "POST",
            f"/api/study-plans/{plan['id']}/workflow",
            json={"action": action},
        )
    world.api(
        "POST",
        f"/api/study-plans/{plan['id']}/assign",
        json={"student_ids": [world.manifest["users"]["learner_a"]]},
    )

    login(page, world, "learner_a")
    start_material(page, world, exercise["id"], plan["id"])
    practice = page.get_by_role("region", name="Independent practice", exact=True)
    expect(practice).to_contain_text(
        "Self-checks are practice, not final grades."
    )
    assert exercise["id"] not in world.api(
        "GET",
        f"/api/study-plans/{plan['id']}/my-progress",
        account="learner_a",
    ).json()["completed_content_ids"]

    requests = []
    page.on("request", lambda request: requests.append(request))
    answer = practice.get_by_label(question, exact=True)
    answer.select_option("One")
    expect(practice).to_contain_text(
        "Practice draft saved in this browser. This does not submit an answer or update progress."
    )
    practice.get_by_role("button", name="Self-check", exact=True).click()
    expect(practice).to_contain_text("Compare your response with the answer key.")
    expect(practice).to_contain_text("Suggested answer: Two")
    expect(practice).to_contain_text("This is a practice self-check, not a final grade.")

    answer.select_option("Two")
    practice.get_by_role("button", name="Self-check", exact=True).click()
    expect(practice).to_contain_text("Your choice matches the answer key.")
    expect(practice).to_contain_text("Suggested answer: Two")
    expect(practice).to_contain_text("This is a practice self-check, not a final grade.")
    assert not [
        request
        for request in requests
        if request.url.startswith(world.base_url + "/api/")
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
    ]

    page.reload()
    expect(practice).to_contain_text(
        "A practice draft for this account, lesson and session is available."
    )
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/content/{exercise['id']}")
            and response.request.method == "GET"
        )
    ) as revalidated:
        practice.get_by_role("button", name="Restore draft", exact=True).click()
    assert revalidated.value.ok
    expect(answer).to_have_value("Two")
    practice.get_by_role("button", name="Self-check", exact=True).click()
    expect(practice).to_contain_text("Your choice matches the answer key.")
    expect(practice).to_contain_text("This is a practice self-check, not a final grade.")
    assert exercise["id"] not in world.api(
        "GET",
        f"/api/study-plans/{plan['id']}/my-progress",
        account="learner_a",
    ).json()["completed_content_ids"]
    screenshot(page, "assigned-practice-restored-feedback.png")
