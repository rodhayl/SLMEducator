"""Persist and render synthetic v9 questions through real Chromium and HTTP."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from test_live_journeys import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def save_and_reopen(page: Page, lesson_id: int, question: str) -> None:
    """Edit the canonical body and reopen its saved visible representation."""
    page.evaluate("id => window.viewContent(id)", lesson_id)
    expect(page.locator("#content-view-body")).to_contain_text(question)
    page.locator("#contentViewModal .btn-close").click()
    page.evaluate("id => window.editContent(id)", lesson_id)
    assert question in page.locator("#edit-content-body").input_value()
    with page.expect_response(
        lambda response: f"/api/content/{lesson_id}" in response.url
        and response.request.method == "PUT"
    ) as saved:
        page.locator("#save-content-edit").click()
    assert saved.value.ok
    page.reload()
    page.wait_for_load_state("networkidle")
    page.evaluate("id => window.viewContent(id)", lesson_id)
    expect(page.locator("#content-view-body")).to_contain_text(question)
    screenshot(page, "v9-clarification-saved-viewer.png")


def export_question(page: Page, plan_id: int, question: str, destination: Path) -> int:
    """Download and import a teacher package containing the actual question."""
    page.locator('[data-portability-purpose="teacher"]').click()
    page.locator("#export-plan").select_option(str(plan_id))
    page.locator("#export-audience").select_option("teacher")
    page.locator("#preview-export").click()
    expect(page.locator("#download-export")).to_be_enabled()
    with page.expect_download() as download:
        page.locator("#download-export").click()
    download.value.save_as(destination)
    package = json.loads(destination.read_text(encoding="utf-8"))
    assert question in json.dumps(package, ensure_ascii=False)
    page.locator('[data-portability-purpose="import"]').click()
    page.locator("#import-file").set_input_files(destination)
    page.locator("#preview-import").click()
    expect(page.locator("#confirm-import")).to_be_enabled()
    page.locator("#confirm-import").click()
    expect(page.locator("#import-result a")).to_be_visible()
    href = page.locator("#import-result a").get_attribute("href")
    assert href is not None
    return int(href.split("id=")[1])


def test_clarification_survives_editor_reload_class_and_export(
    live_page: Page, browser_world: Any, tmp_path: Path
) -> None:
    """Keep the literal question visible through saved author and learner views."""
    page, world = live_page, browser_world
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/source_clarification_render.json")
        .read_text(encoding="utf-8")
    )["cases"][0]
    question = fixture["question"]
    lesson = world.api("POST", "/api/content/", json={
        "title": "Synthetic source clarification",
        "content_type": "lesson",
        "content_data": fixture["learner_output"],
    }).json()
    plan = world.api("POST", "/api/study-plans/", json={
        "title": "Synthetic clarification journey",
        "phases": [{"name": "Records", "content_ids": [lesson["id"]]}],
    }).json()
    login(page, world, "teacher_a")
    save_and_reopen(page, lesson["id"], question)
    for action in ("review", "publish"):
        world.api("POST", f'/api/study-plans/{plan["id"]}/workflow',
                  json={"action": action})
    world.api("POST", f'/api/study-plans/{plan["id"]}/assign',
              json={"student_ids": [world.manifest["users"]["learner_a"]]})
    login(page, world, "learner_a")
    page.goto(f'{world.base_url}/session_player.html?content_id={lesson["id"]}'
              f'&plan_id={plan["id"]}')
    expect(page.locator("#session-content-body")).to_contain_text(question)
    page.reload()
    expect(page.locator("#session-content-body")).to_contain_text(question)
    expect(page.locator("#completed-count")).to_have_text("0/1 completados")
    expect(page.locator("#content-position")).to_have_text("1 de 1")
    screenshot(page, "v9-clarification-learner-reloaded.png")
    login(page, world, "teacher_a")
    page.goto(world.base_url + "/portability.html")
    imported = export_question(page, plan["id"], question, tmp_path / "synthetic-clarification.json")
    assert imported != plan["id"]
    tree = world.api("GET", f"/api/study-plans/{imported}/tree").json()
    page.goto(world.base_url + "/dashboard.html")
    page.wait_for_load_state("networkidle")
    page.evaluate("id => window.viewContent(id)", tree["contents"][0]["id"])
    expect(page.locator("#content-view-body")).to_contain_text(question)
    screenshot(page, "v9-clarification-imported-question.png")
