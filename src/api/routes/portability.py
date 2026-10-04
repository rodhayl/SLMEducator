"""Explicit, permission-scoped course portability and private backup downloads."""

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.security import get_current_user, require_teacher_or_admin
from src.api.policies import require_allowed
from src.core.models import StudyPlan, User
from src.core.models.models import ENCRYPTION_KEY
from src.core.roles import is_admin
from src.core.services.portability_service import (
    MAX_PACKAGE_BYTES,
    export_course,
    import_course,
    preview_package,
    render_handout,
)
from src.core.services.recovery_service import backup_preview, create_backup

router = APIRouter(prefix="/api/portability", tags=["portability"])


class Confirmation(BaseModel):
    confirm: bool = False


def _package(db: Session, user: User, plan_id: int, audience: str) -> dict:
    plan = db.get(StudyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    try:
        return export_course(db, user, plan, audience)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, ValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/plans/{plan_id}/preview")
def export_preview(
    plan_id: int,
    audience: Literal["learner", "teacher"] = Query("learner"),
    export_format: Literal["json", "html", "markdown"] = Query("json", alias="format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Show included/excluded fields and counts before a course export."""
    if audience == "teacher" and export_format != "json":
        raise HTTPException(
            status_code=422, detail="Restorable teacher packages use JSON"
        )
    return {
        **preview_package(_package(db, current_user, plan_id, audience)),
        "selected_format": export_format,
        "available_formats": (
            ["json"] if audience == "teacher" else ["html", "markdown", "json"]
        ),
    }


@router.get("/plans/{plan_id}/export")
def export_plan(
    plan_id: int,
    audience: Literal["learner", "teacher"] = Query("learner"),
    export_format: Literal["json", "html", "markdown"] = Query("json", alias="format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download an authorized learner handout or complete teacher package."""
    package = _package(db, current_user, plan_id, audience)
    if export_format != "json":
        if audience != "learner":
            raise HTTPException(
                status_code=422, detail="Restorable teacher packages use JSON"
            )
        content = render_handout(package, export_format)
        suffix = "html" if export_format == "html" else "md"
        media = "text/html" if export_format == "html" else "text/markdown"
        return Response(
            content,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="course-{plan_id}-learner.{suffix}"',
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; style-src 'none'; sandbox",
            },
        )
    return Response(
        json.dumps(package, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="course-{plan_id}-{audience}.json"',
            "Cache-Control": "no-store",
        },
    )


async def _read_package(request: Request) -> tuple[dict, bool]:
    """Enforce the import byte limit while streaming, before JSON parsing."""
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > MAX_PACKAGE_BYTES:
            raise HTTPException(
                status_code=413, detail="Course package exceeds the 10 MB limit"
            )
        chunks.extend(chunk)
    try:
        body = json.loads(chunks)
        if not isinstance(body, dict) or not isinstance(body.get("package"), dict):
            raise ValueError("Expected a package object")
        return body["package"], body.get("confirm") is True
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=422, detail="Invalid course package JSON"
        ) from error


@router.post("/import/preview")
async def import_preview(
    request: Request, current_user: User = Depends(require_teacher_or_admin)
):
    """Validate a proposed package without changing application data."""
    package, _ = await _read_package(request)
    try:
        preview = preview_package(package)
        if preview["audience"] != "teacher":
            raise ValueError("Learner handouts cannot restore a teacher course")
        return {
            **preview,
            "import_effect": "Creates a new private draft owned by you; existing courses stay unchanged",
        }
    except (ValueError, ValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/import")
async def import_plan(
    request: Request,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Create a reviewed package as a new draft in one transaction."""
    package, confirmed = await _read_package(request)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="Preview the package and confirm the new draft import",
        )
    try:
        preview = preview_package(package)
        plan = import_course(db, current_user, package)
        db.commit()
        return {
            "study_plan_id": plan.id,
            "status": "draft",
            "counts": preview["counts"],
        }
    except PermissionError as error:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, ValidationError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/backup/preview")
def private_backup_preview(current_user: User = Depends(get_current_user)):
    """Explain private database backup scope; never transmit the encryption key."""
    require_allowed(is_admin(current_user))
    return backup_preview(ENCRYPTION_KEY)


@router.post("/backup")
def private_backup(
    confirmation: Confirmation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download an encrypted snapshot after explicit administrator confirmation."""
    require_allowed(is_admin(current_user))
    if not confirmation.confirm:
        raise HTTPException(
            status_code=409,
            detail="Review backup exclusions and confirm the private download",
        )
    bind = db.get_bind()
    database = bind.url.database
    if not database or database == ":memory:":
        raise HTTPException(
            status_code=409,
            detail="Private backups require a file-backed SQLite database",
        )
    try:
        archive = create_backup(Path(database), ENCRYPTION_KEY)
    except (ValueError, OSError, TimeoutError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(
        archive,
        media_type="application/vnd.slmeducator.backup+json",
        headers={
            "Content-Disposition": 'attachment; filename="private-database.slmbackup"',
            "Cache-Control": "no-store",
        },
    )
