"""Verified React artifacts and the narrow HTTP compatibility boundary.

This module never selects legacy HTML or neighboring source checkouts. It is
shared by the package builder and runtime so they enforce the same artifact.
"""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Match

DIGEST = re.compile(r"[a-f0-9]{64}\Z")
ASSET_PATH = re.compile(r"assets/[A-Za-z0-9_./-]+\.(?:js|css|woff2?|ttf|otf|svg|png|jpe?g|webp|gif|avif|ico)\Z")
SPA_PATH = re.compile(
    r"/(?:entrar|inicio|cursos(?:/(?:nuevo|[1-9]\d*(?:/editar)?))?"
    r"|materiales(?:/(?:nuevo|[1-9]\d*(?:/editar)?))?|generar|fuentes|estudio/[1-9]\d*"
    r"|evaluaciones(?:/(?:nueva|historial|[1-9]\d*(?:/(?:editar|historial))?))?"
    r"|intentos/[1-9]\d*|envios/[1-9]\d*|correcciones(?:/[1-9]\d*)?"
    r"|personas(?:/(?:nueva|[1-9]\d*))?|estudiantes/[1-9]\d*"
    r"|progreso|tutor|ayuda|solicitudes(?:/[1-9]\d*)?|mensajes"
    r"|ajustes(?:/(?:cuenta|perfil|seguridad|apariencia|zona-horaria|ia|datos))?"
    r"|administracion/(?:copias|estado))\Z"
)
ROOT_FILES = {"index.html", ".vite/manifest.json", "third-party-notices.json", "favicon.ico"}
REQUIRED_FILES = {"index.html", ".vite/manifest.json", "third-party-notices.json"}
LEGACY_VIEWS = {
    "overview": "/inicio", "inbox": "/mensajes", "library": "/materiales",
    "study-plans": "/materiales", "assessments": "/evaluaciones", "grading": "/correcciones",
    "students": "/personas?role=student", "teachers": "/personas?role=teacher", "admins": "/personas?role=admin",
    "leaderboard": "/progreso?tab=leaderboard", "help-queue": "/solicitudes",
    "create": "/generar", "tutor": "/tutor", "settings": "/ajustes/perfil",
}

# Only caches observed in the supported migration are removed. Do not match a
# broad prefix: another app/old deployment may own unknown caches on this origin.
RETIREMENT_WORKER = """'use strict';
const RETIRED_CACHES = new Set([
  'slm-educator-v22-session-locale',
  'slm-educator-v22-session-locale-auth-validation'
]);
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => RETIRED_CACHES.has(name))
      .map(name => caches.delete(name)));
    await self.registration.unregister();
  })());
});
"""


def is_link(path: Path) -> bool:
    """Identify symlinks and Windows reparse points without dereferencing."""
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Invalid frontend artifact path.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Invalid frontend artifact path.")
    if value not in ROOT_FILES and not ASSET_PATH.fullmatch(value):
        raise ValueError("Unexpected file in frontend artifact.")
    return value


def _regular_file(root: Path, relative: str) -> Path:
    """Reject links in all included path components, including artifact roots."""
    path = root
    for component in ["", *PurePosixPath(relative).parts]:
        path = path / component
        if is_link(path):
            raise ValueError("Symlinked frontend artifact is not supported.")
    if not path.is_file():
        raise ValueError("Frontend artifact file is missing.")
    return path


def _read_json(path: Path) -> Any:
    """Reject duplicate JSON properties rather than silently taking the last."""
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate frontend manifest property.")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def _verify_vite(root: Path, records: dict[str, dict[str, Any]]) -> None:
    graph = _read_json(root / ".vite/manifest.json")
    if not isinstance(graph, dict) or not isinstance(graph.get("index.html"), dict):
        raise ValueError("Frontend Vite entry is missing.")
    if graph["index.html"].get("isEntry") is not True:
        raise ValueError("Frontend Vite entry is invalid.")
    for entry in graph.values():
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str) or entry["file"] not in records:
            raise ValueError("Frontend Vite asset is missing.")
        for key in ("css", "assets", "imports", "dynamicImports"):
            references = entry.get(key, [])
            if not isinstance(references, list) or any(not isinstance(item, str) for item in references):
                raise ValueError("Frontend Vite references are invalid.")
            targets = graph if key in {"imports", "dynamicImports"} else records
            if any(item not in targets for item in references):
                raise ValueError("Frontend Vite references are incomplete.")
    parser = _EntryAssets(records)
    parser.feed((root / "index.html").read_text(encoding="utf-8"))
    if graph["index.html"]["file"] not in parser.references:
        raise ValueError("Frontend HTML does not load its verified Vite entry.")


