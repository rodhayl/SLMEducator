"""Synthetic build integrity, safe HTTP delivery and worker retirement contracts."""

import json
import re
from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.frontend_delivery import (
    RETIREMENT_WORKER, SPA_PATH, register_frontend, resolve_frontend_dir, validate_frontend_dist,
)
from tests.fixtures.frontend_artifact import make_frontend, refresh_manifest


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    return make_frontend(tmp_path)


@pytest.fixture
def client(artifact: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/status")
    def status() -> dict[str, str]:
        return {"status": "online", "version": "2.0.0"}

    @app.get("/api/assistance/known")
    def last_api() -> dict[str, bool]:
        return {"reachable": True}

    register_frontend(app, artifact)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/entrar", "/inicio", "/cursos/12/editar", "/estudio/12", "/materiales/34",
                                  "/evaluaciones/nueva", "/evaluaciones/historial", "/evaluaciones/4/historial",
                                  "/personas/nueva", "/administracion/copias", "/correcciones/42", "/materiales", "/materiales/nuevo",
                                  "/materiales/2/editar", "/generar", "/fuentes", "/ajustes/perfil", "/tutor"])
def test_known_deep_links_serve_verified_html(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert '<div id="root">' in response.text
    assert client.head(path).content == b""


def test_every_navigation_entry_has_a_server_delivery_route() -> None:
    """Prevent menu destinations from becoming unserved client-only routes."""
    contracts = Path("src/frontend/src/app/route-contracts.ts").read_text()
    paths = re.findall(r"path:\s*'([^']+)'", contracts)
    assert paths
    assert all(SPA_PATH.fullmatch(path) for path in paths)


@pytest.mark.parametrize("method", ["get", "head", "post", "put", "patch", "delete", "options"])
def test_unknown_api_never_receives_spa(client: TestClient, method: str) -> None:
    response = getattr(client, method)("/api/no-existe")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert b"<html" not in response.content
    assert client.get("/api/status").json() == {"status": "online", "version": "2.0.0"}
    assert client.get("/api/assistance/known").json() == {"reachable": True}


@pytest.mark.parametrize("path", ["/does-not-exist", "/404.html", "/unknown.html", "/cursos/0", "/personas/-1",
                                  "/assets/missing.js", "/static/js/auth.js", "/src/starter.py", "/.vite/manifest.json",
                                  "/build-manifest.json", "/assets/%2e%2e/index.html", "/assets//index-12345678.js",
                                  "/assets/..%5cindex.html"])
def test_missing_assets_and_unknown_routes_are_true_404(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert "<html" not in response.text


def test_assets_are_local_immutable_and_notices_are_revalidated(client: TestClient) -> None:
    asset = client.get("/assets/index-12345678.js")
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "javascript" in asset.headers["content-type"]
    assert client.get("/third-party-notices.json").headers["cache-control"] == "no-cache"


@pytest.mark.parametrize(("old", "new"), [
    ("/index.html", "/inicio"), ("/login.html?next=https://evil.example", "/entrar"),
    ("/register.html", "/personas/nueva"),
    ("/register.html?role=teacher&next=//evil.example", "/personas/nueva?role=teacher"),
    ("/register.html?role=student", "/personas/nueva?role=student"),
    ("/register.html?role=admin", "/personas/nueva?role=admin"),
    ("/register.html?role=teacher&role=admin", "/personas/nueva"),
    ("/register.html?role=superadmin", "/personas/nueva"),
    ("/register.html?role=//evil.example", "/personas/nueva"), ("/dashboard.html?view=assessments", "/inicio?view=assessments"),
    ("/dashboard.html?tab=students", "/inicio?tab=students"), ("/dashboard.html?view=//evil.example", "/inicio"),
    ("/dashboard.html?view=unknown&tab=library", "/inicio"),
    ("/dashboard.html?view=grading&view=library", "/inicio?view=grading"),
    ("/dashboard.html?view=&tab=library", "/inicio?tab=library"),
    ("/login.html?redirect=%2Fdashboard.html%3Fview%3Dlibrary%23unknown", "/entrar?return=%2Finicio"),
    ("/dashboard.html?view=library", "/inicio?view=library"),
    ("/dashboard.html?view=tutor&content_id=42&plan_id=3&from_session=1&ask_help=1&x=secret", "/inicio?view=tutor&content_id=42&plan_id=3&from_session=1&ask_help=1"),
    ("/dashboard.html?view=grading&grading_filter=graded", "/inicio?view=grading&grading_filter=graded"),
    ("/session_player.html?content_id=42&mode=review", "/materiales/42?mode=review"),
    ("/login.html?redirect=%2Fassessment_taker.html%3Fid%3D42", "/entrar?return=%2Fevaluaciones%2F42"),
    ("/login.html?redirect=%2Fdashboard.html%23library", "/entrar?return=%2Fmateriales"),
    ("/course_designer.html", "/generar"), ("/study_plan_builder.html?id=12", "/cursos/12/editar"),
    ("/assessment_builder.html?id=42", "/evaluaciones/42/editar"),
    ("/assessment_builder.html", "/evaluaciones/nueva"),
    ("/assessment_taker.html?id=42&next=//evil.example", "/evaluaciones/42"),
    ("/assessment_history.html?assessment_id=42", "/evaluaciones/42/historial"),
    ("/assessment_history.html?submission_id=14", "/envios/14"),
    ("/assessment_history.html", "/evaluaciones/historial"),
    ("/grading.html?submission_id=42&filter=pending", "/correcciones/42?filter=pending"),
    ("/grading.html?filter=https://evil.example", "/correcciones"),
    ("/session_player.html?content_id=42&plan_id=14", "/materiales/42?plan_id=14"),
    ("/session_player.html", "/cursos"), ("/portability.html", "/ajustes/datos"),
])
def test_legacy_redirects_preserve_only_allowed_destinations(client: TestClient, old: str, new: str) -> None:
    response = client.get(old, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == new
    assert response.headers["cache-control"] == "no-store"
    assert client.get(new).status_code == 200


@pytest.mark.parametrize("bad", ["0", "-1", "1.0", "01", "../../x", "//evil.example", "%0d%0aLocation:evil", "9007199254740992", "1&id=2"])
def test_legacy_ids_cannot_redirect_or_select_invalid_resource(client: TestClient, bad: str) -> None:
    response = client.get("/assessment_taker.html?id=" + bad, follow_redirects=False)
    assert response.headers["location"] == "/evaluaciones"


def test_missing_build_is_clear_503_without_api_or_legacy_fallback(tmp_path: Path) -> None:
    app = FastAPI()
    register_frontend(app, tmp_path / "missing")
    client = TestClient(app)
    assert client.get("/").status_code == 503
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/static/js/auth.js").status_code == 404
    assert client.get("/sw.js").status_code == 200


def test_missing_listed_asset_after_start_is_not_html(client: TestClient, artifact: Path) -> None:
    assert client.get("/").status_code == 200
    (artifact / "assets/index-12345678.js").unlink()
    assert client.get("/assets/index-12345678.js").status_code == 404


def test_tampered_build_is_not_served(client: TestClient, artifact: Path) -> None:
    (artifact / "assets/index-12345678.js").write_text("unverified bytes")
    assert client.get("/").status_code == 503


@pytest.mark.parametrize("field,value", [("schema_version", 1), ("schema_version", True), ("frontend", "legacy"),
                                        ("lockfile_sha256", "short"), ("source_sha256", "short"),
                                        ("source_identity_version", True), ("source_identity_version", 2), ("assets", {})])
def test_invalid_manifest_headers_fail(artifact: Path, field: str, value: object) -> None:
    path = artifact / "build-manifest.json"
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate_frontend_dist(artifact)


@pytest.mark.parametrize("path", ["../secret", "/tmp/secret", "assets/../../secret", "assets/./secret", "assets//secret",
                                  "assets\\secret", "C:/secret", "src/main.tsx", "build-manifest.json", "assets/x?query"])
def test_manifest_paths_fail_closed(artifact: Path, path: str) -> None:
    manifest_path = artifact / "build-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["assets"][0]["path"] = path
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate_frontend_dist(artifact)


@pytest.mark.parametrize("change", ["duplicate", "size", "hash", "missing", "unlisted", "vite-missing", "vite-external", "html-external"])
def test_artifact_content_and_reference_validation(artifact: Path, change: str) -> None:
    path = artifact / "build-manifest.json"
    manifest = json.loads(path.read_text())
    if change == "duplicate":
        manifest["assets"].append(manifest["assets"][0])
    elif change == "size":
        manifest["assets"][0]["size"] += 1
    elif change == "hash":
        manifest["assets"][0]["sha256"] = "0" * 64
    elif change == "missing":
        (artifact / "third-party-notices.json").unlink()
    elif change == "unlisted":
        (artifact / "secret.txt").write_text("synthetic bytes")
    elif change.startswith("vite"):
        graph = json.loads((artifact / ".vite/manifest.json").read_text())
        graph["index.html"]["file"] = "assets/missing.js" if change == "vite-missing" else "https://external.example/app.js"
        (artifact / ".vite/manifest.json").write_text(json.dumps(graph))
        manifest = refresh_manifest(artifact)
    else:
        (artifact / "index.html").write_text('<script src="https://external.example/app.js"></script>')
        manifest = refresh_manifest(artifact)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate_frontend_dist(artifact)


def test_source_and_override_resolution_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("SLM_FRONTEND_DIR", raising=False)
    monkeypatch.delenv("SLM_WEB_DIR", raising=False)
    base, frontend = resolve_frontend_dir()
    assert frontend == base / "src/frontend/dist"
    invalid = tmp_path / "old-web"
    monkeypatch.setenv("SLM_FRONTEND_DIR", str(invalid))
    assert resolve_frontend_dir() == (base, invalid)
    with pytest.raises(ValueError):
        validate_frontend_dist(invalid)


def test_frozen_resolution_never_selects_neighboring_checkout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package = tmp_path / "checkout/dist/SLMEducator"
    package.mkdir(parents=True)
    legacy = tmp_path / "checkout/src/web"
    (legacy / "static").mkdir(parents=True)
    (legacy / "dashboard.html").write_text("neighboring old GUI")
    make_frontend(tmp_path / "checkout")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(package / "SLMEducator.exe"))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delenv("SLM_WEB_DIR", raising=False)
    monkeypatch.delenv("SLM_FRONTEND_DIR", raising=False)
    assert resolve_frontend_dir() == (package, package / "_internal/src/frontend/dist")
    bundle = tmp_path / "explicit-bundle"
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    assert resolve_frontend_dir() == (package, bundle / "src/frontend/dist")


def test_retirement_worker_http_and_scope(client: TestClient) -> None:
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("application/javascript")
    for forbidden in ("skipWaiting", "clients.claim", "navigate(", "reload(", "localStorage", "indexedDB", "respondWith", "caches.open"):
        assert forbidden not in response.text
    assert "addEventListener('activate'" in response.text
    assert "registration.unregister()" in response.text


def test_retirement_only_deletes_recognized_caches_after_activation(tmp_path: Path) -> None:
    """Execute synthetic SW events in Node; this is not browser lifecycle proof."""
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for synthetic retirement-worker contract")
    script = tmp_path / "worker-test.cjs"
    script.write_text("""
const assert = require('node:assert/strict');
const listeners = {}, deleted = []; let unregistered = false;
global.self = {addEventListener: (name, handler) => {listeners[name] = handler}, registration: {unregister: async () => {unregistered = true}}};
global.caches = {keys: async () => ['slm-educator-v22-session-locale', 'slm-educator-v22-session-locale-auth-validation', 'slm-educator-unknown', 'another-app'], delete: async name => {deleted.push(name)}};
""" + RETIREMENT_WORKER + """
assert.deepEqual(Object.keys(listeners), ['activate']);
assert.deepEqual(deleted, []); assert.equal(unregistered, false);
let work; listeners.activate({waitUntil: promise => {work = promise}});
work.then(() => {assert.deepEqual(deleted.sort(), ['slm-educator-v22-session-locale', 'slm-educator-v22-session-locale-auth-validation'].sort()); assert.equal(unregistered, true)}).catch(error => {console.error(error); process.exitCode = 1});
""", encoding="utf-8")
    subprocess.run([node, str(script)], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/login.html?redirect=/cursos", "/entrar", "/\\evil.example", "/%2f%2fevil.example", "/unknown"])
def test_legacy_login_return_is_allowlisted(client: TestClient, target: str) -> None:
    response = client.get("/login.html", params={"redirect": target}, follow_redirects=False)
    assert response.headers["location"] == "/entrar"


def test_api_trailing_slash_redirect_remains_available() -> None:
    app = FastAPI()

    @app.post("/api/example/")
    def example() -> dict[str, bool]:
        return {"reached": True}

    register_frontend(app, Path("unused"))
    client = TestClient(app)
    response = client.post("/api/example?value=42", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/api/example/?value=42"
    assert client.post("/api/example").json() == {"reached": True}


@pytest.mark.parametrize("path", ["index.html", "assets/index-12345678.js"])
def test_changed_bytes_after_first_request_fail_closed(client: TestClient, artifact: Path, path: str) -> None:
    assert client.get("/").status_code == 200
    (artifact / path).write_text("changed after server verification")
    assert client.get("/" if path == "index.html" else "/" + path).status_code == 503


def test_http_revalidation_keeps_byte_integrity(client: TestClient, artifact: Path) -> None:
    response = client.get("/")
    etag = response.headers["etag"]
    assert client.get("/", headers={"if-none-match": etag}).status_code == 304
    head = client.head("/")
    assert head.content == b""
    assert int(head.headers["content-length"]) == len(response.content)
    (artifact / "index.html").write_text("unverified new index")
    assert client.get("/", headers={"if-none-match": etag}).status_code == 503
