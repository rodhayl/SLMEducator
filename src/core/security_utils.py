"""
Security utilities for SLMEducator

This module provides centralized security functions for:
- Encryption key management
- JWT secret management
- Input sanitization
- SQL injection prevention
"""

import os
import re
import logging
from pathlib import Path
from cryptography.fernet import Fernet
import secrets

logger = logging.getLogger(__name__)


# Security configuration
SECURITY_DIR = Path.home() / ".slm_educator"
ENCRYPTION_KEY_FILE = SECURITY_DIR / "encryption.key"
JWT_SECRET_FILE = SECURITY_DIR / "jwt.secret"

# Input sanitization limits
MAX_INPUT_LENGTH = 10000  # Maximum characters for user input
MAX_PROMPT_LENGTH = 50000  # Maximum characters for AI prompts


def get_or_create_encryption_key() -> bytes:
    """
    Get or create persistent encryption key.

    The key is stored in ~/.slm_educator/encryption.key with restricted permissions.
    If the key doesn't exist, a new one is generated and saved.

    Returns:
        bytes: The encryption key

    Raises:
        PermissionError: If unable to create security directory or key file
    """
    # Check environment variable first
    env_key = os.getenv("SLM_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # Ensure security directory exists
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)

    # Check if key file exists
    if ENCRYPTION_KEY_FILE.exists():
        with open(ENCRYPTION_KEY_FILE, "rb") as f:
            return f.read()

    # Generate new key
    key = Fernet.generate_key()

    # Save key with restricted permissions (owner read/write only)
    with open(ENCRYPTION_KEY_FILE, "wb") as f:
        f.write(key)

    # Set file permissions to 0o600 (owner read/write only)
    try:
        os.chmod(ENCRYPTION_KEY_FILE, 0o600)
    except (OSError, AttributeError) as e:
        # Windows doesn't support chmod in the same way
        # File permissions are handled differently on Windows
        logger.debug(
            f"Cannot set file permissions on {ENCRYPTION_KEY_FILE}: {e} (expected on Windows)"
        )

    return key


def get_or_create_jwt_secret() -> str:
    """
    Get or create persistent JWT secret.

    The secret is stored in ~/.slm_educator/jwt.secret with restricted permissions.
    If the secret doesn't exist, a new one is generated and saved.

    Returns:
        str: The JWT secret

    Raises:
        PermissionError: If unable to create security directory or secret file
    """
    # Check environment variable first
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret

    # Ensure security directory exists
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)

    # Check if secret file exists
    if JWT_SECRET_FILE.exists():
        with open(JWT_SECRET_FILE, "r") as f:
            return f.read().strip()

    # Generate new secret
    secret = secrets.token_urlsafe(32)

    # Save secret with restricted permissions
    with open(JWT_SECRET_FILE, "w") as f:
        f.write(secret)

    # Set file permissions to 0o600 (owner read/write only)
    try:
        os.chmod(JWT_SECRET_FILE, 0o600)
    except (OSError, AttributeError) as e:
        # Windows doesn't support chmod in the same way
        # File permissions are handled differently on Windows
        logger.debug(
            f"Cannot set file permissions on {JWT_SECRET_FILE}: {e} (expected on Windows)"
        )

    return secret


def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize user input for AI prompts.

    This function:
    - Removes control characters (except newlines and tabs)
    - Truncates to maximum length
    - Preserves printable characters and whitespace

    Args:
        text: The input text to sanitize
        max_length: Maximum allowed length (default: 10000)

    Returns:
        str: Sanitized text
    """
    if not text:
        return ""

    # Remove control characters except newline and tab
    sanitized = "".join(
        char for char in text if char.isprintable() or char in ("\n", "\t", "\r")
    )

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def sanitize_prompt(prompt: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
    """
    Sanitize AI prompt text.

    Similar to sanitize_input but with higher length limit for prompts
    that may include context.

    Args:
        prompt: The prompt text to sanitize
        max_length: Maximum allowed length (default: 50000)

    Returns:
        str: Sanitized prompt
    """
    return sanitize_input(prompt, max_length)


def validate_table_name(table_name: str) -> bool:
    """
    Validate table name to prevent SQL injection.

    Only allows alphanumeric characters and underscores.
    Prevents SQL keywords and special characters.

    Args:
        table_name: The table name to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not table_name:
        return False

    # Only allow alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        return False

    # Prevent SQL keywords (basic list)
    sql_keywords = {
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "truncate",
        "union",
        "join",
        "where",
        "from",
    }

    if table_name.lower() in sql_keywords:
        return False

    return True


def scrub_sensitive_data(message: str) -> str:
    """
    Remove sensitive data from log messages.

    This function redacts:
    - API keys
    - Passwords
    - Bearer tokens
    - JWT tokens

    Args:
        message: The log message to scrub

    Returns:
        str: Scrubbed message with sensitive data replaced
    """
    patterns = [
        # API keys
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-_]+)', "api_key=***"),
        # Passwords
        (r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)', "password=***"),
        # Bearer tokens
        (r"Bearer\s+([A-Za-z0-9\-_\.]+)", "Bearer ***"),
        # JWT tokens
        (r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", "jwt_token=***"),
    ]

    scrubbed = message
    for pattern, replacement in patterns:
        scrubbed = re.sub(pattern, replacement, scrubbed, flags=re.IGNORECASE)

    return scrubbed
