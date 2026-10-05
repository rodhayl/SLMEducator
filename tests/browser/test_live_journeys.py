"""Real Chromium role journeys against a disposable loopback HTTP application.

The provider is an explicit deterministic stub. These checks do not establish
native Windows, screen-reader or real-model educational acceptance.
"""

import json
import os
from pathlib import Path
import re
import secrets

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
    expect(page.locator("#dashboard-app")).to_have_attribute("aria-busy", "false")
    expect(page.locator("#dashboard-app")).not_to_have_attribute("inert", "")


def screenshot(page, name):
    directory = Path(os.environ.get("SLM_BROWSER_ARTIFACTS", "/tmp/slm-browser-artifacts"))
    directory.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0, 0)")
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
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_have_class(re.compile("theme-dark"))
    expect(page.locator("body")).to_have_css("background-color", "rgb(17, 24, 39)")
    expect(page.locator(".sidebar")).to_have_css("background-color", "rgb(17, 24, 39)")
    expect(page.locator('label[for="profile-grade-level"]')).to_have_text("Grade Level")
    expect(page.locator("#profile-badges-list")).to_contain_text("Complete activities to earn badges!")
    expect(page.locator("#timezone-status")).to_have_text("UTC is the explicit default. Choose and save your timezone.")
    screenshot(page, "teacher-en-dark.png")
    page.locator('#settings-tabs [data-settings-tab="ai"]').click()
    page.locator('#ai-provider').select_option('lm_studio')
    page.locator('#ai-model').fill('synthetic-browser-model')
    page.locator('#settings-ai-form details summary').click()
    page.locator('#ai-reasoning-effort').select_option('none')
    page.locator('#ai-max-tokens').fill('4000')
    with page.expect_response(lambda response: '/api/settings/ai' in response.url and response.request.method == 'POST') as configured:
        page.locator('#save-ai-config').click()
    assert configured.value.ok
    page.reload()
    page.locator('[data-view="settings"]').click()
    page.locator('#settings-tabs [data-settings-tab="ai"]').click()
    expect(page.locator('#ai-reasoning-effort')).to_have_value('none')
    expect(page.locator('#ai-max-tokens')).to_have_value('4000')


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


def test_teacher_corrections_preserve_source_and_executable_practice(live_page, browser_world):
    page, world = live_page, browser_world
    receipt = {"source_usage": {"source_document_id": "synthetic", "source_characters": 50,
                               "ranges": [{"start": 0, "end": 50}]}}
    lesson = world.api("POST", "/api/content/", json={"title": "Synthetic editable lesson", "content_type": "lesson",
        "content_data": {"body": "Observed amount.", "objectives": ["Explain the observation"],
                         "vocabulary": [{"term": "Half", "definition": "Wrong definition to correct"}], "generation": receipt}}).json()
    exercise = world.api("POST", "/api/content/", json={"title": "Synthetic editable practice", "content_type": "exercise",
        "content_data": {"question": "Choose two", "type": "multiple_choice", "options": {"A": "One", "B": "Two"},
                         "correct_answer": "B", "hints": ["Count groups", "Count both"], "explanation": "Two groups."}}).json()
    login(page, world, "teacher_a")
    page.evaluate("id => window.editContent(id)", lesson["id"])
    body = page.locator("#edit-content-body")
    assert "Explain the observation" in body.input_value()
    assert "Wrong definition to correct" in body.input_value()
    body.fill(body.input_value().replace("Wrong definition to correct", "One of two equal parts"))
    with page.expect_response(lambda response: f'/api/content/{lesson["id"]}' in response.url and response.request.method == "PUT") as saved:
        page.locator("#save-content-edit").click()
    assert saved.value.ok
    expect(page.locator("#contentEditModal")).to_be_hidden()
    data = world.api("GET", f'/api/content/{lesson["id"]}').json()["content_data"]
    assert data["generation"] == receipt and "One of two equal parts" in data["content"]
    page.evaluate("id => window.viewContent(id)", lesson["id"])
    expect(page.locator("#content-view-body")).to_contain_text("One of two equal parts")
    expect(page.locator("#content-view-body [data-generation-notice]")).to_contain_text("50/50")
    page.locator("#contentViewModal .btn-close").click()
    expect(page.locator("#contentViewModal")).to_be_hidden()
    page.evaluate("id => window.editContent(id)", exercise["id"])
    expect(page.locator("#edit-exercise-question")).to_have_value("Choose two")
    expect(page.locator("#edit-exercise-correct-choice")).to_have_value("1")
    page.locator("#edit-exercise-question").fill("Choose the count of two groups")
    with page.expect_response(lambda response: f'/api/content/{exercise["id"]}' in response.url and response.request.method == "PUT") as corrected:
        page.locator("#save-content-edit").click()
    assert corrected.value.ok
    data = world.api("GET", f'/api/content/{exercise["id"]}').json()["content_data"]
    assert data["question"] == "Choose the count of two groups"
    assert data["options"] == ["One", "Two"] and data["correct_answer"] == "Two"
    assert data["hints"] == ["Count groups", "Count both"]


