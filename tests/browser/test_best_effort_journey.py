"""EN/ES acceptance through real browser, API and synthetic provider parser."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.browser.test_live_journeys import login, screenshot


@pytest.mark.parametrize("locale", ["en", "es"])
def test_independent_learner_best_effort(live_page, browser_world, locale):
    """Assigned reading and help work with only a learner browser session."""
    page, world = live_page, browser_world
    world.api("POST", "/api/settings/app", account="learner_a", json={"language": locale, "theme": "light"})
    page.add_init_script(f"localStorage.setItem('slm_language', '{locale}')")
    login(page, world, "learner_a")
    expect(page.locator("html")).to_have_attribute("lang", locale)
    expect(page.locator("#nav-create")).not_to_be_visible()
    first = world.manifest["content_ids"][0]
    plan = world.manifest["plan_id"]
    page.goto(f"{world.base_url}/session_player.html?content_id={first}&plan_id={plan}")
    expect(page.locator("#session-content-title")).to_contain_text(world.manifest["lesson_titles"][0])
    page.goto(world.base_url + "/dashboard.html")
    page.locator('[data-view="tutor"]').click()
    send = page.locator('#chat-form button[type="submit"]')
    expect(send).to_be_enabled()
    translations = json.loads((Path(__file__).parents[2] / "translations" / f"{locale}.json").read_text(encoding="utf-8"))
    calls = []
    page.on("request", lambda request: calls.append(request) if request.url.endswith("/api/ai/chat") else None)
    for mode in ("structured", "prose"):
        page.locator("#chat-input").fill(f"[acceptance:{mode}] Compare parts")
        with page.expect_response(lambda response: response.url.endswith("/api/ai/chat")) as response:
            send.click()
        data = response.value.json()
        assert data["status"] == "suggestion"
        assert data["receipt"]["status"] == "completed"
        expect(page.locator("#chat-history")).to_contain_text(f"Synthetic {mode}")
        expect(page.locator("#chat-history")).to_contain_text(translations["recovery"]["answer_unverified"])
        assert page.locator("#chat-history img, #chat-history script").count() == 0
        assert page.evaluate("window.acceptanceUnsafe") is None
        expect(page.locator("#chat-input")).to_have_value("")
    for mode, status in (("format", "invalid_response"), ("provider", "unavailable")):
        question = f"[acceptance:{mode}] Keep this question"
        page.locator("#chat-input").fill(question)
        ids = []
        for attempt in range(2):
            before = len(calls)
            with page.expect_response(lambda response: response.url.endswith("/api/ai/chat")) as response:
                send.click()
            data = response.value.json()
            assert data["status"] == status
            assert data["receipt"]["status"] == "failed"
            ids.append(data["receipt"]["request_id"])
            expect(page.locator("#tutor-request-status")).to_contain_text(data["response"])
            expect(page.locator("#chat-input")).to_have_value(question)
            expect(send).to_be_enabled()
            page.wait_for_timeout(350)
            assert len(calls) == before + 1
        assert ids[0] != ids[1]
        screenshot(page, f"best-effort-tutor-{mode}-{locale}.png")
    page.locator('[data-view="library"]').click()
    page.locator("#student-qa-btn").click()
    qa_calls = []
    page.on("request", lambda request: qa_calls.append(request) if request.url.endswith("/api/ai/answer-question") else None)
    for mode in ("structured", "prose", "format", "provider"):
        question = f"[acceptance:{mode}] Independent Q&A"
        page.locator("#qa-question").fill(question)
        before = len(qa_calls)
        with page.expect_response(lambda response: response.url.endswith("/api/ai/answer-question")) as response:
            page.locator("#qa-ask-ai-btn").click()
        data = response.value.json()
        assert data["success"] is (mode in ("structured", "prose"))
        assert data["receipt"]["status"] == ("completed" if data["success"] else "failed")
        expect(page.locator("#qa-ai-answer")).to_contain_text(translations["help_panel"]["unverified"])
        expect(page.locator("#qa-ai-answer-content")).to_contain_text("Synthetic" if data["success"] else data["answer"])
        expect(page.locator("#qa-question")).to_have_value(question)
        assert page.locator("#qa-ai-answer-content img, #qa-ai-answer-content script").count() == 0
        assert page.evaluate("window.acceptanceUnsafe") is None
        page.wait_for_timeout(350)
        assert len(qa_calls) == before + 1
        if not data["success"]:
            with page.expect_response(lambda response: response.url.endswith("/api/ai/answer-question")) as retry:
                page.locator("#qa-ask-ai-btn").click()
            assert retry.value.json()["success"] is False
            expect(page.locator("#qa-question")).to_have_value(question)
            assert len(qa_calls) == before + 2
    screenshot(page, f"best-effort-qa-{locale}.png")
