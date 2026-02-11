"""
Custom exceptions for SLMEducator

This module contains all custom exceptions used throughout the application.
"""


class SLMEducatorException(Exception):
    """Base exception for all SLMEducator exceptions"""


class ConfigurationError(SLMEducatorException):
    """Raised when there's a configuration error"""


class ValidationError(SLMEducatorException):
    """Raised when validation fails"""


class AuthenticationError(SLMEducatorException):
    """Raised when authentication fails"""


class AuthorizationError(SLMEducatorException):
    """Raised when authorization fails"""


class DatabaseError(SLMEducatorException):
    """Raised when there's a database error"""


class AIServiceError(SLMEducatorException):
    """Raised when AI service fails"""


class ContentNotFoundError(SLMEducatorException):
    """Raised when content is not found"""


class UserNotFoundError(SLMEducatorException):
    """Raised when user is not found"""


class RateLimitError(SLMEducatorException):
    """Raised when rate limit is exceeded"""


class AccountLockedError(SLMEducatorException):
    """Raised when account is locked"""


class SessionExpiredError(SLMEducatorException):
    """Raised when session has expired"""


class EncryptionError(SLMEducatorException):
    """Raised when encryption/decryption fails"""
