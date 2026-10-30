"""
Progress Tracking Service - Phase 1
Tracks student progress on study plans and content mastery
"""

from datetime import datetime, date
from typing import Dict, Any, List
from sqlalchemy import select, and_, func

from .database import get_db_service
from ..models import (
    StudentStudyPlan,
    MasteryNode,
    LearningSession,
    User,
    Badge,
    UserBadge,
    extract_phases,
)


class ProgressTrackingService:
    """Service for tracking student progress"""

    def __init__(self):
        self.db = get_db_service()

    def award_xp(self, user_id: int, amount: int) -> Dict[str, Any]:
        """
        Award XP to a user and handle level-ups.

        Args:
            user_id: User ID
            amount: XP amount to award

        Returns:
            Dict with new_xp, new_level, leveled_up
        """
        XP_PER_LEVEL = 1000
        try:
            with self.db.get_session() as session:
                user = session.get(User, user_id)
                if not user:
                    return {"new_xp": 0, "new_level": 1, "leveled_up": False}

                old_level = user.level or 1
                user.xp = (user.xp or 0) + amount
                new_level = (user.xp // XP_PER_LEVEL) + 1
                user.level = new_level

                session.commit()

                return {
                    "new_xp": user.xp,
                    "new_level": new_level,
                    "leveled_up": new_level > old_level,
                }
        except Exception:
            return {"new_xp": 0, "new_level": 1, "leveled_up": False}

    def check_and_award_badges(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Check badge criteria and award any newly earned badges.

        Args:
            user_id: User ID

        Returns:
            List of newly awarded badge dicts
        """
        newly_awarded = []
        try:
            with self.db.get_session() as session:
                user = session.get(User, user_id)
                if not user:
                    return []

                badges = (
                    session.execute(select(Badge).where(Badge.is_active == True))
                    .scalars()
                    .all()
                )

                earned_ids = set(
                    row[0]
                    for row in session.execute(
                        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
                    ).all()
                )

                for badge in badges:
                    if badge.id in earned_ids:
                        continue

                    if self._check_badge_criteria(session, user, badge):
                        new_user_badge = UserBadge(
                            user_id=user_id, badge_id=badge.id, earned_at=datetime.now()
                        )
                        session.add(new_user_badge)

                        if badge.xp_value > 0:
                            user.xp = (user.xp or 0) + badge.xp_value

                        newly_awarded.append(
                            {
                                "badge_id": badge.id,
                                "name": badge.name,
                                "description": badge.description,
                                "xp_value": badge.xp_value,
                            }
                        )

                if newly_awarded:
                    session.commit()

                return newly_awarded
        except Exception:
            return []

    def _check_badge_criteria(self, db_session, user: User, badge: Badge) -> bool:
        """Check if user meets badge criteria."""
        criteria = badge.criteria_value or {}
        ctype = badge.criteria_type

        if ctype == "xp_threshold":
            return (user.xp or 0) >= criteria.get("threshold", float("inf"))
        elif ctype == "streak":
            return (user.current_streak or 0) >= criteria.get("days", float("inf"))
        elif ctype == "level":
            return (user.level or 1) >= criteria.get("level", float("inf"))
        return False

    def get_study_plan_progress(
        self, student_id: int, study_plan_id: int
    ) -> Dict[str, Any]:
        """Get progress on a study plan"""
        try:
            with self.db.get_session() as session:
                from ..models import StudyPlan, StudyPlanContent

                assignment = (
                    session.execute(
                        select(StudentStudyPlan).where(
                            and_(
                                StudentStudyPlan.student_id == student_id,
                                StudentStudyPlan.study_plan_id == study_plan_id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if not assignment:
                    return {
                        "progress": 0,
                        "completion_pct": 0,
                        "current_phase": 0,
                        "lessons_completed": 0,
                        "total_items": 0,
                        "status": "not_started",
                    }

                # Get study plan to count total items
                plan = session.get(StudyPlan, study_plan_id)
                total_items = 0
                if plan and plan.phases:
                    # Use extract_phases to handle nested structure
                    phases = extract_phases(plan.phases)
                    for phase in phases:
                        if isinstance(phase, dict):
                            # Count items in each phase
                            items = phase.get("lessons", []) + phase.get("content", [])
                            total_items += len(items)

                # Also count content from StudyPlanContent table
                content_count = (
                    session.execute(
                        select(func.count(StudyPlanContent.id)).where(
                            StudyPlanContent.study_plan_id == study_plan_id
                        )
                    ).scalar()
                    or 0
                )
                total_items = max(total_items, content_count)

                # Count completed items
                lessons_completed = (
                    session.execute(
                        select(func.count(MasteryNode.id)).where(
                            and_(
                                MasteryNode.student_id == student_id,
                                MasteryNode.mastery_level >= 80,
                            )
                        )
                    ).scalar()
                    or 0
                )

                # Calculate completion percentage
                progress_pct = assignment.progress_percentage or 0
                if total_items > 0:
                    completion_pct = min(
                        100, int((lessons_completed / total_items) * 100)
                    )
                else:
                    completion_pct = int(progress_pct)

                return {
                    "progress": progress_pct,
                    "completion_pct": completion_pct,
                    "current_phase": assignment.current_phase or 0,
                    "lessons_completed": lessons_completed,
                    "total_items": total_items,
                    "status": assignment.status or "in_progress",
                }

        except Exception:
            return {
                "progress": 0,
                "completion_pct": 0,
                "current_phase": 0,
                "lessons_completed": 0,
                "total_items": 0,
                "status": "not_started",
            }

    def update_mastery(
        self, student_id: int, content_id: int, mastery_level: float
    ) -> bool:
        """Update mastery level for content"""
        try:
            level_int = max(0, min(100, int(round(mastery_level))))
            with self.db.get_session() as session:
                node = (
                    session.execute(
                        select(MasteryNode).where(
                            and_(
                                MasteryNode.student_id == student_id,
                                MasteryNode.content_id == content_id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if node:
                    node.mastery_level = level_int
                    node.last_reviewed = datetime.now()
                else:
                    node = MasteryNode(
                        student_id=student_id,
                        content_id=content_id,
                        mastery_level=level_int,
                    )
                    session.add(node)

                session.commit()
                return True

        except Exception:
            return False

    def get_topic_mastery(self, student_id: int, content_id: int) -> float:
        """Get mastery level for a specific content item"""
        try:
            with self.db.get_session() as session:
                node = (
                    session.execute(
                        select(MasteryNode).where(
                            and_(
                                MasteryNode.student_id == student_id,
                                MasteryNode.content_id == content_id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                return (
                    float(node.mastery_level)
                    if node and node.mastery_level is not None
                    else 0.0
                )

        except Exception:
            return 0.0

    def get_student_stats(self, student_id: int) -> Dict[str, Any]:
        """Get student statistics"""
        try:
            with self.db.get_session() as session:
                total_sessions = (
                    session.query(func.count(LearningSession.id))
                    .filter(LearningSession.student_id == student_id)
                    .scalar()
                    or 0
                )

                avg_mastery = (
                    session.query(func.avg(MasteryNode.mastery_level))
                    .filter(MasteryNode.student_id == student_id)
                    .scalar()
                    or 0
                )

                return {
                    "total_sessions": total_sessions,
                    "average_mastery": float(avg_mastery) if avg_mastery else 0,
                }

        except Exception:
            return {"total_sessions": 0, "average_mastery": 0}

    def update_progress(
        self, student_id: int, content_id: int, progress_value: float
    ) -> bool:
        """
        Update progress for a student on specific content

        Args:
            student_id: Student ID
            content_id: Content ID
            progress_value: Progress value (0-100)

        Returns:
            True if successful
        """
        return self.update_mastery(student_id, content_id, progress_value)

    def update_streak(self, user_id: int) -> Dict[str, int]:
        """
        Update user's activity streak

        Checks if the user has been active today and updates their streak accordingly.
        - If last activity was yesterday, increment streak
        - If last activity was today, maintain streak
        - If last activity was more than 1 day ago, reset to 1

        Args:
            user_id: User ID

        Returns:
            Dict with current_streak and longest_streak
        """
        try:
            with self.db.get_session() as session:
                user = session.get(User, user_id)

                if not user:
                    return {"current_streak": 0, "longest_streak": 0}

                today = date.today()
                last_activity = user.last_activity_date

                # If this is the first activity ever
                if not last_activity:
                    user.current_streak = 1
                    user.longest_streak = max(user.longest_streak, 1)
                    user.last_activity_date = today

                # If already active today, no change needed
                elif last_activity == today:
                    pass  # Streak unchanged

                # If last activity was yesterday, increment streak
                elif (today - last_activity).days == 1:
                    user.current_streak += 1
                    user.longest_streak = max(user.longest_streak, user.current_streak)
                    user.last_activity_date = today

                # If more than 1 day gap, reset streak to 1
                else:
                    user.current_streak = 1
                    user.last_activity_date = today

                session.commit()

                return {
                    "current_streak": user.current_streak,
                    "longest_streak": user.longest_streak,
                }

        except Exception:
            return {"current_streak": 0, "longest_streak": 0}

    def get_overall_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Get overall progress statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with total_time_hours, current_streak, topics_mastered, total_study_plans
        """
        try:
            with self.db.get_session() as session:
                # Get total study time from learning sessions
                total_minutes = (
                    session.execute(
                        select(func.sum(LearningSession.duration_minutes)).where(
                            LearningSession.student_id == user_id
                        )
                    ).scalar()
                    or 0
                )
                total_hours = round(float(total_minutes) / 60, 1)

                # Get streak
                streak_info = self.get_streak(user_id)
                current_streak = streak_info.get("current_streak", 0)

                # Get topics mastered (content with mastery >= 80%)
                topics_mastered = (
                    session.execute(
                        select(func.count(MasteryNode.id)).where(
                            and_(
                                MasteryNode.student_id == user_id,
                                MasteryNode.mastery_level >= 80,
                            )
                        )
                    ).scalar()
                    or 0
                )

                # Get total study plans assigned
                total_study_plans = (
                    session.execute(
                        select(func.count())
                        .select_from(StudentStudyPlan)
                        .where(StudentStudyPlan.student_id == user_id)
                    ).scalar()
                    or 0
                )

                return {
                    "total_time_hours": total_hours,
                    "current_streak": current_streak,
                    "topics_mastered": topics_mastered,
                    "total_study_plans": total_study_plans,
                }

        except Exception:
            return {
                "total_time_hours": 0,
                "current_streak": 0,
                "topics_mastered": 0,
                "total_study_plans": 0,
            }

    def get_streak(self, user_id: int) -> Dict[str, int]:
        """
        Get user's current streak information

        Args:
            user_id: User ID

        Returns:
            Dict with current_streak and longest_streak
        """
        try:
            with self.db.get_session() as session:
                user = session.get(User, user_id)

                if not user:
                    return {"current_streak": 0, "longest_streak": 0}

                # Check if streak is still valid (last activity was today or yesterday)
                if user.last_activity_date:
                    days_since_activity = (date.today() - user.last_activity_date).days

                    # Streak is broken if more than 1 day has passed
                    if days_since_activity > 1:
                        return {
                            "current_streak": 0,
                            "longest_streak": user.longest_streak,
                        }

                return {
                    "current_streak": user.current_streak or 0,
                    "longest_streak": user.longest_streak or 0,
                }

        except Exception:
            return {"current_streak": 0, "longest_streak": 0}


# Singleton
_progress_tracking_service = None


def get_progress_tracking_service() -> ProgressTrackingService:
    """Get or create progress tracking service singleton"""
    global _progress_tracking_service
    if _progress_tracking_service is None:
        _progress_tracking_service = ProgressTrackingService()
    return _progress_tracking_service
