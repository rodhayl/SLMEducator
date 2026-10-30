"""
Core services for SLMEducator
"""

from .database import DatabaseService, get_db_service, init_db_service
from .auth import AuthService, get_auth_service, AuthenticationError
from .logging import LoggingService, get_logging_service, get_logger
from .ai_service import AIService, get_ai_service, init_ai_service
from .translation_service import TranslationService, get_translation_service, tr

# Active Services
from .study_plan_service import get_study_plan_service
from .content_service import get_content_service
from .learning_session_service import get_learning_session_service
from .progress_tracking_service import get_progress_tracking_service
from .exercise_generator_service import get_exercise_generator_service
from .spaced_repetition_service import get_spaced_repetition_service

__all__ = [
    "DatabaseService",
    "get_db_service",
    "init_db_service",
    "AuthService",
    "get_auth_service",
    "AuthenticationError",
    "LoggingService",
    "get_logging_service",
    "get_logger",
    "AIService",
    "get_ai_service",
    "init_ai_service",
    "TranslationService",
    "get_translation_service",
    "tr",
    # Active Services
    "get_study_plan_service",
    "get_content_service",
    "get_learning_session_service",
    "get_progress_tracking_service",
    "get_exercise_generator_service",
    "get_spaced_repetition_service",
]
