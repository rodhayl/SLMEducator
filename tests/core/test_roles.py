from core.models import UserRole
from core.roles import normalize_role, parse_user_role


def test_normalize_role_accepts_enum_value_object():
    assert normalize_role(UserRole.ADMIN) == "admin"
    assert parse_user_role(UserRole.ADMIN) == UserRole.ADMIN


def test_normalize_role_accepts_string_variants():
    assert normalize_role("admin") == "admin"
    assert normalize_role(" ADMIN ") == "admin"
    assert parse_user_role("admin") == UserRole.ADMIN


def test_normalize_role_accepts_enumish_strings():
    assert normalize_role("UserRole.ADMIN") == "admin"
    assert parse_user_role("UserRole.ADMIN") == UserRole.ADMIN
    assert normalize_role("UserRole.TEACHER") == "teacher"
    assert parse_user_role("UserRole.TEACHER") == UserRole.TEACHER
