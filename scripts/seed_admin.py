#!/usr/bin/env python3
"""
Seed initial admin user for fresh database installation.

Security behavior:
- If SLM_INITIAL_ADMIN_PASSWORD is set, that value is used (min length: 12).
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
    """Ensure admin user exists with deterministic credentials when requested."""
    print("Seeding database with initial admin user...")

    db_service = DatabaseService()
    session = db_service.get_session()

    try:
        from sqlalchemy import or_
        from src.core.models import User, AuthAttempt

        initial_password, password_from_env = _resolve_admin_password()
        initial_email = (
            os.getenv("SLM_INITIAL_ADMIN_EMAIL", "admin@example.invalid").strip()
            or "admin@example.invalid"
        )

        admin_user = session.query(User).filter(User.username == "admin").first()

        if admin_user:
            if password_from_env:
                admin_user.password_hash = hash_password(initial_password)
                admin_user.email = initial_email
                admin_user.active = True
                admin_user.role = UserRole.ADMIN
                admin_user.failed_login_count = 0
                admin_user.locked_until = None
                session.query(AuthAttempt).filter(
                    or_(
                        AuthAttempt.user_id == admin_user.id,
                        AuthAttempt.username == "admin",
                    )
                ).delete(synchronize_session=False)
                session.commit()
                print("[OK] Admin credentials updated from environment.")
                print("  Username: admin")
                print("  Password: (from SLM_INITIAL_ADMIN_PASSWORD)")
                print(f"  Email: {initial_email}")
                return 0
            print("Admin user already exists, skipping admin creation.")
            return 0

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
