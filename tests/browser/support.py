"""Accessible React controls shared by the isolated browser acceptance suite."""

import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect


def login(page: Page, world: Any, account: str, locale: str = "en") -> None:
    """Sign in through the real form, signing out a preceding UI session first."""
    page.goto(world.base_url + "/entrar")
    username = page.get_by_label(re.compile(r"^(Username|Usuario)$"))
    sign_out = page.get_by_role(
        "button", name=re.compile(r"^(Sign out|Cerrar sesión)$")
    )
    expect(username.or_(sign_out).first).to_be_visible()
    if sign_out.is_visible():
        sign_out.click()
        page.get_by_role("dialog").get_by_role(
            "button",
            name=re.compile(
                r"^(Sign out and keep my drafts here|Salir y conservar mis borradores aquí)$"
            ),
        ).click()
    page.get_by_label(re.compile(r"^(Language|Idioma)$")).select_option(locale)
    username.fill(account)
    page.get_by_label(re.compile(r"^(Password|Contraseña)$")).fill(
        world.accounts[account]["password"]
    )
    page.get_by_role("button", name=re.compile(r"^(Sign in|Entrar)$")).click()
    expect(page).to_have_url(re.compile(r"/inicio$"))
    expect(page.get_by_role("main")).to_be_visible()
    expect(page.get_by_role("navigation")).to_be_visible()
    expect(page.locator("html")).to_have_attribute("lang", locale)


def screenshot(page: Page, name: str) -> None:
    """Save evidence only in the explicitly selected private artifact directory."""
    directory = Path(
        os.environ.get("SLM_BROWSER_ARTIFACTS", "/tmp/slm-browser-artifacts")
    )
    directory.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(directory / name), full_page=True)


def start_material(page: Page, world: Any, content_id: int, plan_id: int) -> None:
    """Open a GET-only preview and deliberately start or continue studying."""
    page.goto(f"{world.base_url}/materiales/{content_id}?plan_id={plan_id}")
    page.get_by_role(
        "button", name=re.compile(r"^(Start studying|Continue session)$")
    ).first.click()
    expect(page).to_have_url(re.compile(r"/estudio/\d+\?"))
    expect(page.get_by_role("article", name="Saved lesson version")).to_be_visible()


def export_import_course(
    page: Page, plan_id: int, destination: Path
) -> tuple[int, dict]:
    """Review, confirm, download and import a teacher package as a new draft."""
    page.get_by_label("Purpose", exact=True).select_option("teacher")
    page.get_by_label("Course", exact=True).select_option(str(plan_id))
    download_button = page.get_by_role(
        "button", name="Download selected export", exact=True
    )
    expect(download_button).to_be_disabled()
    page.get_by_role("button", name="Review preview", exact=True).click()
    expect(download_button).to_be_enabled()
    download_button.click()
    with page.expect_download() as download:
        page.get_by_role("dialog").get_by_role(
            "button", name="Download selected export", exact=True
        ).click()
    download.value.save_as(destination)
    package = json.loads(destination.read_text(encoding="utf-8"))
    assert package["version"] == 2 and package["audience"] == "teacher"
    page.get_by_label("Purpose", exact=True).select_option("import")
    page.get_by_label("Teacher JSON file", exact=True).set_input_files(destination)
    create = page.get_by_role("button", name="Create new draft", exact=True)
    expect(create).to_be_disabled()
    page.get_by_role("button", name="Validate import", exact=True).click()
    expect(create).to_be_enabled()
    create.click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Create new draft", exact=True
    ).click()
    opened = page.get_by_role("link", name="Open draft for review", exact=True)
    expect(opened).to_be_visible()
    match = re.fullmatch(r"/cursos/(\d+)/editar", opened.get_attribute("href") or "")
    assert match is not None
    return int(match[1]), package


def authenticated_status(
    page: Page, path: str, method: str = "GET", body: Any = None
) -> int:
    """Exercise backend authorization with the currently signed-in UI account."""
    return page.evaluate(
        """async ({path, method, body}) => {
            const response = await fetch(path, {method, headers: {
                Authorization: 'Bearer ' + localStorage.getItem('token'),
                'Content-Type': 'application/json'
            }, ...(body === null ? {} : {body: JSON.stringify(body)})});
            return response.status;
        }""",
        {"path": path, "method": method, "body": body},
    )
