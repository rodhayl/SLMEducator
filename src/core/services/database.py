"""
Database service for SLMEducator
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, cast
from weakref import WeakSet
import weakref
from sqlalchemy import create_engine, event, select, func, and_, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from ..models import (
    Base,
    User,
    AIModelConfiguration,
    StudyPlan,
    Content,
    StudentStudyPlan,
    StudyPlanContent,
    LearningSession,
    TeacherMessage,
    AuditLog,
    LoggingConfiguration,
    ApplicationConfiguration,
    AuthAttempt,
)
from .settings_config_service import SettingsConfigService


class DatabaseService:
    """Database service for managing SQLite connections and sessions"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database service"""
        if db_path is None:
            db_path = os.getenv("SLM_DB_PATH", "slm_educator.db")

        self.db_path = Path(db_path)
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker[Session]] = None
        self._session: Optional[Session] = None
        # Track open sessions to ensure cleanup in tests
        self._open_sessions: WeakSet[Session] = WeakSet()
        self.settings_service = SettingsConfigService()

        # Import logging service after initialization to avoid circular imports
        from .logging import get_logging_service

        self.logger = get_logging_service().get_logger("database")

        # Configure SQLite for better performance
        self._setup_engine()
        self._create_tables()

    def _setup_engine(self):
        """Set up SQLAlchemy engine with SQLite optimizations"""

        # Use WAL mode for better concurrency
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA mmap_size=30000000000")  # 30GB mmap
                cursor.close()

        # Create engine
        database_url = f"sqlite:///{self.db_path}"

        if os.getenv("SLM_TEST_MODE"):
            # Use file-based database for tests to allow session sharing
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        else:
            # Ensure database directory exists for file-based databases
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(
                database_url,
                echo=bool(os.getenv("SLM_DEV_MODE")),
                pool_pre_ping=True,
                pool_recycle=3600,
            )

        # Ensure engine is disposed when DatabaseService is garbage collected
        try:
            weakref.finalize(self, self.engine.dispose)
        except Exception:
            pass

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def _create_tables(self):
        """Create all database tables"""
        if self.engine is None:
            raise RuntimeError("Database engine not initialized")
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session"""
        if self.SessionLocal is None:
            raise RuntimeError("Database session factory not initialized")
        session = self.SessionLocal()
        try:
            self._open_sessions.add(session)
        except Exception:
            # If session is not weakrefable, ignore tracking
            pass
        return session

    @property
    def session(self) -> Session:
        """Get a stable database session (compatibility property for services/tests).

        NOTE: `SessionLocal()` returns a new Session each call; exposing that directly
        makes patterns like `db.session.add(); db.session.commit(); db.session.refresh()`
        fail because they operate on different Session instances. This property returns
        a memoized session for the lifetime of the DatabaseService instance.
        """
        if self._session is not None:
            return self._session

        if self.SessionLocal is None:
            raise RuntimeError("Database session factory not initialized")
        session = self.SessionLocal()
        try:
            self._open_sessions.add(session)
        except Exception:
            pass
        self._session = session
        return session

    def get_connection(self):
        """Get a raw database connection"""
        if self.engine is None:
            raise RuntimeError("Database engine not initialized")
        return self.engine.connect()

    def close(self):
        """Close database connections"""
        if self.engine:
            # Close any open sessions tracked
            try:
                if self._session is not None:
                    try:
                        self._session.close()
                    except Exception:
                        pass
                    self._session = None

                for session in list(self._open_sessions):
                    try:
                        session.close()
                    except Exception:
                        pass
            except Exception:
                # Ignore session cleanup failures
                pass
            self.engine.dispose()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def backup_database(self, backup_path: str):
        """Create a backup of the database"""
        if not self.engine:
            return

        backup_engine = create_engine(f"sqlite:///{backup_path}")

        # Copy schema and data
        with self.engine.connect() as source_conn:
            with backup_engine.connect() as dest_conn:
                source_conn.connection.backup(dest_conn.connection)

        backup_engine.dispose()

    def get_database_stats(self) -> dict:
        """Get database statistics"""
        if not self.engine:
            return {}

        stats = {}
        with self.engine.connect() as conn:
            # Get table row counts
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]

            for table in tables:
                if table.startswith("sqlite_"):
                    continue

                # Validate table name to prevent SQL injection
                from ..security_utils import validate_table_name

                if not validate_table_name(table):
                    continue

                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[table] = count_result.scalar()

        return stats

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self.get_session() as session:
            return session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.get_session() as session:
            return session.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with self.get_session() as session:
            return session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()

    def create_user(self, user: User) -> User:
        """Create a new user"""
        try:
            with self.get_session() as session:
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
        except Exception as e:
            from core.exceptions import DatabaseError

            raise DatabaseError(f"Failed to create user: {str(e)}") from e

    def create_study_plan(self, study_plan: "StudyPlan") -> "StudyPlan":
        """Create a new study plan"""
        with self.get_session() as session:
            session.add(study_plan)
            session.commit()
            session.refresh(study_plan)
            return study_plan

    def create_content(self, content: "Content") -> "Content":
        """Create a new content"""
        with self.get_session() as session:
            session.add(content)
            session.commit()
            session.refresh(content)
            return content

    def create_student_study_plan(
        self, assignment: "StudentStudyPlan"
    ) -> "StudentStudyPlan":
        """Assign a study plan to a student"""
        with self.get_session() as session:
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            return assignment

    def assign_study_plan_to_student(
        self, student_id: int, study_plan_id: int
    ) -> "StudentStudyPlan":
        """Assign a study plan to a student"""
        assignment = StudentStudyPlan(
            student_id=student_id,
            study_plan_id=study_plan_id,
            assigned_at=datetime.now(),
        )
        return self.create_student_study_plan(assignment)

    def get_study_plan_by_id(self, study_plan_id: int) -> Optional["StudyPlan"]:
        """Get study plan by ID"""
        with self.get_session() as session:
            return session.execute(
                select(StudyPlan).where(StudyPlan.id == study_plan_id)
            ).scalar_one_or_none()

    def create_learning_session(self, session_data: dict) -> "LearningSession":
        """Create a learning session"""
        with self.get_session() as session:
            learning_session = LearningSession(**session_data)
            session.add(learning_session)
            session.commit()
            session.refresh(learning_session)
            return learning_session

    def create_teacher_message(self, message_data: dict) -> "TeacherMessage":
        """Create a teacher message"""
        with self.get_session() as session:
            message = TeacherMessage(**message_data)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def create_audit_log(self, audit_data: dict) -> "AuditLog":
        """Create an audit log entry"""
        with self.get_session() as session:
            audit_log = AuditLog(**audit_data)
            session.add(audit_log)
            session.commit()
            session.refresh(audit_log)
            return audit_log

    def get_ai_config(self) -> Optional[AIModelConfiguration]:
        """Get AI configuration from database"""
        with self.get_session() as session:
            return session.execute(select(AIModelConfiguration)).scalars().first()

    def create_ai_config(self, config_data: dict) -> AIModelConfiguration:
        """Create new AI configuration"""
        with self.get_session() as session:
            config = AIModelConfiguration(**config_data)
            session.add(config)
            session.commit()
            session.refresh(config)
            return config

    def update_ai_config(
        self, config_id: int, config_data: dict
    ) -> Optional[AIModelConfiguration]:
        """Update existing AI configuration"""
        with self.get_session() as session:
            config = session.execute(
                select(AIModelConfiguration).where(AIModelConfiguration.id == config_id)
            ).scalar_one_or_none()
            if config:
                for key, value in config_data.items():
                    setattr(config, key, value)
                session.commit()
                session.refresh(config)
            return config

    def get_logging_config(self) -> dict:
        """Get logging configuration"""
        try:
            with self.get_session() as session:
                # Get system-wide config (user_id is None) or fallback to defaults
                config = session.execute(
                    select(LoggingConfiguration).where(
                        LoggingConfiguration.user_id.is_(None)
                    )
                ).scalar_one_or_none()

                if config:
                    return {
                        "level": config.level,
                        "max_file_size_mb": config.max_file_size_mb,
                        "backup_count": config.backup_count,
                        "log_to_console": config.log_to_console,
                        "log_to_file": config.log_to_file,
                        "structured_logging": config.structured_logging,
                    }
                else:
                    # Return defaults if no config exists
                    return {
                        "level": "INFO",
                        "max_file_size_mb": 10,
                        "backup_count": 5,
                        "log_to_console": True,
                        "log_to_file": True,
                        "structured_logging": True,
                    }
        except Exception as e:
            self.logger.error(f"Failed to get logging config: {e}")
            # Return defaults on error
            return {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "log_to_console": True,
                "log_to_file": True,
                "structured_logging": True,
            }

    def update_logging_config(self, config: dict):
        """Update logging configuration"""
        try:
            with self.get_session() as session:
                # Get or create system-wide config (user_id is None)
                db_config = session.execute(
                    select(LoggingConfiguration).where(
                        LoggingConfiguration.user_id.is_(None)
                    )
                ).scalar_one_or_none()

                if not db_config:
                    db_config = LoggingConfiguration(user_id=None)
                    session.add(db_config)

                # Update configuration
                db_config.level = config.get("level", "INFO")
                db_config.max_file_size_mb = config.get("max_file_size_mb", 10)
                db_config.backup_count = config.get("backup_count", 5)
                db_config.log_to_console = config.get("log_to_console", True)
                db_config.log_to_file = config.get("log_to_file", True)
                db_config.structured_logging = config.get("structured_logging", True)

                session.commit()
                self.logger.info("Logging configuration updated successfully")

        except Exception as e:
            self.logger.error(f"Failed to update logging config: {e}")
            raise

    def get_application_config(self) -> dict:
        """Get application configuration"""
        try:
            with self.get_session() as session:
                # Get system-wide config (user_id is None) or fallback to defaults
                config = session.execute(
                    select(ApplicationConfiguration).where(
                        ApplicationConfiguration.user_id.is_(None)
                    )
                ).scalar_one_or_none()

                if config:
                    return {
                        "theme": config.theme,
                        "font_size": config.font_size,
                        "auto_save": config.auto_save,
                        "cache_size_mb": config.cache_size_mb,
                        "language": config.language,
                        "date_format": config.date_format,
                        "timezone": config.timezone,
                        "enable_tooltips": config.enable_tooltips,
                        "enable_animations": config.enable_animations,
                        "show_welcome_screen": config.show_welcome_screen,
                    }
                else:
                    # Return defaults if no config exists
                    return {
                        "theme": "auto",
                        "font_size": "medium",
                        "auto_save": True,
                        "cache_size_mb": 100,
                        "language": "en",
                        "date_format": "%Y-%m-%d",
                        "timezone": "UTC",
                        "enable_tooltips": True,
                        "enable_animations": True,
                        "show_welcome_screen": True,
                    }
        except Exception as e:
            self.logger.error(f"Failed to get application config: {e}")
            # Return defaults on error
            return {
                "theme": "auto",
                "font_size": "medium",
                "auto_save": True,
                "cache_size_mb": 100,
                "language": "en",
                "date_format": "%Y-%m-%d",
                "timezone": "UTC",
                "enable_tooltips": True,
                "enable_animations": True,
                "show_welcome_screen": True,
            }

    def update_application_config(self, config: dict):
        """Update application configuration"""
        try:
            with self.get_session() as session:
                # Get or create system-wide config (user_id is None)
                db_config = session.execute(
                    select(ApplicationConfiguration).where(
                        ApplicationConfiguration.user_id.is_(None)
                    )
                ).scalar_one_or_none()

                if not db_config:
                    db_config = ApplicationConfiguration(user_id=None)
                    session.add(db_config)

                # Update configuration
                db_config.theme = config.get("theme", "auto")
                db_config.font_size = config.get("font_size", "medium")
                db_config.auto_save = config.get("auto_save", True)
                db_config.cache_size_mb = config.get("cache_size_mb", 100)
                db_config.language = config.get("language", "en")
                db_config.date_format = config.get("date_format", "%Y-%m-%d")
                db_config.timezone = config.get("timezone", "UTC")
                db_config.enable_tooltips = config.get("enable_tooltips", True)
                db_config.enable_animations = config.get("enable_animations", True)
                db_config.show_welcome_screen = config.get("show_welcome_screen", True)

                session.commit()
                self.logger.info("Application configuration updated successfully")

        except Exception as e:
            self.logger.error(f"Failed to update application config: {e}")
            raise

    def reset_all_config_to_defaults(self):
        """Reset all configuration to defaults"""
        with self.get_session() as session:
            # Reset AI config to defaults
            ai_config = session.execute(select(AIModelConfiguration)).scalars().first()
            if ai_config:
                ai_config.provider = self.settings_service.get(
                    "ai", "default.provider", "ollama"
                )
                ai_config.model_name = self.settings_service.get(
                    "ai", "default.model", "llama2"
                )
                ai_config.base_url = self.settings_service.get(
                    "ai", "ollama.url", "http://localhost:11434"
                )
                ai_config.api_key = None
                ai_config.model_parameters = {
                    "temperature": self.settings_service.get_float(
                        "ai", "default.temperature", 0.7
                    ),
                    "max_tokens": self.settings_service.get_int(
                        "ai", "default.max_tokens", 1000
                    ),
                }

            session.commit()

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up learning sessions older than specified days"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)

        with self.get_session() as session:
            # Delete old learning sessions
            old_sessions = (
                session.execute(
                    select(LearningSession).where(
                        LearningSession.start_time < cutoff_date
                    )
                )
                .scalars()
                .all()
            )

            deleted_count = len(old_sessions)
            for session_obj in old_sessions:
                session.delete(session_obj)

            session.commit()
            self.logger.info(f"Cleaned up {deleted_count} old learning sessions")
            return deleted_count

    def cleanup_old_logs(self, days_old: int = 30) -> int:
        """Clean up audit logs older than specified days"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)

        with self.get_session() as session:
            # Delete old audit logs - handle invalid enum values gracefully
            try:
                old_logs = (
                    session.execute(
                        select(AuditLog).where(AuditLog.timestamp < cutoff_date)
                    )
                    .scalars()
                    .all()
                )

                deleted_count = len(old_logs)
                for log in old_logs:
                    session.delete(log)

                session.commit()
                self.logger.info(f"Cleaned up {deleted_count} old audit logs")
                return deleted_count
            except Exception as e:
                self.logger.warning(f"Error cleaning up audit logs: {e}")
                session.rollback()
                return 0

    def cleanup_unused_content(self) -> int:
        """Clean up unused content (content not assigned to any study plan)"""
        with self.get_session() as session:
            # Find content that is not referenced by any study plan
            # Content with study_plan_id = None is not assigned to any study plan
            unused_content = (
                session.execute(select(Content).where(Content.study_plan_id.is_(None)))
                .scalars()
                .all()
            )

            deleted_count = len(unused_content)
            for content in unused_content:
                session.delete(content)

            session.commit()
            self.logger.info(f"Cleaned up {deleted_count} unused content items")
            return deleted_count

    def cleanup_auth_attempts(self, days_old: int = 7) -> int:
        """Clean up old authentication attempts"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)

        with self.get_session() as session:
            # Delete old auth attempts
            old_attempts = (
                session.execute(
                    select(AuthAttempt).where(AuthAttempt.timestamp < cutoff_date)
                )
                .scalars()
                .all()
            )

            deleted_count = len(old_attempts)
            for attempt in old_attempts:
                session.delete(attempt)

            session.commit()
            self.logger.info(f"Cleaned up {deleted_count} old auth attempts")
            return deleted_count

    def add_content_to_plan(
        self, plan_id: int, content_id: int, phase_index: int, order_index: int = 0
    ) -> bool:
        """Add content to a study plan phase"""
        try:
            with self.get_session() as session:
                # Check if association already exists
                existing = session.execute(
                    select(StudyPlanContent).where(
                        StudyPlanContent.study_plan_id == plan_id,
                        StudyPlanContent.content_id == content_id,
                        StudyPlanContent.phase_index == phase_index,
                    )
                ).scalar_one_or_none()

                if existing:
                    return False  # Already exists

                # Create new association
                association = StudyPlanContent(
                    study_plan_id=plan_id,
                    content_id=content_id,
                    phase_index=phase_index,
                    order_index=order_index,
                )
                session.add(association)
                session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to add content to plan: {e}")
            return False

    def get_plan_contents(self, plan_id: int) -> dict:
        """Get all content associated with a study plan, organized by phase"""
        try:
            with self.get_session() as session:
                associations = (
                    session.execute(
                        select(StudyPlanContent).where(
                            StudyPlanContent.study_plan_id == plan_id
                        )
                    )
                    .scalars()
                    .all()
                )

                result: dict[int, list[dict[str, object]]] = {}
                for assoc in associations:
                    phase_index = (
                        assoc.phase_index if assoc.phase_index is not None else 0
                    )
                    if phase_index not in result:
                        result[phase_index] = []

                    # Get content details
                    content = session.execute(
                        select(Content).where(Content.id == assoc.content_id)
                    ).scalar_one_or_none()
                    if content:
                        result[phase_index].append(
                            {
                                "id": content.id,
                                "title": content.title,
                                "type": str(content.content_type).split(".")[-1],
                                "order": int(assoc.order_index or 0),
                            }
                        )

                # Sort by order index
                for phase in result:
                    result[phase].sort(key=lambda x: cast(int, x.get("order", 0)))

                return result
        except Exception as e:
            self.logger.error(f"Failed to get plan contents: {e}")
            return {}

    def remove_content_from_plan(
        self, plan_id: int, content_id: int, phase_index: int
    ) -> bool:
        """Remove content from a study plan phase"""
        try:
            with self.get_session() as session:
                association = session.execute(
                    select(StudyPlanContent).where(
                        StudyPlanContent.study_plan_id == plan_id,
                        StudyPlanContent.content_id == content_id,
                        StudyPlanContent.phase_index == phase_index,
                    )
                ).scalar_one_or_none()

                if association:
                    session.delete(association)
                    session.commit()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove content from plan: {e}")
            return False

    def reorder_phase_content(
        self, plan_id: int, phase_index: int, content_order: list
    ) -> bool:
        """
        Update the order of content within a phase

        Args:
            plan_id: Study plan ID
            phase_index: Phase index
            content_order: List of content IDs in desired order

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Validate plan exists
                plan = session.execute(
                    select(StudyPlan).where(StudyPlan.id == plan_id)
                ).scalar_one_or_none()
                if not plan:
                    return False

                for order_idx, content_id in enumerate(content_order):
                    stmt = select(StudyPlanContent).where(
                        StudyPlanContent.study_plan_id == plan_id,
                        StudyPlanContent.content_id == content_id,
                        StudyPlanContent.phase_index == phase_index,
                    )
                    assoc = session.execute(stmt).scalar_one_or_none()

                    if assoc:
                        assoc.order_index = order_idx

                session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to reorder content: {e}")
            return False

    def get_user_study_plans(self, user_id: int) -> list:
        """Get study plans for a user (teacher or student)"""
        try:
            with self.get_session() as session:
                user = session.execute(
                    select(User).where(User.id == user_id)
                ).scalar_one_or_none()
                if not user:
                    return []

                from ..roles import is_teacher

                is_teacher_role = is_teacher(user)

                if is_teacher_role:
                    # Teachers see plans they created
                    return list(
                        session.execute(
                            select(StudyPlan).where(StudyPlan.creator_id == user_id)
                        )
                        .scalars()
                        .all()
                    )
                else:
                    # Students see plans assigned to them
                    assignments = (
                        session.execute(
                            select(StudentStudyPlan).where(
                                StudentStudyPlan.student_id == user_id
                            )
                        )
                        .scalars()
                        .all()
                    )
                    plan_ids = [a.study_plan_id for a in assignments]
                    if not plan_ids:
                        return []
                    return list(
                        session.execute(
                            select(StudyPlan).where(StudyPlan.id.in_(plan_ids))
                        )
                        .scalars()
                        .all()
                    )
        except Exception as e:
            self.logger.error(f"Failed to get user study plans: {e}")
            return []

    def get_all_content(self, user_id: Optional[int] = None) -> list:
        """Get all content items, optionally filtered by user"""
        try:
            with self.get_session() as session:
                query = select(Content)

                if user_id is not None:
                    query = query.where(Content.creator_id == user_id)

                return list(session.execute(query).scalars().all())
        except Exception as e:
            self.logger.error(f"Failed to get all content: {e}")
            return []

    def get_user_content(self, user_id: int) -> list:
        """Get content created by a specific user (personal content)"""
        try:
            with self.get_session() as session:
                query = select(Content).where(
                    and_(Content.creator_id == user_id, Content.is_personal.is_(True))
                )
                return list(session.execute(query).scalars().all())
        except Exception as e:
            self.logger.error(f"Failed to get user content: {e}")
            return []

    def get_shared_student_content(self, teacher_id: int) -> list:
        """Get content shared with teacher by students"""
        try:
            with self.get_session() as session:
                query = select(Content).where(
                    and_(
                        Content.shared_with_teacher.is_(True),
                        Content.is_personal.is_(True),
                    )
                )
                return list(session.execute(query).scalars().all())
        except Exception as e:
            self.logger.error(f"Failed to get shared student content: {e}")
            return []

    def get_student_study_plans(self, student_id: int) -> list:
        """Get study plans assigned to a student"""
        try:
            with self.get_session() as session:
                assignments = (
                    session.execute(
                        select(StudentStudyPlan).where(
                            StudentStudyPlan.student_id == student_id
                        )
                    )
                    .scalars()
                    .all()
                )
                return [a.study_plan for a in assignments]
        except Exception as e:
            self.logger.error(f"Failed to get student study plans: {e}")
            return []

    def get_study_stats(self, user_id: int) -> dict:
        """Get study statistics for a user"""
        try:
            with self.get_session() as session:
                from datetime import date

                # Calculate total study time
                sessions = (
                    session.execute(
                        select(LearningSession).where(
                            LearningSession.student_id == user_id
                        )
                    )
                    .scalars()
                    .all()
                )
                total_seconds = sum(
                    (s.duration_minutes or (s.calculate_duration() or 0)) * 60
                    for s in sessions
                )

                # Count completed items from MasteryNode tracking
                from ..models import MasteryNode

                completed_items = (
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

                # Get streak information from user
                user = session.get(User, user_id)
                streak_days = 0
                if user and user.last_activity_date:
                    days_since_activity = (date.today() - user.last_activity_date).days
                    # Only count as active streak if activity was today or yesterday
                    if days_since_activity <= 1:
                        streak_days = user.current_streak or 0

                return {
                    "total_study_time": total_seconds,
                    "completed_items": completed_items,
                    "streak_days": streak_days,
                }
        except Exception as e:
            self.logger.error(f"Failed to get study stats: {e}")
            return {"total_study_time": 0, "completed_items": 0, "streak_days": 0}

    def delete_study_plan(self, plan_id: int) -> bool:
        """Delete a study plan"""
        try:
            with self.get_session() as session:
                plan = session.execute(
                    select(StudyPlan).where(StudyPlan.id == plan_id)
                ).scalar_one_or_none()
                if plan:
                    session.delete(plan)
                    session.commit()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete study plan: {e}")
            return False

    def update_study_plan(self, plan_id: int, data: dict) -> bool:
        """Update a study plan"""
        try:
            with self.get_session() as session:
                plan = session.execute(
                    select(StudyPlan).where(StudyPlan.id == plan_id)
                ).scalar_one_or_none()
                if plan:
                    for key, value in data.items():
                        if hasattr(plan, key):
                            setattr(plan, key, value)
                    session.commit()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to update study plan: {e}")
            return False

    def get_study_plan_summary(
        self, plan_id: int, selected_phase_index: Optional[int] = None
    ):
        """Get lightweight study plan summary for AI context

        Args:
            plan_id: The study plan ID
            selected_phase_index: Optional index of the selected topic/phase for context
        """
        try:
            from ..models import extract_phases

            with self.get_session() as session:
                plan = session.execute(
                    select(StudyPlan).where(StudyPlan.id == plan_id)
                ).scalar_one_or_none()
                if not plan:
                    return None

                # Use extract_phases to handle both flat and nested structures
                phases_list = extract_phases(plan.phases) if plan.phases else []

                # If a specific phase is selected, use that; otherwise use first phase
                if (
                    selected_phase_index is not None
                    and 0 <= selected_phase_index < len(phases_list)
                ):
                    current_phase = phases_list[selected_phase_index]
                elif phases_list:
                    current_phase = phases_list[0]
                else:
                    current_phase = None

                phase_name = "Unknown Phase"
                phase_objectives = []

                if current_phase and isinstance(current_phase, dict):
                    phase_name = current_phase.get(
                        "title", current_phase.get("name", "Untitled Phase")
                    )
                    phase_objectives = current_phase.get("objectives", [])
                    if not isinstance(phase_objectives, list):
                        phase_objectives = []

                return {
                    "id": plan.id,
                    "title": plan.title,
                    "description": plan.description[:200] if plan.description else "",
                    "total_phases": len(phases_list),
                    "selected_phase_index": selected_phase_index,
                    "current_phase": (
                        {
                            "name": phase_name,
                            "objectives": phase_objectives[:5],  # Limit to 5
                        }
                        if current_phase
                        else None
                    ),
                }
        except Exception as e:
            self.logger.error(f"Failed to get study plan summary: {e}")
            return None

    def get_content_summary(self, content_id: int):
        """Get lightweight content summary for AI context"""
        try:
            with self.get_session() as session:
                content = session.execute(
                    select(Content).where(Content.id == content_id)
                ).scalar_one_or_none()
                if not content:
                    return None

                content_type_enum = content.content_type
                return {
                    "id": content.id,
                    "title": content.title,
                    "type": (
                        content_type_enum.value if content_type_enum is not None else ""
                    ),
                    "difficulty": content.difficulty,
                    "estimated_time_min": content.estimated_time_min,
                }
        except Exception as e:
            self.logger.error(f"Failed to get content summary: {e}")
            return None


# Global database service singleton.
#
# This module is imported under multiple names in this repo/environment
# (e.g., `core.services.database` and `src.core.services.database`). If we keep
# a per-module global, we end up with multiple DatabaseService instances pointing
# at different engines/sessions, which breaks tests and request-scoped dependency
# overrides. We therefore store the singleton in `sys.modules` under a stable key
# so it is shared across all import paths.
from types import ModuleType
import sys

_SINGLETON_KEY = "slm_educator._database_service_singleton"
_singleton = cast(
    Any, sys.modules.setdefault(_SINGLETON_KEY, ModuleType(_SINGLETON_KEY))
)
if not hasattr(_singleton, "service"):
    _singleton.service = None

# Back-compat alias (kept in sync with the singleton)
_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get the global database service instance"""
    global _db_service
    if _singleton.service is None:
        _singleton.service = DatabaseService()
    _db_service = _singleton.service
    return _singleton.service


def init_db_service(db_path: Optional[str] = None) -> DatabaseService:
    """Initialize the global database service"""
    global _db_service
    _singleton.service = DatabaseService(db_path)
    _db_service = _singleton.service

    # Seed default badges if not present
    seed_default_badges(_singleton.service)

    return _singleton.service


def seed_default_badges(db_service: DatabaseService) -> None:
    """Seed default badges for gamification if they don't exist."""
    from ..models import Badge

    default_badges: list[dict[str, Any]] = [
        {
            "name": "First Steps",
            "description": "Complete your first learning session",
            "criteria_type": "xp_threshold",
            "criteria_value": {"threshold": 50},
            "xp_value": 25,
            "is_active": True,
        },
        {
            "name": "Quick Learner",
            "description": "Earn 500 XP",
            "criteria_type": "xp_threshold",
            "criteria_value": {"threshold": 500},
            "xp_value": 100,
            "is_active": True,
        },
        {
            "name": "Knowledge Seeker",
            "description": "Earn 1000 XP",
            "criteria_type": "xp_threshold",
            "criteria_value": {"threshold": 1000},
            "xp_value": 200,
            "is_active": True,
        },
        {
            "name": "Streak Master",
            "description": "Maintain a 7-day study streak",
            "criteria_type": "streak",
            "criteria_value": {"days": 7},
            "xp_value": 150,
            "is_active": True,
        },
        {
            "name": "Level Up",
            "description": "Reach Level 2",
            "criteria_type": "level",
            "criteria_value": {"level": 2},
            "xp_value": 50,
            "is_active": True,
        },
    ]

    try:
        with db_service.get_session() as session:
            for badge_data in default_badges:
                existing = session.execute(
                    select(Badge).where(Badge.name == badge_data["name"])
                ).scalar_one_or_none()

                if not existing:
                    badge = Badge(**badge_data)
                    session.add(badge)

            session.commit()
    except Exception:
        pass  # Non-critical, badges can be added later
