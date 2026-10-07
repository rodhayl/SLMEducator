"""EN/ES React acceptance through browser, real API and synthetic provider parser."""

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
    "en": {
        "tutor": "Tutor and questions",
        "conversation": "Tutor conversation",
        "prompt": "What would you like help with?",
        "send": "Ask tutor",
        "questions": "My questions",
        "question": "My question",
        "ask": "Ask AI for a suggestion",
        "unverified": "AI suggestion, not verified.",
        "failed": "No usable suggestion was confirmed.",
        "start": "Start studying",
        "continue": "Continue session",
    },
    "es": {
        "tutor": "Tutor y preguntas",
        "conversation": "Conversación con el tutor",
        "prompt": "¿En qué necesitas ayuda?",
        "send": "Preguntar al tutor",
        "questions": "Mis preguntas",
        "question": "Mi pregunta",
        "ask": "Pedir una sugerencia a la IA",
        "unverified": "Sugerencia de IA sin verificar.",
        "failed": "No se confirmó una sugerencia utilizable.",
        "start": "Comenzar a estudiar",
        "continue": "Continuar sesión",
    },
}


@pytest.mark.parametrize("locale", ["en", "es"])
def test_independent_learner_best_effort(live_page, browser_world, locale):
    """Assigned reading, tutor and private questions need no teacher session."""
    page, world, labels = live_page, browser_world, LABELS[locale]
    login(page, world, "learner_a", locale)
    expect(
        page.get_by_role("navigation").get_by_role(
            "link", name=re.compile("^(People|Personas)$")
        )
    ).to_have_count(0)
    first, plan = world.manifest["content_ids"][0], world.manifest["plan_id"]
    page.goto(f"{world.base_url}/materiales/{first}?plan_id={plan}")
    expect(page.get_by_role("heading", level=1)).to_have_text(
        world.manifest["lesson_titles"][0]
    )
    expect(page.get_by_role("article")).to_be_visible()
    page.get_by_role("navigation").get_by_role(
        "link", name=labels["tutor"], exact=True
    ).click()
    conversation = page.get_by_role("region", name=labels["conversation"], exact=True)
    question = conversation.get_by_label(labels["prompt"], exact=True)
    send = conversation.get_by_role("button", name=labels["send"], exact=True)
    calls = []
    page.on(
        "request",
        lambda request: (
            calls.append(request.url)
            if request.url.endswith("/api/ai/chat") and request.method == "POST"
            else None
        ),
    )
    for mode in ("structured", "prose"):
        question.fill(f"[acceptance:{mode}] Compare parts")
        with page.expect_response(
            lambda response: response.url.endswith("/api/ai/chat")
        ) as response:
            send.click()
        data = response.value.json()
        assert (
            data["status"] == "suggestion" and data["receipt"]["status"] == "completed"
        )
        log = conversation.get_by_role("log", name=labels["conversation"], exact=True)
        expect(log).to_contain_text(f"Synthetic {mode}")
        expect(log).to_contain_text(labels["unverified"])
        assert log.locator("img, script").count() == 0
        assert page.evaluate("window.acceptanceUnsafe") is None
        expect(question).to_have_value("")
    for mode, status in (("format", "invalid_response"), ("provider", "unavailable")):
        text = f"[acceptance:{mode}] Keep this question"
        question.fill(text)
        ids = []
        for _ in range(2):
            before = len(calls)
            with page.expect_response(
                lambda response: response.url.endswith("/api/ai/chat")
            ) as response:
                send.click()
            data = response.value.json()
            assert data["status"] == status and data["receipt"]["status"] == "failed"
            ids.append(data["receipt"]["request_id"])
            expect(conversation.get_by_role("status")).to_contain_text(labels["failed"])
            expect(question).to_have_value(text)
            expect(send).to_be_enabled()
            page.wait_for_timeout(350)
            assert len(calls) == before + 1
        assert ids[0] != ids[1]
        screenshot(page, f"best-effort-tutor-{mode}-{locale}.png")
    # Switching the two panes preserves typed questions without creating a saved record.
    page.get_by_role("button", name=labels["questions"], exact=True).click()
    questions = page.get_by_role("region", name=labels["questions"], exact=True)
    qa = questions.get_by_label(labels["question"], exact=True)
    ask = questions.get_by_role("button", name=labels["ask"], exact=True)
    qa_calls = []
    page.on(
        "request",
        lambda request: (
            qa_calls.append(request.url)
            if request.url.endswith("/api/ai/answer-question")
            and request.method == "POST"
            else None
        ),
    )
    for mode in ("structured", "prose", "format", "provider"):
        text = f"[acceptance:{mode}] Independent Q&A"
        qa.fill(text)
        before = len(qa_calls)
        with page.expect_response(
            lambda response: response.url.endswith("/api/ai/answer-question")
        ) as response:
            ask.click()
        data = response.value.json()
        assert data["success"] is (mode in ("structured", "prose"))
        assert data["receipt"]["status"] == (
            "completed" if data["success"] else "failed"
        )
        if data["success"]:
            expect(questions).to_contain_text(labels["unverified"])
            expect(questions).to_contain_text(f"Synthetic {mode}")
        else:
            expect(
                questions.get_by_role("status").filter(has_text=labels["failed"])
            ).to_be_visible()
            expect(
                questions.get_by_role(
                    "heading", name=re.compile("^(AI suggestion|Sugerencia de IA)$")
                )
            ).to_have_count(0)
        expect(qa).to_have_value(text)
        assert questions.locator("img, script").count() == 0
        assert page.evaluate("window.acceptanceUnsafe") is None
        page.wait_for_timeout(350)
        assert len(qa_calls) == before + 1
        if not data["success"]:
            with page.expect_response(
                lambda response: response.url.endswith("/api/ai/answer-question")
            ) as retry:
                ask.click()
            assert retry.value.json()["success"] is False
            expect(qa).to_have_value(text)
            assert len(qa_calls) == before + 2
    screenshot(page, f"best-effort-qa-{locale}.png")
