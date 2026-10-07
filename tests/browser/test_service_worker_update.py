"""Actual v22 → production retirement lifecycle; never force activation/reload."""

import os

import pytest
from playwright.sync_api import expect

from tests.browser.support import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)

KNOWN_CACHES = {
    "slm-educator-v22-session-locale",
    "slm-educator-v22-session-locale-auth-validation",
}
RETAINED_CACHES = {"unrelated-application", "slm-educator-unknown-version"}


def test_v22_retirement_waits_for_last_dirty_tab_and_preserves_unowned_data(
    live_browser, browser_world
):
    """An existing root worker updates without replacing any open dirty page."""
    world = browser_world
    context = live_browser.new_context(service_workers="allow")
    page = context.new_page()
    page.set_default_timeout(15000)
    try:
        login(page, world, "teacher_a")
        page.evaluate("""async () => {
            await navigator.serviceWorker.register('/sw.js', {scope: '/', updateViaCache: 'none'});
            await navigator.serviceWorker.ready;
        }""")
        page.reload()  # Establish control before the dirty-edit/update scenario.
        page.wait_for_function(
            "navigator.serviceWorker.controller?.state === 'activated'"
        )
        assert (
            page.evaluate("navigator.serviceWorker.controller.scriptURL")
            == world.base_url + "/sw.js"
        )
        assert set(page.evaluate("caches.keys()")) == {
            "slm-educator-v22-session-locale-auth-validation"
        }
        # Seed the other recognized cache and unrelated caches after v22 activation:
        # its historic broad prune is not a promise made by the new retirement code.
        drafts = {
            "slm_draft_v1:999:course:designer:active": "foreign owner draft",
            "another-application-draft": "unrelated recovery text",
        }
        page.evaluate(
            """async ({names, drafts}) => {
            for (const name of names) {
                const cache = await caches.open(name);
                await cache.put('/acceptance-cache-witness', new Response('preserve:' + name));
            }
            for (const [key, value] of Object.entries(drafts)) localStorage.setItem(key, value);
        }""",
            {"names": sorted(KNOWN_CACHES | RETAINED_CACHES), "drafts": drafts},
        )
        page.goto(world.base_url + "/generar")
        page.get_by_label("Topic", exact=True).fill(
            "Unsaved synthetic work must stay in this tab"
        )
        page.get_by_role(
            "button", name="Keep generation setup on this device", exact=True
        ).click()
        expect(
            page.get_by_text(
                "Generation setup saved on this device, unencrypted. Temporary material previews are not included.",
                exact=True,
            )
        ).to_be_visible()
        page.wait_for_timeout(600)  # Let the documented 400 ms draft debounce settle.
        stored = page.evaluate(
            "Object.fromEntries(Object.entries(localStorage).filter(([key]) => key.includes('draft') || key.includes('draft_v1'))) "
        )
        assert any(
            key.startswith(f"slm_draft_v1:{world.manifest['users']['teacher_a']}:")
            for key in stored
        )
        page.evaluate(
            "window.acceptanceDocumentIdentity = crypto.randomUUID(); window.acceptanceControllerChanges = 0; navigator.serviceWorker.addEventListener('controllerchange', () => window.acceptanceControllerChanges++);"
        )
        identity = page.evaluate("window.acceptanceDocumentIdentity")
        second = context.new_page()
        second.goto(world.base_url + "/inicio")
        second.wait_for_function("navigator.serviceWorker.controller !== null")
        (world.directory / "serve-retirement-worker").write_text(
            "retirement", encoding="utf-8"
        )
        # Loading the React entry asks the recognized registration to update itself.
        # The dirty page is never reloaded and the test never posts skipWaiting.
        with context.expect_event("serviceworker") as worker_event:
            second.reload()
        retirement = worker_event.value
        page.wait_for_function(
            "navigator.serviceWorker.getRegistration('/').then(r => r?.waiting?.state === 'installed')"
        )
        assert retirement.url == world.base_url + "/sw.js"
        # Observe the lifecycle in the waiting worker, without changing its state.
        retirement.evaluate("""() => {
            self.acceptanceActivated = new Promise(resolve => self.addEventListener('activate', () => resolve(true), {once: true}));
        }""")
        for retained in (page, second):
            assert (
                set(retained.evaluate("caches.keys()"))
                == KNOWN_CACHES | RETAINED_CACHES
            )
        expect(page.get_by_label("Topic", exact=True)).to_have_value(
            "Unsaved synthetic work must stay in this tab"
        )
        assert page.evaluate("window.acceptanceDocumentIdentity") == identity
        assert page.evaluate("window.acceptanceControllerChanges") == 0
        second.close()
        # Closing another old client is insufficient while the dirty tab remains.
        page.wait_for_timeout(300)
        assert (
            page.evaluate(
                "navigator.serviceWorker.getRegistration('/').then(r => r.waiting.state)"
            )
            == "installed"
        )
        assert page.evaluate("window.acceptanceControllerChanges") == 0
        assert set(page.evaluate("caches.keys()")) == KNOWN_CACHES | RETAINED_CACHES
        expect(page.get_by_label("Topic", exact=True)).to_have_value(
            "Unsaved synthetic work must stay in this tab"
        )
        screenshot(page, "worker-retirement-dirty-tab-preserved.png")
        page.close(run_before_unload=False)
        # No document in scope is opened until normal last-client activation fires.
        assert (
            retirement.evaluate(
                "Promise.race([self.acceptanceActivated, new Promise((_, reject) => setTimeout(() => reject(new Error('Normal worker activation did not occur')), 15000))])"
            )
            is True
        )
        page = context.new_page()
        page.goto(world.base_url + "/entrar")
        page.wait_for_function(
            "navigator.serviceWorker.getRegistrations().then(items => items.length === 0)"
        )
        page.wait_for_function(
            "caches.keys().then(keys => !keys.some(key => ['slm-educator-v22-session-locale', 'slm-educator-v22-session-locale-auth-validation'].includes(key)))"
        )
        assert set(page.evaluate("caches.keys()")) == RETAINED_CACHES
        for name in RETAINED_CACHES:
            assert (
                page.evaluate(
                    "async name => (await (await caches.open(name)).match('/acceptance-cache-witness')).text()",
                    name,
                )
                == "preserve:" + name
            )
        assert (
            page.evaluate(
                "keys => Object.fromEntries(keys.map(key => [key, localStorage.getItem(key)]))",
                list(stored),
            )
            == stored
        )
        page.reload()
        assert page.evaluate("navigator.serviceWorker.controller") is None
        assert (
            page.evaluate(
                "navigator.serviceWorker.getRegistrations().then(items => items.length)"
            )
            == 0
        )
    finally:
        context.close()


def test_fresh_origin_never_registers_worker_or_caches_assets(
    live_browser, browser_world
):
    """A fresh profile uses network React delivery and registers no worker."""
    context = live_browser.new_context(service_workers="allow")
    page = context.new_page()
    try:
        page.goto(browser_world.base_url + "/entrar")
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        assert (
            page.evaluate(
                "navigator.serviceWorker.getRegistrations().then(items => items.length)"
            )
            == 0
        )
        assert page.evaluate("navigator.serviceWorker.controller") is None
        assert page.evaluate("caches.keys()") == []
        context.set_offline(True)
        assert page.evaluate(
            "fetch('/api/status', {cache:'no-store'}).then(() => false).catch(() => true)"
        )
        context.set_offline(False)
        assert (
            page.evaluate(
                "fetch('/api/status', {cache:'no-store'}).then(response => response.status)"
            )
            == 200
        )
        page.reload()
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        assert (
            page.evaluate(
                "navigator.serviceWorker.getRegistrations().then(items => items.length)"
            )
            == 0
        )
    finally:
        context.close()
