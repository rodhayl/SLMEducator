"""Real Chromium React journeys against a disposable loopback application.

The provider is an explicit deterministic stub. Browser execution is a separate
acceptance gate from collection, DOM tests, native Windows and real-model use.
"""

import os
import re
import secrets

import pytest
from playwright.sync_api import expect

from tests.browser.support import (
    authenticated_status,
    export_import_course,
    login,
    screenshot,
    start_material,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def test_isolated_smoke_login_navigation_and_admin_status(live_page, browser_world):
    """Replace the former existing-port smoke/login/navigation checks safely."""
    page, world = live_page, browser_world
    page.goto(world.base_url + "/")
    expect(page).to_have_url(re.compile(r"/entrar\?return="))
    expect(page).to_have_title(re.compile("SLMEducator"))
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(
        page.get_by_text(re.compile("Ask your teacher|Pide a tu docente"))
    ).to_be_visible()
    assert (
        page.get_by_role("link", name=re.compile("Register|Registrarse")).count() == 0
    )
    login(page, world, "admin")
    navigation = page.get_by_role("navigation")
    for name in ("People", "Courses and materials", "Assessments", "Grading"):
        expect(navigation.get_by_role("link", name=name, exact=True)).to_be_visible()
    navigation.get_by_role("link", name="People", exact=True).click()
    expect(page.get_by_role("heading", name="People", exact=True)).to_be_visible()
    navigation.get_by_role("link", name="Account and settings", exact=True).click()
    expect(
        page.get_by_role("heading", name="Account and settings", exact=True)
    ).to_be_visible()
    navigation.get_by_role("link", name="Home", exact=True).click()
    expect(page).to_have_url(world.base_url + "/inicio")
    navigation.get_by_role("link", name="Application status", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text(
        "The application server responded."
    )
    assert authenticated_status(page, "/api/status") == 200


def test_teacher_roster_and_interface_preferences(live_page, browser_world):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.get_by_role("navigation").get_by_role(
        "link", name="My students", exact=True
    ).click()
    expect(page.get_by_role("main")).to_contain_text("learner_a")
    expect(page.get_by_role("main")).not_to_contain_text("learner_b")
    page.get_by_role("navigation").get_by_role(
        "link", name="Account and settings", exact=True
    ).click()
    page.get_by_role("link", name="Appearance and language", exact=True).click()
    main = page.get_by_role("main")
    page.get_by_label("Appearance", exact=True).select_option("light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    light_background = page.locator("body").evaluate(
        "node => getComputedStyle(node).backgroundColor"
    )
    main.get_by_label("Theme", exact=True).select_option("dark")
    main.get_by_label("Language", exact=True).select_option("en")
    with page.expect_response(
        lambda response: (
            response.url.endswith("/api/settings/app")
            and response.request.method == "POST"
        )
    ) as saved:
        main.get_by_role("button", name="Save changes", exact=True).click()
    assert saved.value.ok
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    dark_background = page.locator("body").evaluate(
        "node => getComputedStyle(node).backgroundColor"
    )
    assert dark_background != light_background
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_css("background-color", dark_background)
    screenshot(page, "teacher-en-dark.png")
    page.goto(world.base_url + "/ajustes/perfil")
    expect(main.get_by_label("First name", exact=True)).to_be_visible()
    expect(main).to_contain_text("No badges earned yet.")
    page.goto(world.base_url + "/ajustes/zona-horaria")
    expect(main).to_contain_text("Source: application default (UTC)")
    page.goto(world.base_url + "/ajustes/ia")
    main.get_by_label("Provider", exact=True).select_option("lm_studio")
    main.get_by_label("Model name", exact=True).fill("synthetic-browser-model")
    main.get_by_label("LM Studio reasoning override", exact=True).select_option("none")
    main.get_by_label("Maximum output tokens", exact=True).fill("4000")
    with page.expect_response(
        lambda response: (
            response.url.endswith("/api/settings/ai")
            and response.request.method == "POST"
        )
    ) as configured:
        main.get_by_role("button", name="Save changes", exact=True).click()
    assert configured.value.ok
    page.reload()
    expect(main.get_by_label("LM Studio reasoning override", exact=True)).to_have_value(
        "none"
    )
    expect(main.get_by_label("Maximum output tokens", exact=True)).to_have_value("4000")


def test_learner_notes_help_and_completion_are_real_ui_actions(
    live_page, browser_world
):
    page, world = live_page, browser_world
    login(page, world, "learner_a")
    expect(
        page.get_by_role("navigation").get_by_role("link", name="People", exact=True)
    ).to_have_count(0)
    first, plan = world.manifest["content_ids"][0], world.manifest["plan_id"]
    start_material(page, world, first, plan)
    expect(page.get_by_role("heading", level=1)).to_have_text(
        world.manifest["lesson_titles"][0]
    )
    page.get_by_role("button", name="Notes and annotations", exact=True).click()
    notes = page.get_by_label("My session notes", exact=True)
    notes.fill("Synthetic browser note, preserved through pause.")
    with page.expect_response(
        lambda response: (
            response.url.endswith("/notes") and response.request.method == "PATCH"
        )
    ) as saved:
        page.get_by_role("button", name="Save notes", exact=True).click()
    assert saved.value.ok
    page.get_by_role("button", name="Help", exact=True).click()
    page.get_by_label("What would you like help with?", exact=True).fill(
        "Give a synthetic hint"
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(
        page.get_by_role("log", name="Tutor suggestion", exact=True)
    ).to_contain_text("Synthetic browser-test hint")
    page.get_by_role("button", name="Back to reading", exact=True).click()
    expect(page.get_by_role("heading", level=1)).to_be_focused()
    page.get_by_role("button", name="Save and pause", exact=True).click()
    expect(page).to_have_url(f"{world.base_url}/cursos/{plan}")
    assert (
        first
        not in world.api(
            "GET", f"/api/study-plans/{plan}/my-progress", account="learner_a"
        ).json()["completed_content_ids"]
    )
    start_material(page, world, first, plan)
    page.get_by_role("button", name="Notes and annotations", exact=True).click()
    expect(notes).to_have_value("Synthetic browser note, preserved through pause.")
    page.get_by_role("button", name="Complete and continue", exact=True).click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Complete session", exact=True
    ).click()
    expect(page.get_by_role("heading", level=1)).to_have_text(
        world.manifest["lesson_titles"][1]
    )
    progress = world.api(
        "GET", f"/api/study-plans/{plan}/my-progress", account="learner_a"
    ).json()
    assert progress["completed_content_ids"].count(first) == 1
    screenshot(page, "learner-next-and-notes.png")


def test_portability_preview_download_and_teacher_roundtrip(
    live_page, browser_world, tmp_path
):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.goto(world.base_url + "/ajustes/datos")
    imported, _ = export_import_course(
        page, world.manifest["plan_id"], tmp_path / "synthetic-course.json"
    )
    assert imported != world.manifest["plan_id"]
    assert (
        world.api("GET", f"/api/study-plans/{imported}/workflow").json()["status"]
        == "draft"
    )
    screenshot(page, "teacher-imported-draft.png")


def test_keyboard_and_narrow_login_remain_usable(live_page, browser_world):
    page = live_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(browser_world.base_url + "/entrar")
    page.get_by_label(re.compile(r"^(Language|Idioma)$")).select_option("en")
    page.get_by_label("Username", exact=True).focus()
    page.keyboard.press("Tab")
    expect(page.get_by_label("Password", exact=True)).to_be_focused()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()
    screenshot(page, "login-narrow-keyboard.png")


def test_teacher_corrections_preserve_source_and_executable_practice(
    live_page, browser_world
):
    page, world = live_page, browser_world
    plan = world.api(
        "POST",
        "/api/study-plans/",
        json={
            "title": "Synthetic authoring phases",
            "phases": [
                {"name": "First editable phase", "content_ids": []},
                {"name": "Second editable phase", "content_ids": []},
            ],
        },
    ).json()
    receipt = {
        "source_usage": {
            "source_document_id": "synthetic",
            "source_characters": 50,
            "ranges": [{"start": 0, "end": 50}],
        }
    }
    lesson = world.api(
        "POST",
        "/api/content/",
        json={
            "title": "Synthetic editable lesson",
            "content_type": "lesson",
            "content_data": {
                "body": "Observed amount.",
                "objectives": ["Explain the observation"],
                "vocabulary": [
                    {"term": "Half", "definition": "Wrong definition to correct"}
                ],
                "generation": receipt,
            },
        },
    ).json()
    exercise = world.api(
        "POST",
        "/api/content/",
        json={
            "title": "Synthetic editable practice",
            "content_type": "exercise",
            "content_data": {
                "question": "Choose two",
                "type": "multiple_choice",
                "options": {"A": "One", "B": "Two"},
                "correct_answer": "B",
                "hints": ["Count groups", "Count both"],
                "explanation": "Two groups.",
            },
        },
    ).json()
    login(page, world, "teacher_a")
    page.goto(f"{world.base_url}/generar?plan_id={plan['id']}")
    page.get_by_label("Generation mode", exact=True).select_option("package")
    page.get_by_label(
        "Save each confirmed item to the selected course", exact=True
    ).check()
    phase = page.get_by_label("Course phase", exact=True)
    expect(phase).to_be_enabled()
    expect(phase.get_by_role("option")).to_have_text(
        ["First editable phase", "Second editable phase"]
    )
    phase.select_option("1")
    page.get_by_label("Grade or learning level", exact=True).fill("Adult beginner")
    expect(page.get_by_label("Grade or learning level", exact=True)).to_have_value(
        "Adult beginner"
    )
    page.get_by_role("link", name="Material library", exact=True).click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Discard changes and leave", exact=True
    ).click()
    page.goto(f"{world.base_url}/materiales/{lesson['id']}/editar")
    page.get_by_text("Learning objectives and supporting material", exact=True).click()
    expect(
        page.get_by_label("Learning objectives (one per line)", exact=True)
    ).to_have_value("Explain the observation")
    page.get_by_label("Definition 1", exact=True).fill("One of two equal parts")
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/content/{lesson['id']}")
            and response.request.method == "PUT"
        )
    ) as saved:
        page.get_by_role("button", name="Save draft", exact=True).click()
    assert saved.value.ok
    data = world.api("GET", f"/api/content/{lesson['id']}").json()["content_data"]
    assert data["generation"] == receipt
    assert data["vocabulary"] == [
        {"term": "Half", "definition": "One of two equal parts"}
    ]
    page.get_by_role("link", name="Read material", exact=True).click()
    expect(page.get_by_role("article")).to_contain_text("One of two equal parts")
    expect(page.get_by_role("article")).to_contain_text("50/50")
    page.goto(f"{world.base_url}/materiales/{exercise['id']}/editar")
    expect(page.get_by_label("Question", exact=True)).to_have_value("Choose two")
    expect(page.get_by_label("Correct answer", exact=True)).to_have_value("B")
    page.get_by_label("Question", exact=True).fill("Choose the count of two groups")
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/content/{exercise['id']}")
            and response.request.method == "PUT"
        )
    ) as corrected:
        page.get_by_role("button", name="Save draft", exact=True).click()
    assert corrected.value.ok
    data = world.api("GET", f"/api/content/{exercise['id']}").json()["content_data"]
    assert data["question"] == "Choose the count of two groups"
    assert data["options"] == {"A": "One", "B": "Two"} and data["correct_answer"] == "B"
    assert data["hints"] == ["Count groups", "Count both"]


