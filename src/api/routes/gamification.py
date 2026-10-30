"""
Gamification API Routes

Provides endpoints for Phase 3 gamification features:
- XP, levels, streaks
- Badges and achievements
- Leaderboards
- Daily goals
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    User,
    Badge,
    UserBadge,
    DailyGoal,
    LeaderboardEntry,
    GamificationSettings,
)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


# --- Pydantic Models ---


class GamificationProfile(BaseModel):
    """User's gamification stats"""

    xp: int
    level: int
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date]
    badges_earned: int


class BadgeResponse(BaseModel):
    """Badge details"""

    id: int
    name: str
    description: str
    icon_path: Optional[str]
    xp_value: int
    earned: bool
    earned_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LeaderboardItem(BaseModel):
    """Leaderboard entry"""

    rank: int
    user_id: int
    username: str
    xp: int
    level: int


class DailyGoalResponse(BaseModel):
    """Daily goal status"""

    id: Optional[int]
    goal_type: str
    target_value: int
    current_value: int
    completed: bool
    goal_date: date


class DailyGoalCreate(BaseModel):
    """Create/update daily goal"""

    goal_type: str = "lessons"  # lessons, exercises, time
    target_value: int = 3
    save_as_default: bool = False


# --- Routes ---


@router.get("/profile", response_model=GamificationProfile)
async def get_gamification_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's gamification profile"""
    # Count earned badges
    badges_count = (
        db.query(func.count(UserBadge.badge_id))
        .filter(UserBadge.user_id == current_user.id)
        .scalar()
        or 0
    )

    return GamificationProfile(
        xp=current_user.xp or 0,
        level=current_user.level or 1,
        current_streak=current_user.current_streak or 0,
        longest_streak=current_user.longest_streak or 0,
        last_activity_date=current_user.last_activity_date,
        badges_earned=badges_count,
    )


