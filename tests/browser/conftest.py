"""Explicit, isolated real-browser acceptance; never connect to an existing app."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]


class BrowserWorld(SimpleNamespace):
    """Keep ephemeral credentials out of test failure representations."""

    def __repr__(self) -> str:
        return "<isolated synthetic browser installation>"


@pytest.fixture(scope="module")
def browser_world(tmp_path_factory):
    if os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1":
        pytest.skip("Explicit real-browser acceptance is disabled")
    directory = tmp_path_factory.mktemp("browser-installation")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    logfile = (directory / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "tests/browser/local_server.py"),
            "--state-dir",
            str(directory),
            "--port",
            str(port),
        ],
        cwd=directory,
        stdout=logfile,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    client = requests.Session()
    client.trust_env = False
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail("Synthetic browser server exited before readiness")
            try:
                if client.get(base_url + "/api/status", timeout=0.5).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("Synthetic browser server did not become ready")
        manifest = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
        accounts = {record["username"]: record for record in manifest["credentials"]}
        tokens = {}
        for name, account in accounts.items():
            response = client.post(
                base_url + "/api/auth/login",
                data={"username": name, "password": account["password"]},
                timeout=10,
            )
            assert response.status_code == 200, f"Synthetic login failed: {name}"
            tokens[name] = response.json()["access_token"]

        def api(method, path, account="teacher_a", **kwargs):
            response = client.request(
                method,
                base_url + path,
                headers={"Authorization": "Bearer " + tokens[account]},
                timeout=15,
                **kwargs,
            )
            assert (
                response.status_code < 400
            ), f"Synthetic setup/check failed: {method} {path} {response.status_code}"
            return response

        api("POST", f"/api/assessments/{manifest['assessment_id']}/publish")
        for action in ("review", "publish"):
            api("POST", f"/api/study-plans/{manifest['plan_id']}/workflow", json={"action": action})
        api(
            "POST",
            f"/api/study-plans/{manifest['plan_id']}/assign",
            json={"student_ids": [manifest["users"]["learner_a"]]},
        )
        yield BrowserWorld(
            base_url=base_url, directory=directory, accounts=accounts, manifest=manifest, api=api
        )
    finally:
        client.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        logfile.close()


@pytest.fixture(scope="module")
def live_browser(browser_world):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.environ.get("SLM_BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["SLM_BROWSER_EXECUTABLE"]
        browser = playwright.chromium.launch(**options)
        yield browser
        browser.close()


@pytest.fixture
def live_page(live_browser, browser_world):
    context = live_browser.new_context(
        viewport={"width": 1280, "height": 900}, service_workers="block", accept_downloads=True
    )
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(browser_world.base_url + "/")
            else route.abort()
        ),
    )
    page = context.new_page()
    page.set_default_timeout(10000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    context.close()
    assert errors == [], "Unexpected browser JavaScript error: " + "; ".join(errors)
