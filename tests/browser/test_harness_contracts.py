"""Offline harness checks; these are not browser or native acceptance evidence."""

from hashlib import sha256
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.frontend_delivery import RETIREMENT_WORKER
from tests.browser.local_server import (
    LEGACY_WORKER_SHA256,
    ROOT,
    install_worker_fixture,
)
from tests.windows.exercise_native_login import verify_react_delivery


def test_frozen_v22_fixture_and_exact_retirement_switch(tmp_path: Path) -> None:
    """The fixture uses exact archived bytes and retires only when explicitly staged."""
    archived = (ROOT / "tests/browser/fixtures/service_worker_v22.js").read_bytes()
    assert sha256(archived).hexdigest() == LEGACY_WORKER_SHA256
    assert b"slm-educator-v22-session-locale-auth-validation" in archived
    app = FastAPI()

    @app.get("/sw.js")
    def worker() -> Response:
        return Response(RETIREMENT_WORKER, media_type="application/javascript")

    install_worker_fixture(app, tmp_path)
    with TestClient(app) as client:
        initial = client.get("/sw.js")
        assert initial.status_code == 200 and initial.content == archived
        assert initial.headers["service-worker-allowed"] == "/"
        assert initial.headers["cache-control"] == "no-store"
        assert client.get("/static/js/auth.js").status_code == 200
        assert client.get("/static/js/not-an-archived-asset.js").status_code == 404
        (tmp_path / "serve-retirement-worker").write_text(
            "retirement", encoding="utf-8"
        )
        retired = client.get("/sw.js")
        assert retired.status_code == 200 and retired.text == RETIREMENT_WORKER
        assert client.get("/static/js/auth.js").status_code == 404
        assert client.get("/acceptance-sw.js").status_code == 404


def test_native_login_checks_redirect_and_hashed_react_assets() -> None:
    """Exercise the native helper contract with local responses, never an EXE."""
    html = b'<html><div id="root"></div><script type="module" src="/assets/index-12345678.js"></script></html>'
    javascript = b"console.log('synthetic React asset witness')"
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/login.html":
            return httpx.Response(307, headers={"location": "/entrar"})
        content = html if request.url.path == "/entrar" else javascript
        return httpx.Response(
            200,
            content=content,
            headers={
                "content-type": "text/html"
                if content == html
                else "application/javascript",
                "x-content-type-options": "nosniff",
                "etag": '"' + sha256(content).hexdigest() + '"',
            },
        )

    with httpx.Client(
        base_url="http://127.0.0.1:12345", transport=httpx.MockTransport(respond)
    ) as client:
        verify_react_delivery(client)
    assert requests == ["/login.html", "/entrar", "/assets/index-12345678.js"]


@pytest.mark.parametrize(
    "status,location", [(200, "/entrar"), (307, "https://foreign.invalid/entrar")]
)
def test_native_login_refuses_obsolete_page_or_foreign_redirect(
    status: int, location: str
) -> None:
    with (
        httpx.Client(
            base_url="http://127.0.0.1:12345",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, headers={"location": location})
            ),
        ) as client,
        pytest.raises(AssertionError),
    ):
        verify_react_delivery(client)
