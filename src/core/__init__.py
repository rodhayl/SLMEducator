"""
Core module for SLMEducator
"""

from .models import (
    Base,
    User,
    UserRole,
    StudyPlan,
    Content,
    ContentType,
    Book,
    StudentStudyPlan,
    LearningSession,
    SessionStatus,
    AIModelConfiguration,
    TeacherMessage,
    AuditLog,
)
from .services import (
    DatabaseService,
    get_db_service,
    init_db_service,
    AuthService,
    get_auth_service,
    AuthenticationError,
    LoggingService,
    get_logging_service,
    get_logger,
)

__all__ = [
    # Models
    "Base",
    "User",
    "UserRole",
    "StudyPlan",
    "Content",
    "ContentType",
    "Book",
    "StudentStudyPlan",
    "LearningSession",
    "SessionStatus",
    "AIModelConfiguration",
    "TeacherMessage",
    "AuditLog",
    # Services
    "DatabaseService",
    "get_db_service",
    "init_db_service",
    "AuthService",
    "get_auth_service",
    "AuthenticationError",
    "LoggingService",
    "get_logging_service",
    "get_logger",
]
