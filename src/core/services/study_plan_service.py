"""
Study Plan Service - Phase 1
Manages study plans and student assignments
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import select

from .database import get_db_service
from ..models import StudyPlan, StudentStudyPlan, User


class StudyPlanService:
    """Service for managing study plans"""

    def __init__(self):
        self.db = get_db_service()
        self.logger = logging.getLogger(__name__)

    def create_study_plan(
        self,
        title: str,
        description: str,
        creator_id: int,
        phases: Optional[List[Dict[str, Any]]] = None,
        is_public: bool = False,
        grade_level: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Optional[StudyPlan]:
        """Create a new study plan"""
        try:
            with self.db.get_session() as session:
                plan = StudyPlan(
                    title=title,
                    description=description,
                    creator_id=creator_id,
                    phases=phases or [],
                    is_public=is_public,
                )

                session.add(plan)
                session.commit()
                session.refresh(plan)

                return plan

        except Exception:
            return None

    def assign_study_plan(
        self,
        study_plan_id: int,
        student_id: int,
        teacher_id: Optional[int] = None,
        due_date: Optional[datetime] = None,
    ) -> Optional[StudentStudyPlan]:
        """Assign a study plan to a student"""
        try:
            with self.db.get_session() as session:
                # Only use fields that exist in StudentStudyPlan model
                assignment = StudentStudyPlan(
                    study_plan_id=study_plan_id, student_id=student_id
                )

                session.add(assignment)
                session.commit()
                session.refresh(assignment)

                return assignment

        except Exception as e:
            (
                self.logger.error(f"Failed to assign study plan: {e}")
                if hasattr(self, "logger")
                else None
            )
            return None

    def get_study_plan(self, plan_id: int) -> Optional[StudyPlan]:
        """Get a study plan by ID"""
        try:
            with self.db.get_session() as session:
                return session.get(StudyPlan, plan_id)
        except Exception:
            return None

    def list_study_plans(
        self,
        user_id: Optional[int] = None,
        creator_id: Optional[int] = None,
        include_public: bool = True,
    ) -> List[StudyPlan]:
        """
        List study plans for a user

        Args:
            user_id: User ID (or use creator_id)
            creator_id: Alias for user_id for backward compatibility
            include_public: Include public plans

        Returns:
            List of StudyPlan objects
        """
        # Accept either user_id or creator_id
        actual_user_id = user_id if user_id is not None else creator_id

        if actual_user_id is None:
            return []

        try:
            with self.db.get_session() as session:
                # Get user to check role
                user = session.get(User, actual_user_id)

                if not user:
                    return []

                from ..roles import is_teacher

                is_teacher_role = is_teacher(user)

                if is_teacher_role:
                    stmt = select(StudyPlan).where(
                        StudyPlan.creator_id == actual_user_id
                    )
                else:
                    # Get plans assigned to student or created by student
                    stmt = (
                        select(StudyPlan)
                        .join(
                            StudentStudyPlan,
                            StudyPlan.id == StudentStudyPlan.study_plan_id,
                            isouter=True,
                        )
                        .where(
                            (StudentStudyPlan.student_id == actual_user_id)
                            | (StudyPlan.creator_id == actual_user_id)
                        )
                        .distinct()
                    )

                plans = session.execute(stmt).scalars().all()
                return list(plans)

        except Exception:
            return []

    def get_student_assignments(self, student_id: int) -> List[StudentStudyPlan]:
        """
        Get all study plan assignments for a student.

        Args:
            student_id: Student user ID

        Returns:
            List of StudentStudyPlan objects with study_plan relationship loaded
        """
        try:
            with self.db.get_session() as session:
                from sqlalchemy.orm import joinedload

                stmt = (
                    select(StudentStudyPlan)
                    .options(joinedload(StudentStudyPlan.study_plan))
                    .where(StudentStudyPlan.student_id == student_id)
                )

                assignments = session.execute(stmt).scalars().all()
                return list(assignments)

        except Exception as e:
            self.logger.error(f"Failed to get student assignments: {e}")
            return []

    def get_assigned_students(self, study_plan_id: int) -> List[Dict[str, Any]]:
        """Get all students assigned to a study plan"""
        try:
            with self.db.get_session() as session:
                stmt = (
                    select(StudentStudyPlan, User)
                    .join(User, StudentStudyPlan.student_id == User.id)
                    .where(StudentStudyPlan.study_plan_id == study_plan_id)
                )

                results = session.execute(stmt).all()

                return [
                    {"student": result.User, "assignment": result.StudentStudyPlan}
                    for result in results
                ]

        except Exception:
            return []

    def assign_to_student(
        self, study_plan_id: int, student_id: int
    ) -> Optional[StudentStudyPlan]:
        """
        Assign a study plan to a student (alias for assign_study_plan).

        Args:
            study_plan_id: Study plan ID
            student_id: Student user ID

        Returns:
            StudentStudyPlan assignment or None if failed
        """
        return self.assign_study_plan(study_plan_id, student_id)

    def update_progress(
        self, assignment_id: int, progress: float, current_phase: Optional[int] = None
    ) -> bool:
        """Update student progress on an assignment"""
        try:
            with self.db.get_session() as session:
                assignment = session.get(StudentStudyPlan, assignment_id)

                if not assignment:
                    return False

                assignment.progress_percentage = progress

                if current_phase is not None:
                    assignment.current_phase = current_phase

                session.commit()
                return True

        except Exception:
            return False


# Singleton
_study_plan_service = None


def get_study_plan_service() -> StudyPlanService:
    """Get or create study plan service singleton"""
    global _study_plan_service
    if _study_plan_service is None:
        _study_plan_service = StudyPlanService()
    return _study_plan_service
