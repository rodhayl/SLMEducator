"""
Content Service - Phase 1
Handles content creation, retrieval, and management
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select

from .database import get_db_service
from ..models.models import Content, ContentType


class ContentService:
    """Service for managing educational content"""

    def __init__(self):
        self.db = get_db_service()
        self.logger = logging.getLogger(__name__)

    def create_content(
        self,
        title: str,
        content_type: ContentType,
        creator_id: int,
        content_data: Optional[Dict[str, Any]] = None,
        study_plan_id: Optional[int] = None,
    ) -> Optional[Content]:
        """Create new content"""
        try:
            with self.db.get_session() as session:
                content = Content(
                    title=title,
                    content_type=content_type,
                    creator_id=creator_id,
                    study_plan_id=study_plan_id,
                )

                if content_data:
                    content.set_encrypted_content_data(content_data)

                session.add(content)
                session.commit()
                session.refresh(content)

                return content

        except Exception as e:
            self.logger.error(f"Error creating content '{title}': {e}")
            return None

    def get_content(self, content_id: int) -> Optional[Content]:
        """Get content by ID"""
        try:
            with self.db.get_session() as session:
                return session.get(Content, content_id)
        except Exception as e:
            self.logger.error(f"Error fetching content {content_id}: {e}")
            return None

    def update_content(
        self, content_id: int, updates: Dict[str, Any]
    ) -> Optional[Content]:
        """Update content"""
        try:
            with self.db.get_session() as session:
                content = session.get(Content, content_id)

                if not content:
                    return None

                for key, value in updates.items():
                    if key == "content_data":
                        content.set_encrypted_content_data(value)
                    elif hasattr(content, key):
                        setattr(content, key, value)

                session.commit()
                session.refresh(content)

                return content

        except Exception as e:
            self.logger.error(f"Error updating content {content_id}: {e}")
            return None

    def delete_content(self, content_id: int) -> bool:
        """Delete content"""
        try:
            with self.db.get_session() as session:
                content = session.get(Content, content_id)

                if not content:
                    return False

                session.delete(content)
                session.commit()

                return True

        except Exception as e:
            self.logger.error(f"Error deleting content {content_id}: {e}")
            return False

    def list_content(
        self,
        creator_id: Optional[int] = None,
        study_plan_id: Optional[int] = None,
        content_type: Optional[ContentType] = None,
    ) -> List[Content]:
        """List content with filters"""
        try:
            with self.db.get_session() as session:
                stmt = select(Content)

                if creator_id:
                    stmt = stmt.where(Content.creator_id == creator_id)

                if study_plan_id:
                    stmt = stmt.where(Content.study_plan_id == study_plan_id)

                if content_type:
                    stmt = stmt.where(Content.content_type == content_type)

                content_list = session.execute(stmt).scalars().all()
                return list(content_list)

        except Exception as e:
            self.logger.error(f"Error listing content: {e}")
            return []

    def search_content(self, query: str) -> List[Content]:
        """Search content by title"""
        try:
            with self.db.get_session() as session:
                stmt = select(Content).where(Content.title.ilike(f"%{query}%"))

                results = session.execute(stmt).scalars().all()
                return list(results)

        except Exception as e:
            self.logger.error(f"Error searching content for '{query}': {e}")
            return []


# Singleton
_content_service = None


def get_content_service() -> ContentService:
    """Get or create content service singleton"""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service
