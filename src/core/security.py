"""
Security utilities for password hashing and verification.

This module re-exports the canonical implementations that live in
AuthService so that existing callers (tests, scripts) keep working
without duplicating the bcrypt logic.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash password using bcrypt (canonical implementation)."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash (canonical implementation)."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False
