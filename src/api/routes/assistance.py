"""Teacher-owned assessment assistance control and read-only learner policy."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.api.policies import can_view_assessment, can_manage_assessment, require_allowed
from src.core.models import Assessment, User
from src.core.services.assistance_policy import (
    AssistanceMode,
    assessment_policy,
    set_assessment_policy,
    effective_policy,
)

router = APIRouter(tags=["assistance-policy"])


class PolicyChange(BaseModel):
    mode: AssistanceMode


@router.get("/api/assessments/{assessment_id}/assistance-policy")
def get_assessment_policy(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    require_allowed(can_view_assessment(db, current_user, assessment))
    return {
        "assessment_id": assessment.id,
        "mode": assessment_policy(db, assessment),
        "scope": "active_attempt",
    }


@router.put("/api/assessments/{assessment_id}/assistance-policy")
def update_assessment_policy(
    assessment_id: int,
    request: PolicyChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The assessment author/administrator controls assistance, never the learner."""
    assessment = db.get(Assessment, assessment_id)
    require_allowed(can_manage_assessment(db, current_user, assessment))
    try:
        set_assessment_policy(db, assessment, request.mode)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "assessment_id": assessment.id,
        "mode": request.mode,
        "scope": "active_attempt",
    }


@router.get("/api/ai/assistance-policy")
def get_effective_policy(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Explain enforced scope without exposing another learner's attempts."""
    return effective_policy(db, current_user)