class _EntryAssets(HTMLParser):
    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        super().__init__()
        self.records = records
        self.references: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        value = attributes.get("src") if tag == "script" else attributes.get("href") if tag == "link" else None
        if value is None:
            return
        if not value.startswith("/") or value.startswith("//") or value[1:] not in self.records:
            raise ValueError("Frontend HTML asset must be local and manifest-listed.")
        self.references.add(value[1:])


def frontend_source_digest(root: Path) -> str:
    """Hash the declared production inputs without Node or dependency traversal.

    Keep the inventory and NUL-delimited UTF-8 framing identical to
    src/frontend/scripts/source-identity.mjs. Dist/dependencies are not inputs.
    """
    records: list[tuple[str, bytes]] = []

    def visit(path: Path) -> None:
        if is_link(path):
            raise ValueError("Symlinked frontend source input is not supported.")
        if path.is_dir():
            for child in path.iterdir():
                visit(child)
        elif path.is_file():
            records.append((path.relative_to(root).as_posix(), path.read_bytes()))
        else:
            raise ValueError("Frontend source input must be a regular file.")

    if is_link(root):
        raise ValueError("Symlinked frontend source root is not supported.")
    for name in ("index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts", "src", "scripts"):
        path = root / name
        if is_link(path):
            raise ValueError("Symlinked frontend source input is not supported.")
        if not (path.is_dir() if name in {"src", "scripts"} else path.is_file()):
            raise ValueError("Required frontend source input is missing.")
        visit(path)
    public = root / "public"
    try:
        public.lstat()
    except FileNotFoundError:
        pass
    else:
        visit(public)
    digest = sha256()
    for name, content in sorted(records, key=lambda record: record[0].encode("utf-8")):
        digest.update(f"{name}\0{len(content)}\0{sha256(content).hexdigest()}\n".encode("utf-8"))
    return digest.hexdigest()