def test_isolated_fixture_has_only_synthetic_course(browser_world):
    world = browser_world
    assert len(world.manifest["content_ids"]) == 3
    assert (
        world.api(
            "GET", f"/api/study-plans/{world.manifest['plan_id']}/workflow"
        ).json()["status"]
        == "published"
    )
    assert len(world.api("GET", "/api/study-plans/", account="learner_a").json()) == 1
    assert world.api("GET", "/api/study-plans/", account="learner_b").json() == []


def test_unavailable_profile_keeps_private_shell_closed_until_verification(
    live_page, browser_world
):
    page, world = live_page, browser_world
    login(page, world, "teacher_a")
    page.route(
        "**/api/auth/me",
        lambda route: route.fulfill(status=503, json={"detail": "Synthetic outage"}),
    )
    page.reload()
    expect(
        page.get_by_role("heading", name=re.compile("^(Welcome back|Sign in again)$"))
    ).to_be_visible()
    expect(page.get_by_role("navigation")).to_have_count(0)
    expect(page.get_by_role("main")).to_have_count(0)
    expect(page.get_by_role("alert")).to_be_visible()
    screenshot(page, "dashboard-profile-unavailable.png")
    page.unroute("**/api/auth/me")
    page.get_by_label("Username", exact=True).fill("teacher_a")
    page.get_by_label("Password", exact=True).fill(
        world.accounts["teacher_a"]["password"]
    )
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("navigation").get_by_role(
        "link", name="My students", exact=True
    ).click()
    expect(page.get_by_role("main")).to_contain_text("learner_a")


