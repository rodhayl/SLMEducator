"""
Role normalization helpers (backend).

Canonical contract:
- Internal (DB/runtime): roles are represented by ``UserRole`` when possible.
- API/UI boundaries: roles are serialized as lowercase strings: "student" | "teacher" | "admin".

Legacy tolerance:
- Accept role objects with ``.value`` or dicts like ``{"value": "teacher"}`` when reading.
- Always emit the canonical lowercase string when writing.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from .models import UserRole

RoleLike = Union[str, UserRole, Any]


def normalize_role(role: RoleLike) -> str:
    """Return canonical lowercase role string, or "" if missing/unknown."""
    if role is None:
        return ""

    if isinstance(role, UserRole):
        return role.value

    # Legacy shapes: {"value": "teacher"} or objects with .value
    if isinstance(role, dict):
        role = role.get("value")
    elif hasattr(role, "value"):
        role = getattr(role, "value", role)

    try:
        raw = str(role).strip()
    except Exception:
        return ""

    if not raw:
        return ""

    lowered = raw.lower()
    if lowered in {
        UserRole.STUDENT.value,
        UserRole.TEACHER.value,
        UserRole.ADMIN.value,
    }:
        return lowered

    # Tolerate enum-ish string representations like "UserRole.ADMIN"
    if "." in raw:
        tail = raw.split(".")[-1].strip()
        tail_lower = tail.lower()
        if tail_lower in {
            UserRole.STUDENT.value,
            UserRole.TEACHER.value,
            UserRole.ADMIN.value,
        }:
            return tail_lower

    return lowered


def parse_user_role(role: RoleLike) -> Optional[UserRole]:
    """Best-effort conversion to ``UserRole``; returns None if invalid/unknown."""
    role_value = normalize_role(role)
    if not role_value:
        return None
    try:
        return UserRole(role_value)
    except Exception:
        return None


def role_str(user_or_role: Any) -> str:
    """Accept a user-like object (with ``.role``) or a role value."""
    if hasattr(user_or_role, "role"):
        return normalize_role(getattr(user_or_role, "role", None))
    return normalize_role(user_or_role)


def has_role(user_or_role: Any, *roles: Union[UserRole, str]) -> bool:
    """Return True if the user/role matches any of the given roles."""
    current = role_str(user_or_role)
    if not current:
        return False
    allowed = {normalize_role(r) for r in roles}
    return current in allowed


def is_teacher_or_admin(user_or_role: Any) -> bool:
    return has_role(user_or_role, UserRole.TEACHER, UserRole.ADMIN)


def is_admin(user_or_role: Any) -> bool:
    return has_role(user_or_role, UserRole.ADMIN)


def is_teacher(user_or_role: Any) -> bool:
    return has_role(user_or_role, UserRole.TEACHER)


def is_student(user_or_role: Any) -> bool:
    return has_role(user_or_role, UserRole.STUDENT)
