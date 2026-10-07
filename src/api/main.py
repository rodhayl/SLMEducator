"""FastAPI domain routes followed by verified React delivery."""

from fastapi import FastAPI

from src.frontend_delivery import register_frontend, resolve_frontend_dir

app = FastAPI(title="SLM Educator API")

# Kept as a compatibility import for packaging/launcher checks.
_resolve_web_dir = resolve_frontend_dir
BASE_DIR, WEB_DIR = resolve_frontend_dir()

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
    portability,
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
app.include_router(portability.router)
from src.api.routes import timezone as timezone_settings
app.include_router(timezone_settings.router)

from src.api.routes import upload

app.include_router(upload.router)

from src.api.routes import students

app.include_router(students.router)


@app.get("/api/status")
async def get_status() -> dict[str, str]:
    return {"status": "online", "version": "2.0.0"}


from src.api.routes import assistance

app.include_router(assistance.router)

# All APIs must precede this narrow, allowlisted frontend route.
register_frontend(app, WEB_DIR)
