"""
Gamification API Routes

Provides endpoints for Phase 3 gamification features:
- XP, levels, streaks
- Badges and achievements
- Leaderboards
- Daily goals
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.services.temporal_service import local_date, record_activity_day, user_timezone, record_goal_day, goal_day_info, last_activity_day
from src.api.policies import teacher_student_ids
from src.core.roles import is_admin, is_student, is_teacher
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
    timezone: str = "UTC"
    day_provenance: str = "legacy_unknown"


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
    """Participation feedback ranked only within the viewer's authorized scope."""

    rank: int
    user_id: int
    username: str
    xp: int
    level: int
    metric_type: str = "participation"
    rank_scope: str = "visible_users"


class DailyGoalResponse(BaseModel):
    """Daily goal status"""

    id: Optional[int]
    goal_type: str
    target_value: int
    current_value: int
    completed: bool
    goal_date: date
    timezone: str = "UTC"
    day_timezone: Optional[str] = None
    day_provenance: str = "legacy_unknown"
    mixed_day_policy: bool = False


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
        timezone=user_timezone(current_user),
        day_provenance="recorded" if last_activity_day(current_user) else "legacy_unknown",
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


def _leaderboard_users(db: Session, user: User):
    """Apply the same enrollment boundary to live and cached participation data."""
    query = db.query(User.id).filter(User.active.is_(True))
    if is_admin(user):
        return query
    if is_teacher(user):
        return query.filter(User.id.in_(teacher_student_ids(db, user.id)))
    if is_student(user):
        return query.filter(User.id == user.id)
    return query.filter(User.id.in_([]))


@router.get("/leaderboard", response_model=List[LeaderboardItem])
async def get_leaderboard(
    period: str = "weekly",
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return scoped participation XP, never a global student directory/rank."""
    visible_users = _leaderboard_users(db, current_user)
    entries = (
        db.query(LeaderboardEntry, User)
        .join(User, User.id == LeaderboardEntry.user_id)
        .filter(LeaderboardEntry.period == period, User.id.in_(visible_users))
        .order_by(LeaderboardEntry.rank, User.id)
        .limit(limit)
        .all()
    )
    if entries:
        return [
            LeaderboardItem(
                rank=rank,
                user_id=user.id,
                username=user.username,
                xp=entry.xp,
                level=user.level or 1,
            )
            for rank, (entry, user) in enumerate(entries, 1)
        ]
    users = (
        db.query(User)
        .filter(User.id.in_(visible_users))
        .order_by(User.xp.desc(), User.id)
        .limit(limit)
        .all()
    )
    return [
        LeaderboardItem(
            rank=rank,
            user_id=user.id,
            username=user.username,
            xp=user.xp or 0,
            level=user.level or 1,
        )
        for rank, user in enumerate(users, 1)
    ]


@router.get("/daily-goal", response_model=DailyGoalResponse)
async def get_daily_goal(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get today's daily goal"""
    current_user = db.get(User, current_user.id)
    today = local_date(current_user)

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
            db.flush()
            record_goal_day(current_user, goal, new=True)
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
                **goal_day_info(current_user),
            )

    return DailyGoalResponse(
        id=goal.id,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        completed=goal.completed,
        goal_date=goal.goal_date,
        **goal_day_info(current_user, goal),
    )


@router.get("/daily-goal/progress")
async def get_daily_goal_progress(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get today's daily goal progress as a percentage.

    Returns progress data for dashboard widgets.
    """
    today = local_date(current_user)

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
                **goal_day_info(current_user),
            }
        else:
            return {
                "goal_type": None,
                "target": 0,
                "current": 0,
                "percentage": 0,
                "completed": False,
                "has_goal": False,
                **goal_day_info(current_user),
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
        **goal_day_info(current_user, goal),
    }


@router.post("/daily-goal", response_model=DailyGoalResponse)
async def set_daily_goal(
    goal_data: DailyGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update today's daily goal"""
    current_user = db.get(User, current_user.id)
    today = local_date(current_user)

    goal = (
        db.query(DailyGoal)
        .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
        .first()
    )

    new_goal = goal is None
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

    db.flush()
    record_goal_day(current_user, goal, new=new_goal)

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
        **goal_day_info(current_user, goal),
    )


def award_activity_xp(db: Session, user_id: int, amount: int) -> None:
    """Record a server-verified reward inside the activity's transaction.

    Call only after claiming a previously unfinished activity. The caller owns
    commit/rollback, so activity completion and its reward cannot split.
    """
    db.query(User).filter(User.id == user_id).update(
        {User.xp: func.coalesce(User.xp, 0) + amount}, synchronize_session=False
    )
    user = db.get(User, user_id)
    db.refresh(user)
    record_activity_day(user)
    user.level = (user.xp // 1000) + 1
    from src.core.services.progress_tracking_service import ProgressTrackingService

    earned_ids = {row[0] for row in db.query(UserBadge.badge_id).filter_by(user_id=user_id)}
    for badge in db.query(Badge).filter(Badge.is_active == True).all():
        if badge.id in earned_ids:
            continue
        if ProgressTrackingService._check_badge_criteria(None, db, user, badge):
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            user.xp += max(0, badge.xp_value or 0)
    user.level = (user.xp // 1000) + 1


@router.post("/award-xp")
async def award_xp(
    amount: int,
    reason: str = "activity",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject arbitrary client rewards; verified activity routes award XP."""
    raise HTTPException(
        status_code=403,
        detail="XP is awarded only for verified server-side activity",
    )