def validate_frontend_dist(
    root: Path, *, lockfile: Path | None = None, source_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Validate shipped bytes and optional build-time source/lockfile identity.

    The manifest inventories every file except itself. It supplies integrity and
    consistency, not a signature or evidence of native/browser acceptance.
    """
    try:
        manifest = _read_json(_regular_file(root, "build-manifest.json"))
        if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
                or manifest.get("schema_version") != 2 or manifest.get("frontend") != "slm-educator"):
            raise ValueError("Unsupported frontend build manifest.")
        digest = manifest.get("lockfile_sha256")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError("Invalid frontend lockfile digest.")
        if lockfile is not None and (is_link(lockfile) or sha256(lockfile.read_bytes()).hexdigest() != digest):
            raise ValueError("Frontend build does not match package-lock.json; rebuild explicitly.")
        source_digest = manifest.get("source_sha256")
        if (type(manifest.get("source_identity_version")) is not int or manifest.get("source_identity_version") != 1
                or not isinstance(source_digest, str) or not DIGEST.fullmatch(source_digest)):
            raise ValueError("Invalid frontend source identity.")
        if source_root is not None and frontend_source_digest(source_root) != source_digest:
            raise ValueError("Frontend build does not match current source inputs; rebuild explicitly.")
        assets = manifest.get("assets")
        if not isinstance(assets, list):
            raise ValueError("Invalid frontend asset inventory.")
        records = _verify_assets(root, assets)
        _verify_vite(root, records)
        notices = _read_json(root / "third-party-notices.json")
        if not isinstance(notices, dict) or not isinstance(notices.get("packages"), list):
            raise ValueError("Frontend third-party notices are missing.")
        return records
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Frontend build is missing or unreadable; run npm run build in src/frontend.") from error


def _verify_assets(root: Path, assets: list[Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for record in assets:
        if not isinstance(record, dict):
            raise ValueError("Invalid frontend asset record.")
        relative = _safe_relative(record.get("path"))
        size, digest = record.get("size"), record.get("sha256")
        if relative in records or type(size) is not int or size < 0 or not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError("Duplicate or invalid frontend asset record.")
        content = _regular_file(root, relative).read_bytes()
        if len(content) != size or sha256(content).hexdigest() != digest:
            raise ValueError("Frontend asset integrity failed; rebuild explicitly.")
        records[relative] = record
    if not REQUIRED_FILES <= records.keys() or not any(name.startswith("assets/") for name in records):
        raise ValueError("Frontend build is incomplete.")
    actual = set()
    for path in root.rglob("*"):
        if is_link(path):
            raise ValueError("Symlinked frontend artifact is not supported.")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise ValueError("Frontend artifact must contain regular files only.")
    if actual != set(records) | {"build-manifest.json"}:
        raise ValueError("Frontend build contains unlisted or missing files.")
    return records


def resolve_frontend_dir() -> tuple[Path, Path]:
    """Select only explicit override, own frozen bundle, or this source tree."""
    frozen = bool(getattr(sys, "frozen", False))
    base = Path(sys.executable).absolute().parent if frozen else Path(__file__).resolve().parents[1]
    override = os.getenv("SLM_FRONTEND_DIR", "").strip() or os.getenv("SLM_WEB_DIR", "").strip()
    if override:
        # An invalid override is reported, never replaced by a different UI.
        return base, Path(override).expanduser().absolute()
    bundle = Path(getattr(sys, "_MEIPASS", base / "_internal")) if frozen else base
    return base, bundle / "src/frontend/dist"


def _positive_id(request: Request, key: str) -> str | None:
    values = request.query_params.getlist(key)
    if len(values) != 1 or not re.fullmatch(r"[1-9]\d{0,15}", values[0]):
        return None
    return values[0] if int(values[0]) <= 9007199254740991 else None


def _legacy_context(request: Request, *, ids: tuple[str, ...] = ("content_id", "plan_id")) -> str:
    """Keep recognized context without replaying actions or arbitrary query data."""
    values = {key: value for key in ids if (value := _positive_id(request, key))}
    for key, allowed in (("mode", {"review"}), ("from_session", {"1"}), ("ask_help", {"1"}),
                         ("filter", {"pending", "graded", "all"})):
        selected = request.query_params.getlist(key)
        if len(selected) == 1 and selected[0] in allowed:
            values[key] = selected[0]
    return "?" + urlencode(values) if values else ""


def _dashboard_destination(request: Request) -> str:
    # Fragments are invisible to HTTP. Always enter the client bridge at /inicio
    # so a hash can retain precedence over view/tab, including unknown hashes.
    view = request.query_params.getlist("view")
    tab = request.query_params.getlist("tab")
    key, value = ("view", view[0]) if view and view[0] else ("tab", tab[0] if tab else "")
    suffix = _legacy_context(request)
    if value in LEGACY_VIEWS:
        suffix = "?" + urlencode({key: value}) + ("&" + suffix[1:] if suffix else "")
    if "filter" not in request.query_params:
        filters = request.query_params.getlist("grading_filter")
        if len(filters) == 1 and filters[0] in {"pending", "graded", "all"}:
            suffix += ("&" if suffix else "?") + urlencode({"grading_filter": filters[0]})
    return "/inicio" + suffix


def _login_destination(request: Request) -> str:
    value = request.query_params.get("redirect", "")
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/entrar"
    try:
        target = urlsplit(value)
    except ValueError:
        return "/entrar"
    if target.netloc or target.scheme or target.path in {"/entrar", "/login.html"}:
        return "/entrar"
    context = Request({**request.scope, "path": target.path, "query_string": target.query.encode("utf-8")})
    destination = legacy_destination(context)
    if target.path == "/dashboard.html" and target.fragment:
        destination = LEGACY_VIEWS.get(target.fragment, "/inicio")
        suffix = _legacy_context(context)
        if target.fragment in LEGACY_VIEWS and suffix:
            destination += ("&" if "?" in destination else "?") + suffix[1:]
    if destination is None and (target.path == "/" or SPA_PATH.fullmatch(target.path)):
        destination = target.path + _legacy_context(context, ids=("content_id", "plan_id", "assessment_id", "submission_id"))
    return "/entrar?" + urlencode({"return": destination}) if destination else "/entrar"


def legacy_destination(request: Request) -> str | None:
    """Map known old pages and validated IDs without forwarding arbitrary URLs."""
    path = request.url.path
    simple = {"/index.html": "/inicio",
              "/course_designer.html": "/generar", "/portability.html": "/ajustes/datos"}
    if path in simple:
        return simple[path]
    if path == "/register.html":
        roles = request.query_params.getlist("role")
        return "/personas/nueva" + ("?" + urlencode({"role": roles[0]})
                                   if len(roles) == 1 and roles[0] in {"student", "teacher", "admin"} else "")
    if path == "/login.html":
        return _login_destination(request)
    if path == "/dashboard.html":
        return _dashboard_destination(request)
    identifier = _positive_id(request, "id")
    if path == "/study_plan_builder.html":
        return f"/cursos/{identifier}/editar" if identifier else "/cursos/nuevo"
    if path == "/assessment_builder.html":
        return f"/evaluaciones/{identifier}/editar" if identifier else "/evaluaciones/nueva"
    if path == "/assessment_taker.html":
        return f"/evaluaciones/{identifier}" if identifier else "/evaluaciones"
    if path == "/assessment_history.html":
        submission = _positive_id(request, "submission_id")
        assessment = _positive_id(request, "assessment_id")
        if submission:
            return f"/envios/{submission}"
        return f"/evaluaciones/{assessment}/historial" if assessment else "/evaluaciones/historial"
    if path == "/grading.html":
        submission = _positive_id(request, "submission_id")
        target = f"/correcciones/{submission}" if submission else "/correcciones"
        status = request.query_params.get("filter")
        return target + "?" + urlencode({"filter": status}) if status in {"pending", "graded", "all"} else target
    if path == "/session_player.html":
        content = _positive_id(request, "content_id")
        return f"/materiales/{content}" + _legacy_context(request, ids=("plan_id",)) if content else "/cursos"
    return None


class FrontendDelivery:
    """Read-only serving of one verified frontend, without generic SPA fallback."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.records: dict[str, dict[str, Any]] | None = None

    async def serve(self, request: Request) -> Response:
        path = request.url.path
        if path == "/api" or path.startswith("/api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        destination = legacy_destination(request)
        if destination:
            return RedirectResponse(destination, status_code=307, headers={"Cache-Control": "no-store"})
        if path == "/sw.js":
            return Response(RETIREMENT_WORKER, media_type="application/javascript", headers={"Cache-Control": "no-store"})
        relative = path.lstrip("/")
        is_page = path == "/" or bool(SPA_PATH.fullmatch(path))
        # Unknown paths (including old assets and source files) are real 404s.
        if not is_page and not ASSET_PATH.fullmatch(relative) and relative not in {"third-party-notices.json", "favicon.ico"}:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        try:
            if not is_page:
                _safe_relative(relative)
        except ValueError:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        try:
            if self.records is None:
                self.records = validate_frontend_dist(self.root)
            relative = "index.html" if is_page else relative
            if relative not in self.records:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            source = _regular_file(self.root, _safe_relative(relative))
            content = source.read_bytes()
            record = self.records[relative]
            if len(content) != record["size"] or sha256(content).hexdigest() != record["sha256"]:
                raise ValueError("Frontend changed after verification; restart after rebuilding.")
        except ValueError:
            return JSONResponse({"detail": "Frontend build unavailable. Build src/frontend explicitly and restart."}, status_code=503,
                                headers={"Cache-Control": "no-store"})
        except OSError:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        hashed = re.fullmatch(r"assets/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+", relative)
        cache = "public, max-age=31536000, immutable" if hashed and not is_page else "no-cache"
        headers = {"Cache-Control": cache, "X-Content-Type-Options": "nosniff", "ETag": '"' + record["sha256"] + '"'}
        if request.headers.get("if-none-match") == headers["ETag"]:
            return Response(status_code=304, headers=headers)
        headers["Content-Length"] = str(len(content))
        return Response(b"" if request.method == "HEAD" else content,
                        media_type=mimetypes.guess_type(str(source))[0] or "application/octet-stream", headers=headers)


def register_frontend(app: FastAPI, root: Path) -> None:
    """Add the final GET/HEAD boundary only after every API has been included."""
    async def missing_api(request: Request) -> Response:
        # A catch-all would otherwise mask FastAPI's normal slash redirects.
        alternate = request.url.path.rstrip("/") if request.url.path.endswith("/") else request.url.path + "/"
        scope = {**request.scope, "path": alternate}
        for route in app.routes:
            if getattr(route, "path", "") in {"/api", "/api/{path:path}", "/{path:path}"}:
                continue
            if route.matches(scope)[0] == Match.FULL:
                suffix = "?" + request.url.query if request.url.query else ""
                return RedirectResponse(alternate + suffix, status_code=307)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    for path in ("/api", "/api/{path:path}"):
        app.add_api_route(path, missing_api, methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
    frontend = FrontendDelivery(root)
    app.add_api_route("/{path:path}", frontend.serve, methods=["GET", "HEAD"], include_in_schema=False)
