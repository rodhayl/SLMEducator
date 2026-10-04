"""Create-only admin bootstrap contracts using disposable, real SQLite databases."""

from datetime import date, datetime
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def bootstrap_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Use only the seeder's ORM namespace, with no app or provider fixtures."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SLM_DB_PATH", str(tmp_path / "bootstrap.sqlite3"))
    monkeypatch.setenv("JWT_SECRET", "synthetic-bootstrap-tests-only-not-a-real-secret")
    monkeypatch.delenv("SLM_INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("SLM_INITIAL_ADMIN_EMAIL", raising=False)

    from scripts import seed_admin

    database = seed_admin.DatabaseService()
    monkeypatch.setattr(seed_admin, "DatabaseService", lambda: database)
    try:
        yield seed_admin, database
    finally:
        database.close()


def _snapshot(database: Any) -> dict[str, list[tuple[Any, ...]]]:
    """Read every persisted column without mixing core/src.core ORM classes."""
    with sqlite3.connect(database.db_path) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            for table in ("users", "auth_attempts")
        }


@pytest.mark.parametrize("role_name", ["ADMIN", "TEACHER", "STUDENT"])
@pytest.mark.parametrize(
    "configured_password",
    [None, "", "   ", "short", "SyntheticBootstrap123!", "ChangedBootstrap456!"],
)
def test_existing_admin_preserves_all_account_and_attempt_state(
    bootstrap_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    role_name: str,
    configured_password: str | None,
) -> None:
    """Repeated startup must not recover, promote, unlock or overwrite an account."""
    from src.core.models import AuthAttempt, User, UserRole

    seed_admin, database = bootstrap_db
    with database.get_session() as session:
        teacher = User(
            username="synthetic-teacher",
            email="teacher@example.invalid",
            password_hash="synthetic-teacher-hash",
            role=UserRole.TEACHER,
            first_name="Synthetic",
            last_name="Teacher",
        )
        session.add(teacher)
        session.flush()
        user = User(
            username="admin",
            email="rotated@example.invalid",
            password_hash="synthetic-previously-rotated-hash",
            role=UserRole[role_name],
            active=False,
            first_name="Existing",
            last_name="Account",
            grade_level="synthetic-grade",
            failed_login_count=7,
            locked_until=datetime(2099, 1, 1),
            created_at=datetime(2020, 1, 1),
            last_login=datetime(2026, 1, 1),
            xp=17,
            level=3,
            current_streak=2,
            longest_streak=5,
            last_activity_date=date(2026, 1, 1),
            teacher_id=teacher.id,
            settings={"language": "es", "synthetic_note": "preserve this setting"},
        )
        session.add(user)
        session.flush()
        session.add_all(
            [
                AuthAttempt(user_id=user.id, username="previous-name", success=False),
                AuthAttempt(username="admin", success=False),
                AuthAttempt(username="unrelated", success=True),
            ]
        )
        session.commit()
    before = _snapshot(database)

    if configured_password is not None:
        monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", configured_password)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "replacement@example.invalid")
    forbidden = Mock(side_effect=AssertionError("Existing accounts are read-only"))
    for attribute in ("_resolve_admin_password", "_generate_password", "hash_password"):
        monkeypatch.setattr(seed_admin, attribute, forbidden)
    monkeypatch.setattr(Session, "commit", forbidden)

    for _ in range(2):
        assert seed_admin.seed_admin_user() == 0
        assert _snapshot(database) == before
    forbidden.assert_not_called()
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert output.count("Admin user already exists, skipping admin creation.") == 2
    assert "Password:" not in output
    assert "replacement@example.invalid" not in output


def test_fresh_explicit_password_creates_one_admin_without_printing_secret(
    bootstrap_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The existing 12-character bootstrap boundary still works for a new account."""
    from src.core.models import User, UserRole
    from src.core.security import verify_password

    seed_admin, database = bootstrap_db
    password = "Synthetic12!"
    assert len(password) == 12
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", f"  {password}  ")
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "  bootstrap@example.invalid  ")
    generator = Mock(side_effect=AssertionError("An explicit password was supplied"))
    monkeypatch.setattr(seed_admin, "_generate_password", generator)

    assert seed_admin.seed_admin_user() == 0
    with database.get_session() as session:
        user = session.query(User).one()
        assert user.username == "admin"
        assert user.email == "bootstrap@example.invalid"
        assert user.role is UserRole.ADMIN
        assert user.active is True
        assert verify_password(password, user.password_hash)
    before = _snapshot(database)
    assert seed_admin.seed_admin_user() == 0
    assert _snapshot(database) == before
    generator.assert_not_called()
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert password not in output
    assert output.count("Initial admin user created successfully!") == 1


@pytest.mark.parametrize("password", ["x", "x" * 11, "  short  "])
def test_fresh_invalid_password_leaves_no_partial_account(
    bootstrap_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    password: str,
) -> None:
    """Validation failures are nonzero and leave the synthetic database unchanged."""
    seed_admin, database = bootstrap_db
    before = _snapshot(database)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", password)
    assert seed_admin.seed_admin_user() == 1
    assert _snapshot(database) == before
    output = capsys.readouterr().out
    assert "at least 12 characters" in output
    assert "Generated Password:" not in output
    assert "Initial admin user created successfully!" not in output


@pytest.mark.parametrize("password", [None, "", "   "])
def test_fresh_missing_password_is_generated_and_printed_only_once(
    bootstrap_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    password: str | None,
) -> None:
    """Random credentials are emitted only on creation, never on subsequent runs."""
    from src.core.models import User
    from src.core.security import verify_password

    seed_admin, database = bootstrap_db
    if password is not None:
        monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", password)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "   ")
    generator = Mock(wraps=seed_admin._generate_password)
    monkeypatch.setattr(seed_admin, "_generate_password", generator)

    assert seed_admin.seed_admin_user() == 0
    captured = capsys.readouterr()
    assert captured.out.count("Generated Password:") == 1
    generated = re.search(r"Generated Password: (\S+)", captured.out)
    assert generated is not None
    generated_password = generated.group(1)
    assert len(generated_password) == 20
    assert generated_password not in captured.err
    with database.get_session() as session:
        user = session.query(User).one()
        assert user.email == "admin@example.invalid"
        assert verify_password(generated_password, user.password_hash)
    before = _snapshot(database)

    assert seed_admin.seed_admin_user() == 0
    assert _snapshot(database) == before
    captured = capsys.readouterr()
    assert "Password:" not in captured.out + captured.err
    generator.assert_called_once_with()


def test_fresh_commit_failure_does_not_print_generated_password(
    bootstrap_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unsuccessful creation must not announce a usable generated credential."""
    seed_admin, database = bootstrap_db
    generated_password = "SyntheticGenerated123!"
    monkeypatch.setattr(seed_admin, "_generate_password", lambda: generated_password)
    monkeypatch.setattr(
        Session, "commit", Mock(side_effect=RuntimeError("synthetic failure"))
    )
    assert seed_admin.seed_admin_user() == 1
    assert _snapshot(database) == {"users": [], "auth_attempts": []}
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert generated_password not in output
    assert "Initial admin user created successfully!" not in output


def test_launcher_does_not_assign_a_shared_bootstrap_password() -> None:
    """The launcher delegates first-run credential selection to the seeder."""
    launcher = (Path(__file__).parents[1] / "start.bat").read_text(encoding="utf-8")
    assert not re.search(r"(?im)^\s*set\s+\"?SLM_INITIAL_ADMIN_PASSWORD\s*=", launcher)
    assert "python scripts\\seed_admin.py" in launcher
