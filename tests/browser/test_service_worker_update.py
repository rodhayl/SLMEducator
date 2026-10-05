"""Real Chromium service-worker installation, upgrade and offline recovery."""

import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
                               reason="Explicit isolated browser acceptance only")


def test_previous_worker_waits_for_tabs_and_offline_cache_is_scoped(live_browser, browser_world):
    context = live_browser.new_context(service_workers="allow")
    page = context.new_page()
    try:
        page.goto(browser_world.base_url + "/login.html")
        page.evaluate("""async () => {
            const r = await navigator.serviceWorker.register('/acceptance-sw.js', {scope:'/'});
            await navigator.serviceWorker.ready;
        }""")
        page.reload()
        page.wait_for_function("navigator.serviceWorker.controller !== null")
        assert page.evaluate("navigator.serviceWorker.controller.scriptURL.endsWith('/acceptance-sw.js')")
        assert page.evaluate("caches.keys()") == ['slm-educator-v14-practice-options']
        page.evaluate("""async () => {
            const r = await navigator.serviceWorker.getRegistration(); await r.update();
        }""")
        page.wait_for_function("navigator.serviceWorker.getRegistration().then(r => r.waiting !== null)")
        # A live previous-version page must not be claimed by the update.
        assert page.evaluate("caches.keys()") == ['slm-educator-v14-practice-options', 'slm-educator-v15-atomic-install']
        page.close()
        page = context.new_page()
        # Closing the last controlled client schedules activation asynchronously.
        # Keep this new page at about:blank until that transition can finish.
        page.wait_for_timeout(1000)
        page.goto(browser_world.base_url + "/login.html")
        page.wait_for_function("caches.keys().then(keys => !keys.includes('slm-educator-v14-practice-options'))")
        page.reload()
        page.wait_for_function("navigator.serviceWorker.controller !== null")
        page.wait_for_function("navigator.serviceWorker.controller.state === 'activated'")
        assert page.evaluate("navigator.serviceWorker.controller.scriptURL.endsWith('/acceptance-sw.js')")
        page.evaluate("""async () => {
            const foreign = await caches.open('unrelated-application');
            await foreign.put('/static/js/missing-asset.js', new Response('STALE FOREIGN VERSION'));
        }""")
        context.set_offline(True)
        missing = page.evaluate("""async () => {
            const r = await fetch('/static/js/missing-asset.js'); return {status:r.status,text:await r.text()};
        }""")
        assert missing['status'] == 503 and 'STALE' not in missing['text'], missing
        assert page.evaluate("fetch('/api/status').then(() => false).catch(() => true)")
        assert page.evaluate("fetch('/static/js/auth.js').then(r => r.ok)")
        context.set_offline(False)
        assert page.evaluate("fetch('/api/status').then(r => r.status)") == 200
        page.reload()
        assert page.locator('#login-form').is_visible()
    finally:
        context.close()
