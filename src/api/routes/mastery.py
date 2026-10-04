from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.api.dependencies import get_db
from src.api.policies import require_content

from src.api.security import get_current_user
from src.core.models import User
from src.core.services.spaced_repetition_service import (
    SpacedRepetitionService,
    get_spaced_repetition_service,
)

router = APIRouter(prefix="/api/mastery", tags=["mastery"])


class DueItem(BaseModel):
    mastery_node_id: int
    content_id: int
    content_title: str
    content_type: str
    mastery_level: int
    days_overdue: int
    evidence_type: str = "legacy_or_self_report"


class ReviewSubmit(BaseModel):
    content_id: int
    rating: int = Field(ge=1, le=5)
    actual_duration_min: int = Field(default=5, ge=0, le=1440)


class MasteryOverview(BaseModel):
    total_items: int
    average_mastery: int
    items_mastered: int
    items_in_progress: int
    items_due_review: int
    evidence_note: str = (
        "Review schedule is a heuristic. Confidence and legacy activity are not assessed mastery."
    )


@router.get("/due", response_model=List[DueItem])
async def get_due_reviews(
    current_user: User = Depends(get_current_user),
    sr_service: SpacedRepetitionService = Depends(get_spaced_repetition_service),
):
    """Get items due for review for the current student"""
    due_items = sr_service.get_due_reviews(current_user.id, limit=20)
    observed = (current_user.settings or {}).get("assessed_content_ids", [])
    for item in due_items:
        item["evidence_type"] = (
            "final_assessment"
            if item["content_id"] in observed
            else "legacy_or_self_report"
        )
    return due_items


@router.post("/review")
async def submit_review(
    review: ReviewSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Keep self-confidence distinct from checked understanding or final grades."""
    require_content(db, current_user, review.content_id)
    user = db.get(User, current_user.id)
    settings = dict(user.settings or {})
    confidence = dict(settings.get("self_confidence", {}))
    confidence[str(review.content_id)] = {
        "rating": review.rating,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    settings["self_confidence"] = confidence
    user.settings = settings
    db.commit()
    return {
        "status": "ok",
        "self_confidence": review.rating,
        "evidence_type": "self_report",
        "is_assessed_mastery": False,
    }


@router.get("/overview", response_model=MasteryOverview)
async def get_overview(
    current_user: User = Depends(get_current_user),
    sr_service: SpacedRepetitionService = Depends(get_spaced_repetition_service),
):
    """Get mastery overview stats"""
    return sr_service.get_student_mastery_overview(current_user.id)


@router.get("/levels")
async def get_all_mastery_levels(
    current_user: User = Depends(get_current_user),
    sr_service: SpacedRepetitionService = Depends(get_spaced_repetition_service),
):
    """Get mastery levels for all content (content_id -> mastery_level mapping)"""
    return sr_service.get_all_mastery_levels(current_user.id)


@router.get("/evidence")
async def review_evidence(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Expose the provenance of legacy review, checked scores and self-confidence."""
    from src.core.models import MasteryNode, Content
    from src.api.policies import can_view_content

    user = db.get(User, current_user.id)
    settings = user.settings or {}
    assessed = settings.get("assessed_content_ids", [])
    confidence = settings.get("self_confidence", {})
    nodes = {
        node.content_id: node
        for node in db.query(MasteryNode).filter_by(student_id=user.id)
    }
    ids = set(nodes) | {int(key) for key in confidence if key.isdigit()}
    items = []
    for content_id in sorted(ids):
        content = db.get(Content, content_id)
        if not can_view_content(db, user, content):
            continue
        node = nodes.get(content_id)
        observed = content_id in assessed and node is not None
        items.append(
            {
                "content_id": content_id,
                "evidence_type": (
                    "final_assessment" if observed else "legacy_or_self_report"
                ),
                "assessment_percent": node.mastery_level if observed else None,
                "self_confidence": confidence.get(str(content_id), {}).get("rating"),
            }
        )
    return {"items": items}