def test_admin_recovery_ui_revokes_sessions_and_preserves_isolation(
    live_page, browser_world
):
    import requests

    page, world = live_page, browser_world
    target = world.manifest["users"]["learner_b"]
    with requests.Session() as http:
        http.trust_env = False
        old = http.post(
            world.base_url + "/api/auth/login",
            data={
                "username": "learner_b",
                "password": world.accounts["learner_b"]["password"],
            },
            timeout=10,
        ).json()["access_token"]
        login(page, world, "teacher_b")
        page.get_by_role("navigation").get_by_role(
            "link", name="My students", exact=True
        ).click()
        expect(page.get_by_role("main")).to_contain_text("learner_b")
        expect(page.get_by_role("main")).not_to_contain_text("learner_a")
        assert (
            authenticated_status(
                page,
                f"/api/auth/users/{target}/status",
                "PATCH",
                {"active": False, "confirm": True},
            )
            == 403
        )
        login(page, world, "admin")
        page.goto(f"{world.base_url}/personas/{target}")
        expect(page.get_by_role("main")).to_contain_text("learner_b")
        page.get_by_role("button", name="Deactivate account", exact=True).click()
        page.get_by_role("dialog").get_by_role(
            "button", name="Deactivate account", exact=True
        ).click()
        expect(
            page.get_by_text(
                "Account status updated. Existing sessions were revoked.", exact=True
            )
        ).to_be_visible()
        assert (
            http.get(
                world.base_url + "/api/auth/me",
                headers={"Authorization": "Bearer " + old},
                timeout=10,
            ).status_code
            == 401
        )
        assert (
            http.post(
                world.base_url + "/api/auth/login",
                data={
                    "username": "learner_b",
                    "password": world.accounts["learner_b"]["password"],
                },
                timeout=10,
            ).status_code
            == 401
        )
        page.get_by_role("button", name="Activate account", exact=True).click()
        page.get_by_role("dialog").get_by_role(
            "button", name="Activate account", exact=True
        ).click()
        expect(
            page.get_by_role("button", name="Deactivate account", exact=True)
        ).to_be_visible()
        new_password = "SyntheticRecovery-" + secrets.token_urlsafe(16) + "A1!"
        page.get_by_text("Recover account access", exact=True).click()
        page.get_by_label("New password", exact=True).fill(new_password)
        page.get_by_label("Repeat new password", exact=True).fill(new_password)
        page.get_by_role("button", name="Reset password", exact=True).click()
        page.get_by_role("dialog").get_by_role(
            "button", name="Reset password", exact=True
        ).click()
        expect(
            page.get_by_text(
                "Password reset. Existing sessions were revoked.", exact=True
            )
        ).to_be_visible()
        assert (
            http.post(
                world.base_url + "/api/auth/login",
                data={"username": "learner_b", "password": new_password},
                timeout=10,
            ).status_code
            == 200
        )
        expect(page.get_by_label("New password", exact=True)).to_have_value("")
        world.accounts["learner_b"]["password"] = new_password
        screenshot(page, "admin-account-recovery.png")
