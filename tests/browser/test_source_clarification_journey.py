"""Persist and render synthetic source clarification through React and HTTP."""

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.browser.support import (
    export_import_course,
    login,
    screenshot,
    start_material,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def save_and_reopen(page: Page, world: Any, lesson_id: int, question: str) -> None:
    """Edit with real section controls and reopen the saved visible material."""
    page.goto(f"{world.base_url}/materiales/{lesson_id}")
    expect(page.get_by_role("article")).to_contain_text(question)
    page.goto(f"{world.base_url}/materiales/{lesson_id}/editar")
    texts = page.get_by_label(re.compile(r"^Section \d+ content$"))
    assert any(
        question in value
        for value in texts.evaluate_all("nodes => nodes.map(node => node.value)")
    )
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/content/{lesson_id}")
            and response.request.method == "PUT"
        )
    ) as saved:
        page.get_by_role("button", name="Save draft", exact=True).click()
    assert saved.value.ok
    page.get_by_role("link", name="Read material", exact=True).click()
    page.reload()
    expect(page.get_by_role("article")).to_contain_text(question)
    screenshot(page, "source-clarification-saved-viewer.png")


def test_clarification_survives_editor_reload_class_and_export(
    live_page: Page, browser_world: Any, tmp_path: Path
) -> None:
    """Keep the question visible through authoring, studying and package import."""
    page, world = live_page, browser_world
    fixture = json.loads(
        (
            Path(__file__).parents[1] / "fixtures/source_clarification_render.json"
        ).read_text(encoding="utf-8")
    )["cases"][0]
    question = fixture["question"]
    lesson = world.api(
        "POST",
        "/api/content/",
        json={
            "title": "Synthetic source clarification",
            "content_type": "lesson",
            "content_data": fixture["learner_output"],
        },
    ).json()
    plan = world.api(
        "POST",
        "/api/study-plans/",
        json={
            "title": "Synthetic clarification journey",
            "phases": [{"name": "Records", "content_ids": [lesson["id"]]}],
        },
    ).json()
    login(page, world, "teacher_a")
    save_and_reopen(page, world, lesson["id"], question)
    for action in ("review", "publish"):
        world.api(
            "POST", f"/api/study-plans/{plan['id']}/workflow", json={"action": action}
        )
    world.api(
        "POST",
        f"/api/study-plans/{plan['id']}/assign",
        json={"student_ids": [world.manifest["users"]["learner_a"]]},
    )
    login(page, world, "learner_a")
    start_material(page, world, lesson["id"], plan["id"])
    expect(page.get_by_role("article", name="Saved lesson version")).to_contain_text(
        question
    )
    page.reload()
    expect(page.get_by_role("article", name="Saved lesson version")).to_contain_text(
        question
    )
    page.get_by_role("button", name="Course index", exact=True).click()
    expect(page.get_by_text("0 of 1 materials completed", exact=True)).to_be_visible()
    expect(
        page.get_by_role("button", name="Synthetic source clarification", exact=True)
    ).to_have_attribute("aria-current", "step")
    screenshot(page, "source-clarification-learner-reloaded.png")
    login(page, world, "teacher_a")
    page.goto(world.base_url + "/ajustes/datos")
    imported, package = export_import_course(
        page, plan["id"], tmp_path / "synthetic-clarification.json"
    )
    assert question in json.dumps(package, ensure_ascii=False)
    assert imported != plan["id"]
    tree = world.api("GET", f"/api/study-plans/{imported}/tree").json()
    page.goto(f"{world.base_url}/materiales/{tree['contents'][0]['id']}")
    expect(page.get_by_role("article")).to_contain_text(question)
    screenshot(page, "source-clarification-imported-question.png")