@router.get("/badges", response_model=List[BadgeResponse])
async def get_badges(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all badges with user's earned status"""
    all_badges = db.query(Badge).filter(Badge.is_active == True).all()

    # Get user's earned badges
    earned = db.query(UserBadge).filter(UserBadge.user_id == current_user.id).all()
    earned_map = {ub.badge_id: ub.earned_at for ub in earned}

    result = []
    for badge in all_badges:
        result.append(
            BadgeResponse(
                id=badge.id,
                name=badge.name,
                description=badge.description,
                icon_path=badge.icon_path,
                xp_value=badge.xp_value,
                earned=badge.id in earned_map,
                earned_at=earned_map.get(badge.id),
            )
        )

    return result


@router.get("/leaderboard", response_model=List[LeaderboardItem])
async def get_leaderboard(
    period: str = "weekly",
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get leaderboard for specified period"""
    # Try to get from pre-computed leaderboard
    entries = (
        db.query(LeaderboardEntry)
        .filter(LeaderboardEntry.period == period)
        .order_by(LeaderboardEntry.rank)
        .limit(limit)
        .all()
    )

    if entries:
        result = []
        for entry in entries:
            user = db.query(User).filter(User.id == entry.user_id).first()
            result.append(
                LeaderboardItem(
                    rank=entry.rank,
                    user_id=entry.user_id,
                    username=user.username if user else f"User #{entry.user_id}",
                    xp=entry.xp,
                    level=user.level if user else 1,
                )
            )
        return result

    # Fallback: compute from users table
    users = (
        db.query(User)
        .filter(User.active == True)
        .order_by(User.xp.desc())
        .limit(limit)
        .all()
    )

    result = []
    for idx, user in enumerate(users, 1):
        result.append(
            LeaderboardItem(
                rank=idx,
                user_id=user.id,
                username=user.username,
                xp=user.xp or 0,
                level=user.level or 1,
            )
        )

    return result


@router.get("/daily-goal", response_model=DailyGoalResponse)
async def get_daily_goal(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get today's daily goal"""
    today = date.today()

    goal = (
        db.query(DailyGoal)
        .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
        .first()
    )

    if not goal:
        # Check for default settings
        settings = (
            db.query(GamificationSettings)
            .filter(GamificationSettings.user_id == current_user.id)
            .first()
        )

        if settings and settings.default_goal_type and settings.default_goal_target:
            # Auto-create goal from defaults
            goal = DailyGoal(
                user_id=current_user.id,
                goal_date=today,
                goal_type=settings.default_goal_type,
                target_value=settings.default_goal_target,
                current_value=0,
                completed=False,
            )
            db.add(goal)
            db.commit()
            db.refresh(goal)
        else:
            # Return default placeholder if none set
            return DailyGoalResponse(
                id=None,
                goal_type="lessons",
                target_value=3,
                current_value=0,
                completed=False,
                goal_date=today,
            )

    return DailyGoalResponse(
        id=goal.id,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        completed=goal.completed,
        goal_date=goal.goal_date,
    )


@router.get("/daily-goal/progress")
async def get_daily_goal_progress(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get today's daily goal progress as a percentage.

    Returns progress data for dashboard widgets.
    """
    today = date.today()

    goal = (
        db.query(DailyGoal)
        .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
        .first()
    )

    if not goal:
        # Check for default settings
        settings = (
            db.query(GamificationSettings)
            .filter(GamificationSettings.user_id == current_user.id)
            .first()
        )

        if settings and settings.default_goal_type and settings.default_goal_target:
            return {
                "goal_type": settings.default_goal_type,
                "target": settings.default_goal_target,
                "current": 0,
                "percentage": 0,
                "completed": False,
                "has_goal": True,
            }
        else:
            return {
                "goal_type": None,
                "target": 0,
                "current": 0,
                "percentage": 0,
                "completed": False,
                "has_goal": False,
            }

    percentage = (
        min(100, round((goal.current_value / goal.target_value) * 100))
        if goal.target_value > 0
        else 0
    )

    return {
        "goal_type": goal.goal_type,
        "target": goal.target_value,
        "current": goal.current_value,
        "percentage": percentage,
        "completed": goal.completed,
        "has_goal": True,
    }


@router.post("/daily-goal", response_model=DailyGoalResponse)
async def set_daily_goal(
    goal_data: DailyGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update today's daily goal"""
    today = date.today()

    goal = (
        db.query(DailyGoal)
        .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
        .first()
    )

    if goal:
        goal.goal_type = goal_data.goal_type
        goal.target_value = goal_data.target_value
    else:
        goal = DailyGoal(
            user_id=current_user.id,
            goal_date=today,
            goal_type=goal_data.goal_type,
            target_value=goal_data.target_value,
            current_value=0,
            completed=False,
        )
        db.add(goal)

    # Handle save as default
    if goal_data.save_as_default:
        settings = (
            db.query(GamificationSettings)
            .filter(GamificationSettings.user_id == current_user.id)
            .first()
        )

        if settings:
            settings.default_goal_type = goal_data.goal_type
            settings.default_goal_target = goal_data.target_value
        else:
            settings = GamificationSettings(
                user_id=current_user.id,
                default_goal_type=goal_data.goal_type,
                default_goal_target=goal_data.target_value,
            )
            db.add(settings)

    db.commit()
    db.refresh(goal)

    return DailyGoalResponse(
        id=goal.id,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        completed=goal.completed,
        goal_date=goal.goal_date,
    )


@router.post("/award-xp")
async def award_xp(
    amount: int,
    reason: str = "activity",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Award XP to current user (internal use)"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="XP amount must be positive")

    current_user.xp = (current_user.xp or 0) + amount

    # Level up check (simple: 100 XP per level)
    new_level = (current_user.xp // 100) + 1
    if new_level > (current_user.level or 1):
        current_user.level = new_level

    # Update streak
    today = date.today()
    if current_user.last_activity_date:
        days_diff = (today - current_user.last_activity_date).days
        if days_diff == 1:
            current_user.current_streak = (current_user.current_streak or 0) + 1
            if current_user.current_streak > (current_user.longest_streak or 0):
                current_user.longest_streak = current_user.current_streak
        elif days_diff > 1:
            current_user.current_streak = 1
    else:
        current_user.current_streak = 1

    current_user.last_activity_date = today

    db.commit()

    return {
        "xp_awarded": amount,
        "total_xp": current_user.xp,
        "level": current_user.level,
        "streak": current_user.current_streak,
    }
