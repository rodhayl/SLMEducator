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
from pathlib import Path

# Add parent directory to path (where src/ is located)
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.core.models import UserRole
from src.core.security import hash_password
from src.core.services.database import DatabaseService


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
    raise SystemExit(seed_admin_user())
