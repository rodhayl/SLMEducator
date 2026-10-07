"""Measure actual Chromium tab zoom through its browser API, not CSS scaling."""

import json
import os

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.browser.support import login

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)


def test_native_200_percent_zoom_keeps_modes_keyboard_and_reflow(
    browser_world, tmp_path
):
    extension = tmp_path / "zoom-extension"
    extension.mkdir()
    (extension / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 3,
                "name": "Synthetic tab zoom measurement",
                "version": "1.0",
                "permissions": ["tabs"],
                "background": {"service_worker": "background.js"},
            }
        ),
        encoding="utf-8",
    )
    (extension / "background.js").write_text(
        "chrome.runtime.onInstalled.addListener(() => {});", encoding="utf-8"
    )
    with sync_playwright() as playwright:
        # Unpacked extension lives only in this disposable Chromium test profile.
        context = playwright.chromium.launch_persistent_context(
            str(tmp_path / "profile"),
            channel="chromium",
            headless=False,
            viewport={"width": 1280, "height": 900},
            service_workers="block",
            args=[
                f"--disable-extensions-except={extension}",
                f"--load-extension={extension}",
            ],
        )
        try:
            worker = (
                context.service_workers[0]
                if context.service_workers
                else context.wait_for_event("serviceworker")
            )
            page = context.pages[0]
            login(page, browser_world, "teacher_a")
            before = page.evaluate("({dpr:devicePixelRatio,width:innerWidth})")
            zoom = worker.evaluate(
                """async url => {
                const [tab] = await chrome.tabs.query({url:url+'/*'});
                await chrome.tabs.setZoom(tab.id, 2); return chrome.tabs.getZoom(tab.id);
            }""",
                browser_world.base_url,
            )
            assert zoom == 2
            page.wait_for_function(
                "factor => devicePixelRatio === factor", arg=before["dpr"] * 2
            )
            assert page.evaluate("innerWidth") <= before["width"] / 2 + 1
            page.get_by_role("button", name="Open navigation", exact=True).click()
            drawer = page.get_by_role("dialog")
            expect(drawer.get_by_role("navigation")).to_be_visible()
            drawer.get_by_role("link", name="Courses and materials", exact=True).click()
            expect(drawer).not_to_be_visible()
            page.goto(browser_world.base_url + "/generar")
            page.get_by_label("Topic", exact=True).fill("Retained synthetic topic")
            page.get_by_label("Generation mode", exact=True).select_option("package")
            page.get_by_label("Assessment", exact=True).check()
            page.get_by_label("Assessment question types", exact=True).select_option(
                "short_answer"
            )
            for mode in ["exercise", "plan", "lesson", "package"]:
                page.get_by_label("Generation mode", exact=True).select_option(mode)
                expect(
                    page.get_by_role("button", name="Generate with AI", exact=True)
                ).to_be_visible()
            expect(page.get_by_label("Topic", exact=True)).to_have_value(
                "Retained synthetic topic"
            )
            expect(
                page.get_by_label("Assessment question types", exact=True)
            ).to_have_value("short_answer")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement !== document.body")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "native-200.png"), full_page=True)
        finally:
            context.close()
