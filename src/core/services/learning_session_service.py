"""
Learning Session Service - Phase 1
Tracks student learning sessions and study time
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_

from .database import get_db_service
from ..models import LearningSession


class LearningSessionService:
    """Service for managing learning sessions"""

    def __init__(self):
        self.db = get_db_service()

    def start_session(
        self,
        student_id: int,
        content_id: Optional[int] = None,
        study_plan_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> LearningSession:
        """Start a new learning session"""
        with self.db.get_session() as session:
            # End any active sessions first
            active = self.get_active_session(student_id)
            if active:
                if active.id is not None:
                    self.end_session(active.id, completion_status="interrupted")

            learning_session = LearningSession(
                student_id=student_id,
                content_id=content_id,
                start_time=datetime.now(),
                notes=notes,
            )

            session.add(learning_session)
            session.commit()
            session.refresh(learning_session)

            return learning_session

    def end_session(
        self,
        session_id: int,
        completion_status: str = "completed",
        notes: Optional[str] = None,
    ) -> bool:
        """End a learning session"""
        try:
            with self.db.get_session() as session:
                learning_session = session.get(LearningSession, session_id)

                if not learning_session:
                    return False

                learning_session.end_time = datetime.now()
                learning_session.notes = notes or learning_session.notes
                learning_session.completion_status = completion_status
                learning_session.duration_minutes = (
                    learning_session.calculate_duration()
                )

                session.commit()
                return True

        except Exception:
            return False

    def get_active_session(self, student_id: int) -> Optional[LearningSession]:
        """Get active session for student"""
        try:
            with self.db.get_session() as session:
                stmt = (
                    select(LearningSession)
                    .where(
                        and_(
                            LearningSession.student_id == student_id,
                            LearningSession.end_time.is_(None),
                        )
                    )
                    .order_by(LearningSession.start_time.desc())
                )

                return session.execute(stmt).scalars().first()

        except Exception:
            return None

    def get_session_history(
        self, student_id: int, limit: int = 20
    ) -> List[LearningSession]:
        """Get session history for student"""
        try:
            with self.db.get_session() as session:
                stmt = (
                    select(LearningSession)
                    .where(LearningSession.student_id == student_id)
                    .order_by(LearningSession.start_time.desc())
                    .limit(limit)
                )

                sessions = session.execute(stmt).scalars().all()
                return list(sessions)

        except Exception:
            return []


# Singleton
_learning_session_service = None


def get_learning_session_service() -> LearningSessionService:
    """Get or create learning session service singleton"""
    global _learning_session_service
    if _learning_session_service is None:
        _learning_session_service = LearningSessionService()
    return _learning_session_service
