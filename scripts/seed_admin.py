#!/usr/bin/env python3
"""
Seed initial admin user for fresh database installation.

Security behavior:
- Existing admin accounts are always left unchanged, including their security state.
- For a new account, SLM_INITIAL_ADMIN_PASSWORD is used when set (min length: 12).
- Otherwise, a cryptographically random password is generated and printed once.
"""

import os
import secrets
import string
import sys
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Literal
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Add parent directory to path (where src/ is located)
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.core.models import AuditLog, EventType, User, UserRole
from src.core.security import hash_password
from src.core.services.database import DatabaseService

SetupState = Literal["needed", "configured", "recovery"]
SETUP_MARKER = "local_first_admin_setup_v1"


def _setup_marker(session: Session) -> AuditLog | None:
    """Find local bootstrap provenance without introducing a schema migration."""
    return session.query(AuditLog).filter(
        AuditLog.user_id.is_(None),
        AuditLog.details["bootstrap"].as_string() == SETUP_MARKER,
    ).order_by(AuditLog.id.desc()).first()


def _setup_state(session: Session) -> SetupState:
    """An established or unrecognized database never reopens account setup."""
    if session.query(User.id).filter(User.role == UserRole.ADMIN).first():
        return "configured"
    if session.query(User.id).first():
        return "recovery"
    marker = _setup_marker(session)
    return "needed" if marker and (marker.details or {}).get("state") == "pending" else "recovery"


def _read_setup_state(path: Path) -> SetupState:
    """Inspect existing installation provenance without initializing or writing it."""
    uri = path.absolute().as_uri() + "?mode=ro"
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True))
    try:
        with Session(engine) as session:
            return _setup_state(session)
    except (sqlite3.Error, SQLAlchemyError):
        return "recovery"
    finally:
        engine.dispose()


def _prepare_candidate(path: Path) -> None:
    """Build a complete account-free DB only inside an owned private directory."""
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    database = DatabaseService(db_path=str(path))
    try:
        with database.get_session() as session:
            session.add(AuditLog(event_type=EventType.CREATE, details={
                "bootstrap": SETUP_MARKER, "state": "pending",
            }))
            session.commit()
    finally:
        database.close()
    # Publish a standalone database, never a file dependent on private WAL data.
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
            raise RuntimeError("First-run database could not be made standalone")


def prepare_first_run() -> SetupState:
    """Atomically publish a prepared local DB without replacing existing data.

    A sibling temporary directory keeps preparation on the destination volume.
    Hard-link creation is atomic and no-clobber on supported Windows/Unix file
    systems. Unsupported file systems fail before publishing any destination.
    A racing loser discards only its own temporary files and reads the winner.
    """
    path = Path(os.getenv("SLM_DB_PATH", "slm_educator.db")).absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with tempfile.TemporaryDirectory(prefix=".slm-first-run-", dir=path.parent) as temporary:
            candidate = Path(temporary) / "prepared.sqlite3"
            _prepare_candidate(candidate)
            try:
                os.link(candidate, path)
            except FileExistsError:
                pass
    return _read_setup_state(path)


def create_first_admin(username: str, password: str, repeat: str) -> None:
    """Create the installation owner's first admin atomically, from local UI only."""
    from src.core.services.auth import AuthService

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
        raise ValueError("username")
    if len(password) < 12 or not AuthService.validate_password(password):
        raise ValueError("password")
    if password != repeat:
        raise ValueError("repeat")
    path = Path(os.getenv("SLM_DB_PATH", "slm_educator.db"))
    if _read_setup_state(path) != "needed":
        raise ValueError("closed")
    uri = path.absolute().as_uri() + "?mode=rw"
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True, timeout=30))
    try:
        with Session(engine) as session:
            # SQLite reserves the writer before testing eligibility. A second
            # launcher waits, then sees the committed account/completed marker.
            session.execute(text("BEGIN IMMEDIATE"))
            if _setup_state(session) != "needed":
                raise ValueError("closed")
            marker = _setup_marker(session)
            assert marker is not None
            session.add(User(
                username=username, email=f"{username}@example.invalid",
                password_hash=hash_password(password), first_name="Administrator",
                last_name="", role=UserRole.ADMIN, active=True,
            ))
            marker.details = {"bootstrap": SETUP_MARKER, "state": "complete"}
            session.commit()
    finally:
        engine.dispose()


def _generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _resolve_admin_password() -> tuple[str, bool]:
    configured = os.getenv("SLM_INITIAL_ADMIN_PASSWORD", "").strip()
    if configured:
        if len(configured) < 12:
            raise ValueError(
                "SLM_INITIAL_ADMIN_PASSWORD must be at least 12 characters."
            )
        return configured, True
    return _generate_password(), False


def seed_admin_user() -> int:
    """Create a missing admin account without changing an existing account."""
    print("Seeding database with initial admin user...")

    db_service = DatabaseService()
    session = db_service.get_session()

    try:
        from src.core.models import User

        admin_user = session.query(User).filter(User.username == "admin").first()
        if admin_user is not None:
            print("Admin user already exists, skipping admin creation.")
            return 0

        initial_password, password_from_env = _resolve_admin_password()
        initial_email = (
            os.getenv("SLM_INITIAL_ADMIN_EMAIL", "admin@example.invalid").strip()
            or "admin@example.invalid"
        )

        admin_user = User(
            username="admin",
            email=initial_email,
            password_hash=hash_password(initial_password),
            first_name="Administrator",
            last_name="User",
            role=UserRole.ADMIN,
            active=True,
        )

        session.add(admin_user)
        session.commit()

        print("[OK] Initial admin user created successfully!")
        print("  Username: admin")
        if password_from_env:
            print("  Password: (from SLM_INITIAL_ADMIN_PASSWORD)")
        else:
            print(f"  Generated Password: {initial_password}")
        print(f"  Email: {initial_email}")
        print("  Role: Admin")
        print("  Action Required: Sign in and rotate credentials immediately.")
        return 0

    except Exception as e:
        print(f"[FAIL] Error creating admin user: {e}")
        import traceback

        traceback.print_exc()
        session.rollback()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    if "--prepare-only" in sys.argv:
        raise SystemExit(0 if prepare_first_run() == "needed" else 1)
    if "--interactive" in sys.argv or "--console" in sys.argv:
        from src.first_run_setup import ensure_initial_admin
        raise SystemExit(0 if ensure_initial_admin(gui="--console" not in sys.argv) else 1)
    raise SystemExit(seed_admin_user())
