"""
Models package for SLMEducator

This package contains all database models and enums for the application.
"""

from .models import (
    Base,
    User,
    StudyPlan,
    StudyPlanContent,
    Content,
    Book,
    StudentStudyPlan,
    LearningSession,
    AIModelConfiguration,
    TeacherMessage,
    AuditLog,
    AuthAttempt,
    UserRole,
    ContentType,
    SessionStatus,
    EventType,
    QuestionType,
    SubmissionStatus,
    GradingMode,
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    QuestionResponse,
    Rubric,
    RubricCriterion,
    LoggingConfiguration,
    ApplicationConfiguration,
    MasteryNode,
    Annotation,
    HelpRequest,
    Badge,
    UserBadge,
    DailyGoal,
    LeaderboardEntry,
    GamificationSettings,
    encrypt_data,
    decrypt_data,
)

# For backward compatibility with existing code
AIModelConfig = AIModelConfiguration
Question = AssessmentQuestion
Submission = AssessmentSubmission


def extract_phases(phases_data):
    """
    Extract phases from study plan data, handling both flat and nested structures.

    The phases can be stored in two formats:
    1. Flat: [{"title": "Phase 1", ...}, {"title": "Phase 2", ...}]
    2. Nested: [{"title": "Plan Title", "phases": [{"title": "Phase 1", ...}, ...]}]

    This function normalizes both formats to return the actual phases list.

    Args:
        phases_data: The phases field from a StudyPlan object

    Returns:
        List of phase dictionaries, or empty list if invalid
    """
    if not phases_data or not isinstance(phases_data, list):
        return []

    # Check if it's the nested format (list with one wrapper object containing 'phases')
    if (
        len(phases_data) > 0
        and isinstance(phases_data[0], dict)
        and "phases" in phases_data[0]
        and isinstance(phases_data[0]["phases"], list)
    ):
        # Nested format - extract the inner phases
        return phases_data[0]["phases"]

    # Flat format or list of phase dicts - return as is
    return phases_data


__all__ = [
    "Base",
    "User",
    "StudyPlan",
    "StudyPlanContent",
    "Content",
    "Book",
    "StudentStudyPlan",
    "LearningSession",
    "AIModelConfiguration",
    "AIModelConfig",  # Alias for backward compatibility
    "TeacherMessage",
    "AuditLog",
    "AuthAttempt",
    "UserRole",
    "ContentType",
    "SessionStatus",
    "EventType",
    "QuestionType",
    "SubmissionStatus",
    "GradingMode",
    "Assessment",
    "AssessmentQuestion",
    "AssessmentSubmission",
    "QuestionResponse",
    "Rubric",
    "RubricCriterion",
    "LoggingConfiguration",
    "ApplicationConfiguration",
    "MasteryNode",
    "Annotation",
    "HelpRequest",
    "Badge",
    "UserBadge",
    "DailyGoal",
    "LeaderboardEntry",
    "GamificationSettings",
    "encrypt_data",
    "decrypt_data",
    "extract_phases",
]