def test_isolated_fixture_has_only_synthetic_course(browser_world):
    world = browser_world
    assert len(world.manifest["content_ids"]) == 3
    assert (
        world.api("GET", f"/api/study-plans/{world.manifest['plan_id']}/workflow").json()["status"]
        == "published"
    )
    assert len(world.api("GET", "/api/study-plans/", account="learner_a").json()) == 1
    assert world.api("GET", "/api/study-plans/", account="learner_b").json() == []


def test_unavailable_profile_keeps_dashboard_closed_until_retry(live_page, browser_world):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.route("**/api/auth/me", lambda route: route.fulfill(status=503, json={"detail": "Synthetic outage"}))
    page.reload()
    expect(page.locator("#dashboard-loading")).to_have_attribute("role", "alert")
    expect(page.locator("#dashboard-loading")).to_contain_text(re.compile("could not start|No se pudo iniciar"))
    expect(page.locator("#dashboard-app")).to_have_attribute("inert", "")
    expect(page.locator("#dashboard-app")).to_have_attribute("aria-busy", "false")
    screenshot(page, "dashboard-profile-unavailable.png")
    page.unroute("**/api/auth/me")
    page.locator("#dashboard-loading button").click()
    expect(page.locator("#dashboard-loading")).to_be_hidden()
    expect(page.locator("#dashboard-app")).not_to_have_attribute("inert", "")
    page.locator('[data-view="students"]').click()
    expect(page.locator("#student-list")).to_contain_text("learner_a")


def test_admin_recovery_ui_revokes_sessions_and_preserves_isolation(live_page, browser_world):
    import requests

    page, world = live_page, browser_world
    # The second learner leaves the original teacher/learner journey intact.
    target = world.manifest['users']['learner_b']
    with requests.Session() as http:
        http.trust_env = False
        old = http.post(world.base_url + '/api/auth/login', data={
            'username': 'learner_b', 'password': world.accounts['learner_b']['password']}).json()['access_token']
        login(page, world, 'teacher_b')
        page.locator('[data-view="students"]').click()
        expect(page.locator('#student-list')).to_contain_text('learner_b')
        expect(page.locator('#student-list')).not_to_contain_text('learner_a')
        denied = page.evaluate("""async id => (await fetch('/api/auth/users/'+id+'/status', {
            method:'PATCH',headers:{Authorization:'Bearer '+localStorage.getItem('token'),'Content-Type':'application/json'},
            body:JSON.stringify({active:false,confirm:true})})).status""", target)
        assert denied == 403
        login(page, world, 'admin')
        page.locator('[data-view="students"]').click()
        page.locator(f'#student-list button[onclick="manageAccount({target}, \'student\')"]').click()
        expect(page.locator('#account-identity')).to_contain_text('@learner_b')
        page.locator('#account-status-btn').click()
        page.locator('button[id^="confirm-modal-"][id$="-confirm"]:visible').click()
        expect(page.locator('#account-operation-status')).to_contain_text(re.compile('saved|guardado',re.I))
        assert http.get(world.base_url + '/api/auth/me',headers={'Authorization':'Bearer '+old}).status_code == 401
        assert http.post(world.base_url + '/api/auth/login',data={
            'username':'learner_b','password':world.accounts['learner_b']['password']}).status_code == 401
        page.locator('#account-status-btn').click()
        page.locator('button[id^="confirm-modal-"][id$="-confirm"]:visible').click()
        expect(page.locator('#account-status-btn')).to_contain_text(re.compile('Deactivate|Desactivar',re.I))
        new_password = 'SyntheticRecovery-' + secrets.token_urlsafe(16) + 'A1!'
        page.locator('#account-new-password').fill(new_password)
        page.locator('#account-confirm-password').fill(new_password)
        page.locator('#account-reset-btn').click()
        page.locator('button[id^="confirm-modal-"][id$="-confirm"]:visible').click()
        expect(page.locator('#account-operation-status')).to_contain_text(re.compile('reset|restablecida',re.I))
        assert http.post(world.base_url+'/api/auth/login',data={'username':'learner_b','password':new_password}).status_code == 200
        expect(page.locator('#account-new-password')).to_have_value('')
        world.accounts['learner_b']['password'] = new_password
        screenshot(page, 'admin-account-recovery.png')
