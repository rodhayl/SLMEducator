"""Explicit per-user timezone policy, separate from timestamp migration."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import User
from src.core.services.temporal_service import (
    local_date,
    user_timezone,
    validate_timezone,
)

router = APIRouter(prefix="/api/settings/timezone", tags=["settings"])


class TimezoneUpdate(BaseModel):
    timezone: str = Field(min_length=1, max_length=100)


def _policy(user: User) -> dict:
    return {
        "timezone": user_timezone(user),
        "timezone_source": (
            "user" if (user.settings or {}).get("timezone") else "default"
        ),
        "local_date": local_date(user),
        "timestamp_policy": "utc_offset_v1",
        "legacy_timestamps": "unknown_until_explicit_migration",
        "historical_dates": "preserved_as_recorded",
    }


@router.get("")
async def get_timezone(current_user: User = Depends(get_current_user)):
    """Show the explicit UTC default or user's selected civil-day timezone."""
    return _policy(current_user)


@router.put("")
async def set_timezone(
    data: TimezoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change future local-day calculations without converting historical data."""
    try:
        zone = validate_timezone(data.timezone)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    user = db.get(User, current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    settings = dict(user.settings or {})
    settings["timezone"] = zone
    user.settings = settings
    db.commit()
    return _policy(user)
