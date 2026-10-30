"""
FastAPI authentication + authorization helpers.

This centralizes:
- Token -> current user dependency
- Role normalization at the API boundary
- Standard role-based route guards (dependencies)
"""

from __future__ import annotations

from typing import Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.core.models import User, UserRole
from src.core.roles import has_role, parse_user_role, role_str
from src.core.services.auth import AuthService, get_auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)


def _ensure_user_role_enum(user: User) -> None:
    """
    Best-effort coercion to keep backend runtime representation consistent.

    ``User.role`` should be ``UserRole`` (SQLAlchemy Enum). We tolerate legacy
    shapes (string / {"value": "..."} / objects with .value) and coerce them.
    """
    try:
        role_enum = parse_user_role(getattr(user, "role", None))
        if role_enum is not None and getattr(user, "role", None) != role_enum:
            # Safe even for detached instances; ensures downstream code can
            # reliably do enum comparisons.
            user.role = role_enum
    except Exception:
        # Never fail auth due to normalization errors.
        return


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    user = auth_service.validate_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _ensure_user_role_enum(user)
    return user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """Return user if token is valid, otherwise None (no 401)."""
    if not token:
        return None
    try:
        user = auth_service.validate_token(token)
        if not user:
            return None
        _ensure_user_role_enum(user)
        return user
    except Exception:
        return None


RoleInput = Union[UserRole, str]


def require_roles(*roles: RoleInput):
    """
    Dependency factory that enforces role membership and returns ``current_user``.

    Usage:
        current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
    """

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not has_role(current_user, *roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )
        return current_user

    return _dep


def require_teacher_or_admin(
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
) -> User:
    return current_user


def require_admin(current_user: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    return current_user


def user_role_str(user: User) -> str:
    """Canonical role string for API responses."""
    return role_str(user)
