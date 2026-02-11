from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys
import os

app = FastAPI(title="SLM Educator API")


def _looks_like_web_dir(path: Path) -> bool:
    try:
        return (path / "static").exists() and (path / "dashboard.html").exists()
    except OSError:
        return False


def _resolve_web_dir() -> tuple[Path, Path]:
    """
    Resolve the directory containing the web UI.

    Order of preference:
      1) `SLM_WEB_DIR` env override (if valid)
      2) Source checkout `src/web` (when running from repo even if frozen)
      3) Bundled PyInstaller `_internal/src/web`
    """
    frozen = bool(getattr(sys, "frozen", False))

    if frozen:
        # Running as compiled executable
        # sys.executable is the exe path, parent is the dist/APPNAME folder
        base_dir = Path(sys.executable).parent
        bundled = base_dir / "_internal" / "src" / "web"

        env_override = os.getenv("SLM_WEB_DIR", "").strip()
        if env_override:
            env_path = Path(env_override).expanduser().resolve()
            if _looks_like_web_dir(env_path):
                return base_dir, env_path

        # When running from a repo checkout, prefer the up-to-date source web dir
        # over the bundled copy (which can be stale if the exe wasn't rebuilt).
        repo_candidate = base_dir.parent.parent / "src" / "web"
        if _looks_like_web_dir(repo_candidate):
            return base_dir, repo_candidate

        local_candidate = base_dir / "src" / "web"
        if _looks_like_web_dir(local_candidate):
            return base_dir, local_candidate

        return base_dir, bundled

    # Running from source
    # src/api/main.py -> src/api -> src -> project_root
    base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir, base_dir / "src" / "web"


# Define paths - handle both development and frozen (PyInstaller) environments
BASE_DIR, WEB_DIR = _resolve_web_dir()

# API Routes - starter.py sets up sys.path so these work in both environments
from src.api.routes import (
    auth,
    dashboard,
    content,
    ai,
    settings,
    generation,
    assessment,
    learning,
    mastery,
    classroom,
    study_plans,
    gamification,
    annotations,
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(content.router)
app.include_router(ai.router)
app.include_router(settings.router)
app.include_router(generation.router)
app.include_router(assessment.router)
app.include_router(learning.router)
app.include_router(mastery.router)
app.include_router(classroom.router)
app.include_router(study_plans.router)
app.include_router(gamification.router)
app.include_router(annotations.router)

from src.api.routes import upload

app.include_router(upload.router)

from src.api.routes import students

app.include_router(students.router)


@app.get("/api/status")
async def get_status():
    return {"status": "online", "version": "2.0.0"}


# Avoid noisy 404s in the browser console for favicon requests.


@app.get("/favicon.ico")
async def favicon():
    icon_path = WEB_DIR / "static" / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    return Response(status_code=204)


# Serve Service Worker from root (required for proper scope)
@app.get("/sw.js")
async def service_worker():
    sw_path = WEB_DIR / "sw.js"
    if sw_path.exists():
        # Avoid SW caching across deployments; the SW itself controls caching.
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )
    return Response(status_code=404)


# Serve Static Files
# Mount /static for CSS/JS
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

# Serve Index (SPA style)


@app.get("/")
async def read_index():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Index file not found. Please build the frontend."}


@app.get("/{page_name}.html")
async def read_page(page_name: str):
    """Serve HTML pages from the WEB_DIR."""
    page_path = WEB_DIR / f"{page_name}.html"
    if page_path.exists():
        return FileResponse(page_path)
    return Response(status_code=404)


# Mount other static directories
if (WEB_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=str(WEB_DIR / "images")), name="images")
