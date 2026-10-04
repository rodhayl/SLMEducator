"""Real Chromium role journeys against a disposable loopback HTTP application.

The provider is an explicit deterministic stub. These checks do not establish
native Windows, screen-reader or real-model educational acceptance.
"""

import json
import os
from pathlib import Path
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def login(page, world, account):
    page.goto(world.base_url + "/login.html")
    page.locator("#username").fill(account)
    page.locator("#password").fill(world.accounts[account]["password"])
    page.locator("#login-form button[type=submit]").click()
    expect(page).to_have_url(re.compile(r"/dashboard\.html"))
    expect(page.locator("#user-name-display")).to_be_visible()


def screenshot(page, name):
    directory = Path(os.environ.get("SLM_BROWSER_ARTIFACTS", "/tmp/slm-browser-artifacts"))
    directory.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(directory / name), full_page=True)


def test_teacher_roster_and_interface_preferences(live_page, browser_world):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.locator('[data-view="students"]').click()
    expect(page.locator("#student-list")).to_contain_text("learner_a")
    expect(page.locator("#student-list")).not_to_contain_text("learner_b")
    page.locator('[data-view="settings"]').click()
    page.locator('#settings-tabs [data-settings-tab="appearance"]').click()
    page.locator("#app-theme").select_option("dark")
    page.locator("#app-lang").select_option("en")
    with page.expect_response(
        lambda response: "/api/settings/app" in response.url and response.request.method == "POST"
    ) as saved:
        page.locator("#settings-app-form button").click()
    assert saved.value.ok
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.locator('button[id^="confirm-modal-"][id$="-confirm"]').click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator("body")).to_have_class(re.compile("theme-dark"))
    page.reload()
    expect(page.locator("body")).to_have_class(re.compile("theme-dark"))
    screenshot(page, "teacher-en-dark.png")


def test_learner_notes_help_and_completion_are_real_ui_actions(live_page, browser_world):
    page, world = live_page, browser_world
    login(page, world, "learner_a")
    expect(page.locator("#nav-create")).not_to_be_visible()
    first = world.manifest["content_ids"][0]
    plan = world.manifest["plan_id"]
    page.goto(f"{world.base_url}/session_player.html?content_id={first}&plan_id={plan}")
    expect(page.locator("#session-content-title")).to_contain_text(
        world.manifest["lesson_titles"][0]
    )
    notes = page.locator("#session-notes")
    notes.fill("Synthetic browser note, preserved through pause.")
    with page.expect_response(
        lambda response: "/notes" in response.url and response.request.method == "PATCH"
    ) as saved:
        page.locator('[onclick="retryNotesSave()"]').click()
    assert saved.value.ok
    page.locator('#session-help-host [data-i18n="help_panel.tutor"]').click()
    expect(page.locator('[id$="-question"]')).to_be_enabled()
    page.locator('[id$="-question"]').fill("Give a synthetic hint")
    page.locator('#session-help-host [data-i18n="help_panel.send"]').click()
    expect(page.locator('#session-help-host [role="log"]')).to_contain_text(
        "Synthetic browser-test hint"
    )
    page.locator('#session-help-host [data-i18n="help_panel.close"]').click()
    expect(page.locator("#session-help-host section")).to_be_hidden()
    page.locator('[onclick="pauseSession()"]').click()
    expect(page).to_have_url(re.compile(r"/dashboard\.html"))
    progress = world.api("GET", f"/api/study-plans/{plan}/my-progress", account="learner_a").json()
    assert first not in progress["completed_content_ids"]
    page.goto(f"{world.base_url}/session_player.html?content_id={first}&plan_id={plan}")
    expect(notes).to_have_value("Synthetic browser note, preserved through pause.")
    page.locator("#next-content-btn").click()
    expect(page.locator("#session-content-title")).to_contain_text(
        world.manifest["lesson_titles"][1]
    )
    progress = world.api("GET", f"/api/study-plans/{plan}/my-progress", account="learner_a").json()
    assert progress["completed_content_ids"].count(first) == 1
    screenshot(page, "learner-next-and-notes.png")


def test_portability_preview_download_and_teacher_roundtrip(live_page, browser_world, tmp_path):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.goto(world.base_url + "/portability.html")
    page.locator('[data-portability-purpose="teacher"]').click()
    page.locator("#export-plan").select_option(str(world.manifest["plan_id"]))
    page.locator("#export-audience").select_option("teacher")
    expect(page.locator("#download-export")).to_be_disabled()
    page.locator("#preview-export").click()
    expect(page.locator("#download-export")).to_be_enabled()
    with page.expect_download() as download:
        page.locator("#download-export").click()
    destination = tmp_path / "synthetic-course.json"
    download.value.save_as(destination)
    package = json.loads(destination.read_text(encoding="utf-8"))
    assert package["version"] == 2 and package["audience"] == "teacher"
    page.locator('[data-portability-purpose="import"]').click()
    expect(page.locator("#import-section")).to_be_visible()
    page.locator("#import-file").set_input_files(destination)
    expect(page.locator("#confirm-import")).to_be_disabled()
    page.locator("#preview-import").click()
    expect(page.locator("#confirm-import")).to_be_enabled()
    page.locator("#confirm-import").click()
    expect(page.locator("#import-result a")).to_be_visible()
    imported = int(page.locator("#import-result a").get_attribute("href").split("id=")[1])
    assert imported != world.manifest["plan_id"]
    assert world.api("GET", f"/api/study-plans/{imported}/workflow").json()["status"] == "draft"
    screenshot(page, "teacher-imported-draft.png")


def test_keyboard_and_narrow_login_remain_usable(live_page, browser_world):
    page = live_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(browser_world.base_url + "/login.html")
    page.locator("#username").focus()
    page.keyboard.press("Tab")
    expect(page.locator("#password")).to_be_focused()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    expect(page.locator('#login-form button[type="submit"]')).to_be_visible()
    screenshot(page, "login-narrow-keyboard.png")


def test_isolated_fixture_has_only_synthetic_course(browser_world):
    world = browser_world
    assert len(world.manifest["content_ids"]) == 3
    assert (
        world.api("GET", f"/api/study-plans/{world.manifest['plan_id']}/workflow").json()["status"]
        == "published"
    )
    assert len(world.api("GET", "/api/study-plans/", account="learner_a").json()) == 1
    assert world.api("GET", "/api/study-plans/", account="learner_b").json() == []
