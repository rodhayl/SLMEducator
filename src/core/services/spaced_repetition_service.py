"""
Spaced Repetition Service for SLMEducator - Phase 1: Adaptive AI Tutor

Implements spaced repetition algorithm (SM-2) for optimal content review scheduling.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import MasteryNode, Content
from .database import DatabaseService


class SpacedRepetitionService:
    """Service for managing spaced repetition and review scheduling"""

    def __init__(self, db_service: DatabaseService):
        """Initialize spaced repetition service"""
        self.db = db_service
        self.logger = logging.getLogger(__name__)

    def calculate_next_review(
        self, mastery_level: int, review_count: int, last_performance: int
    ) -> datetime:
        """
        Calculate next review date using simplified SM-2 algorithm

        Args:
            mastery_level: Current mastery level (0-100)
            review_count: Number of times reviewed
            last_performance: Last performance score (0-100)

        Returns:
            Next review due date
        """
        # Base intervals in days based on review count
        intervals = [1, 3, 7, 14, 30, 60, 120]

        # Adjust interval based on performance
        if last_performance >= 80:
            # Good performance - extend interval
            multiplier = 1.5
        elif last_performance >= 60:
            # Moderate performance - standard interval
            multiplier = 1.0
        else:
            # Poor performance - shorten interval
            multiplier = 0.5

        # Get base interval
        interval_index = min(review_count, len(intervals) - 1)
        base_interval = intervals[interval_index]

        # Calculate final interval
        final_interval = int(base_interval * multiplier)

        # Return next review date
        return datetime.now() + timedelta(days=final_interval)

    def get_due_reviews(self, student_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get content items due for review

        Args:
            student_id: Student ID
            limit: Maximum number of items to return

        Returns:
            List of content items with review metadata
        """
        with self.db.get_session() as session:
            # Query mastery nodes due for review
            stmt = (
                select(MasteryNode)
                .where(
                    MasteryNode.student_id == student_id,
                    MasteryNode.next_review_due <= datetime.now(),
                )
                .order_by(MasteryNode.next_review_due)
                .limit(limit)
            )

            try:
                nodes = session.execute(stmt).scalars().all()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error fetching due reviews: {e}")
                return []

            # Build result list with content details
            results = []
            for node in nodes:
                content = session.get(Content, node.content_id)
                if content:
                    content_type = (
                        content.content_type.value
                        if content.content_type is not None
                        else ""
                    )
                    results.append(
                        {
                            "mastery_node_id": node.id,
                            "content_id": content.id,
                            "content_title": content.title,
                            "content_type": content_type,
                            "mastery_level": node.mastery_level,
                            "review_count": node.review_count,
                            "last_reviewed": node.last_reviewed,
                            "next_review_due": node.next_review_due,
                            "days_overdue": (
                                (datetime.now() - node.next_review_due).days
                                if node.next_review_due
                                else 0
                            ),
                        }
                    )

            return results

    def update_review_outcome(
        self, student_id: int, content_id: int, performance_score: int
    ) -> bool:
        """
        Update mastery node after a review session

        Args:
            student_id: Student ID
            content_id: Content ID
            performance_score: Performance score (0-100)

        Returns:
            True if successful
        """
        with self.db.get_session() as session:
            # Get or create mastery node
            stmt = select(MasteryNode).where(
                MasteryNode.student_id == student_id,
                MasteryNode.content_id == content_id,
            )
            try:
                node = session.execute(stmt).scalar_one_or_none()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error fetching mastery node: {e}")
                return False

            if not node:
                # Create new node
                node = MasteryNode(
                    student_id=student_id,
                    content_id=content_id,
                    mastery_level=performance_score,
                    last_reviewed=datetime.now(),
                    review_count=1,
                )
                session.add(node)
            else:
                old_mastery = node.mastery_level or 0
                node.mastery_level = int(0.7 * performance_score + 0.3 * old_mastery)
                node.last_reviewed = datetime.now()
                review_count = node.review_count or 0
                node.review_count = review_count + 1

            # Calculate next review date
            mastery_level = node.mastery_level or 0
            review_count = node.review_count or 0
            node.next_review_due = self.calculate_next_review(
                mastery_level, review_count, performance_score
            )

            try:
                session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating review outcome: {e}")
                session.rollback()
                return False
            return True

    def get_student_mastery_overview(self, student_id: int) -> Dict[str, Any]:
        """
        Get overview of student's mastery across all content

        Args:
            student_id: Student ID

        Returns:
            Dictionary with mastery statistics
        """
        with self.db.get_session() as session:
            stmt = select(MasteryNode).where(MasteryNode.student_id == student_id)
            try:
                nodes = session.execute(stmt).scalars().all()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error fetching mastery overview: {e}")
                return {
                    "total_items": 0,
                    "average_mastery": 0,
                    "items_mastered": 0,
                    "items_in_progress": 0,
                    "items_due_review": 0,
                }

            if not nodes:
                return {
                    "total_items": 0,
                    "average_mastery": 0,
                    "items_mastered": 0,
                    "items_in_progress": 0,
                    "items_due_review": 0,
                }

            total_mastery = sum((node.mastery_level or 0) for node in nodes)
            items_mastered = sum(1 for node in nodes if (node.mastery_level or 0) >= 80)
            items_in_progress = sum(
                1 for node in nodes if 40 <= (node.mastery_level or 0) < 80
            )
            items_due = sum(
                1
                for node in nodes
                if node.next_review_due and node.next_review_due <= datetime.now()
            )

            return {
                "total_items": len(nodes),
                "average_mastery": int(total_mastery / len(nodes)),
                "items_mastered": items_mastered,
                "items_in_progress": items_in_progress,
                "items_due_review": items_due,
            }

    def initialize_content_for_review(self, student_id: int, content_id: int) -> bool:
        """
        Initialize a content item for spaced repetition tracking

        Args:
            student_id: Student ID
            content_id: Content ID

        Returns:
            True if successful
        """
        with self.db.get_session() as session:
            # Check if already exists
            stmt = select(MasteryNode).where(
                MasteryNode.student_id == student_id,
                MasteryNode.content_id == content_id,
            )
            try:
                existing = session.execute(stmt).scalar_one_or_none()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error checking existing mastery node: {e}")
                return False

            if existing:
                return True  # Already initialized

            # Create new node with initial review in 1 day
            node = MasteryNode(
                student_id=student_id,
                content_id=content_id,
                mastery_level=0,
                next_review_due=datetime.now() + timedelta(days=1),
                review_count=0,
            )
            session.add(node)
            try:
                session.commit()
            except SQLAlchemyError as e:
                self.logger.error(
                    f"Database error initializing content for review: {e}"
                )
                session.rollback()
                return False
            return True

    def get_all_mastery_levels(self, student_id: int) -> Dict[int, int]:
        """
        Get mastery levels for all content items the student has interacted with.

        Args:
            student_id: Student ID

        Returns:
            Dictionary mapping content_id to mastery_level (0-100)
        """
        with self.db.get_session() as session:
            stmt = select(MasteryNode).where(MasteryNode.student_id == student_id)
            try:
                nodes = session.execute(stmt).scalars().all()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error fetching mastery levels: {e}")
                return {}

            return {
                node.content_id: (node.mastery_level or 0)
                for node in nodes
                if node.content_id is not None
            }


# Singleton instance
_spaced_repetition_service = None


def get_spaced_repetition_service() -> SpacedRepetitionService:
    """Get or create singleton spaced repetition service instance"""
    global _spaced_repetition_service
    if _spaced_repetition_service is None:
        from .database import get_db_service

        _spaced_repetition_service = SpacedRepetitionService(get_db_service())
    return _spaced_repetition_service
