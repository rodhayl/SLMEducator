from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel

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


class ReviewSubmit(BaseModel):
    content_id: int
    rating: int  # 1-5 (Performance score will be calculation logic: e.g. rating * 20)
    actual_duration_min: int = 5


class MasteryOverview(BaseModel):
    total_items: int
    average_mastery: int
    items_mastered: int
    items_in_progress: int
    items_due_review: int


@router.get("/due", response_model=List[DueItem])
async def get_due_reviews(
    current_user: User = Depends(get_current_user),
    sr_service: SpacedRepetitionService = Depends(get_spaced_repetition_service),
):
    """Get items due for review for the current student"""
    due_items = sr_service.get_due_reviews(current_user.id, limit=20)
    return due_items


@router.post("/review")
async def submit_review(
    review: ReviewSubmit,
    current_user: User = Depends(get_current_user),
    sr_service: SpacedRepetitionService = Depends(get_spaced_repetition_service),
):
    """Submit a review result"""
    # Convert 1-5 rating to 0-100 score
    # 1=0, 2=25, 3=50, 4=75, 5=100
    performance_score = (review.rating - 1) * 25
    if performance_score < 0:
        performance_score = 0
    if performance_score > 100:
        performance_score = 100

    success = sr_service.update_review_outcome(
        current_user.id, review.content_id, performance_score
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update mastery")

    return {"status": "ok", "score_awarded": performance_score}


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
