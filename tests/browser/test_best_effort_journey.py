"""EN/ES persisted questions through the browser, API and synthetic parser."""
import os
import re

import pytest
from playwright.sync_api import expect

from tests.browser.support import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)

LABELS = {
    "en": {"title": "Ask", "prompt": "What would you like help with?",
           "send": "Ask the AI", "new": "Write a question",
           "unverified": "AI suggestion, not verified.",
           "failed": "No usable suggestion was confirmed.", "continue": "Continue"},
    "es": {"title": "Preguntar", "prompt": "¿En qué necesitas ayuda?",
           "send": "Pedir una sugerencia a la IA", "new": "Escribir una pregunta",
           "unverified": "Sugerencia de IA sin verificar.",
           "failed": "No se confirmó una sugerencia utilizable.", "continue": "Continuar"},
}


@pytest.mark.parametrize("locale", ["en", "es"])
def test_independent_learner_best_effort(live_page, browser_world, locale):
    """One saved thread survives reload; failures retry on that same thread."""
    page, world, labels = live_page, browser_world, LABELS[locale]
    login(page, world, "learner_a", locale)
    expect(page.get_by_role("navigation").get_by_role(
        "link", name=re.compile("^(People|Personas)$"))).to_have_count(0)
    first, plan = world.manifest["content_ids"][0], world.manifest["plan_id"]
    page.goto(f"{world.base_url}/materiales/{first}?plan_id={plan}")
    expect(page.get_by_role("article")).to_be_visible()
    page.get_by_role("navigation").get_by_role("link", name=labels["title"], exact=True).click()
    calls = []
    page.on("request", lambda request: calls.append(request.url)
            if re.search(r"/api/questions/(ask|\d+/ai)$", request.url)
            and request.method == "POST" else None)
    for mode in ("structured", "prose", "format", "provider"):
        page.get_by_role("button", name=labels["new"], exact=True).click()
        question = f"[acceptance:{mode}] Compare parts {locale}"
        page.get_by_label(labels["prompt"], exact=True).fill(question)
        before = len(calls)
        with page.expect_response(lambda response: response.url.endswith("/api/questions/ask")) as response:
            page.get_by_role("button", name=labels["send"], exact=True).click()
        data = response.value.json()
        thread_id = data["question_id"]
        saved = world.api("GET", f"/api/questions/{thread_id}", account="learner_a").json()
        assert saved["question"] == question
        if mode in ("structured", "prose"):
            assert data["status"] == "suggestion" and data["receipt"]["status"] == "completed"
            expect(page).to_have_url(re.compile(rf"thread_id={thread_id}(?:&|$)"))
            expect(page.get_by_role("log")).to_contain_text(f"Synthetic {mode}")
            expect(page.get_by_role("log")).to_contain_text(labels["unverified"])
            page.reload()
            expect(page.get_by_role("log")).to_contain_text(f"Synthetic {mode}")
            assert len(saved["replies"]) == 1 and saved["replies"][0]["kind"] == "ai"
        else:
            assert data["status"] == {"format": "invalid_response", "provider": "unavailable"}[mode]
            assert data["receipt"]["status"] == "failed" and saved["replies"] == []
            expect(page.get_by_role("status").filter(has_text=labels["failed"])).to_be_visible()
            expect(page.get_by_label(labels["prompt"], exact=True)).to_have_value(question)
            # Open the durable question and retry AI there, without creating a second question.
            page.get_by_role("button", name=question, exact=True).click()
            page.get_by_role("dialog").get_by_role("button", name=labels["continue"], exact=True).click()
            with page.expect_response(lambda response: response.url.endswith(f"/api/questions/{thread_id}/ai")) as retry:
                page.get_by_role("button", name=labels["send"], exact=True).click()
            retried = retry.value.json()
            assert retried["receipt"]["status"] == "failed"
            assert retried["receipt"]["request_id"] != data["receipt"]["request_id"]
            assert world.api("GET", f"/api/questions/{thread_id}", account="learner_a").json()["replies"] == []
            expect(page.get_by_role("status").filter(has_text=labels["failed"])).to_be_visible()
            before += 1
        assert page.get_by_role("log").locator("img, script").count() == 0
        assert page.evaluate("window.acceptanceUnsafe") is None
        page.wait_for_timeout(350)
        assert len(calls) == before + 1
        screenshot(page, f"persisted-question-{mode}-{locale}.png")
