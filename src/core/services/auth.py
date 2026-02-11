"""
Authentication service for SLMEducator
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from sqlalchemy.orm import Session

from ..models import User, UserRole, AuditLog, AuthAttempt, EventType
from .database import get_db_service


class AuthenticationError(Exception):
    """Authentication related errors"""


class AuthService:
    """Authentication and authorization service"""

    def __init__(self):
        # Use persistent JWT secret from security_utils
        from ..security_utils import get_or_create_jwt_secret

        self.jwt_secret = get_or_create_jwt_secret()
        self.jwt_algorithm = "HS256"
        self.token_expiry_minutes = 30
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15
        self.rate_limit_window_minutes = 1
        self.rate_limit_max_attempts = 5

    @property
    def db_service(self):
        # Avoid caching DatabaseService across tests/app reloads. The database
        # module is imported under multiple names in this repo, and tests may
        # re-initialize/replace the global database service between runs.
        return get_db_service()

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole,
        teacher_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Register a new user"""
        # Validate password strength
        if not self.validate_password(password):
            raise AuthenticationError(
                "Password must be at least 8 characters and contain uppercase, "
                "lowercase, digit, and special character"
            )

        with self.db_service.get_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                raise AuthenticationError("Username already exists")

            # Check if email already exists
            existing_email = session.query(User).filter_by(email=email).first()
            if existing_email:
                raise AuthenticationError("Email already exists")

            # Hash password
            password_hash = self._hash_password(password)

            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                first_name=first_name,
                last_name=last_name,
                teacher_id=teacher_id,
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Log registration
            self._log_event(
                session,
                user.id,
                "auth.register",
                {"username": username, "role": role.value},
            )

            # Return user data as dict to avoid detached instance issues
            role_value = user.role.value if user.role else None
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": role_value,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "teacher_id": user.teacher_id,
                "active": user.active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }

    def login_user(
        self, username: str, password: str, ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate user and return JWT token."""
        with self.db_service.get_session() as session:
            # Find user
            user = session.query(User).filter_by(username=username, active=True).first()
            if not user:
                # Best-effort rate limiting even for unknown usernames to reduce
                # brute-force / user enumeration blast radius.
                if not self._check_rate_limit(
                    session, user_id=None, username=username, ip_address=ip_address
                ):
                    raise AuthenticationError(
                        "Too many login attempts. Please try again later."
                    )

                session.add(
                    AuthAttempt.record_attempt(
                        username=username,
                        success=False,
                        user_id=None,
                        ip_address=ip_address,
                    )
                )
                session.commit()
                raise AuthenticationError("Invalid username or password")

            # Check rate limiting early (before expensive bcrypt work).
            if not self._check_rate_limit(
                session, user_id=user.id, username=username, ip_address=ip_address
            ):
                session.add(
                    AuthAttempt.record_attempt(
                        username=username,
                        success=False,
                        user_id=user.id,
                        ip_address=ip_address,
                    )
                )
                session.commit()
                raise AuthenticationError(
                    "Too many login attempts. Please try again later."
                )

            # Check if account is locked
            if self._is_account_locked(session, user.id):
                raise AuthenticationError(
                    "Account is locked due to too many failed attempts"
                )

            # Verify password
            if not self._verify_password(password, user.password_hash):
                self._record_failed_attempt(session, user.id, username, ip_address)
                session.commit()
                raise AuthenticationError("Invalid username or password")

            # Generate JWT token
            token = self._generate_jwt_token(user)

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            session.commit()
            session.refresh(user)

            # Clear failed attempts
            self._clear_failed_attempts(session, user.id)

            # Log successful login
            self._log_event(
                session,
                user.id,
                "auth.login",
                {"username": username, "ip_address": ip_address},
            )

            role_value = user.role.value if user.role else None
            return {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role_value,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "teacher_id": user.teacher_id,
                    "active": user.active,
                    "last_login": (
                        user.last_login.isoformat() if user.last_login else None
                    ),
                },
                "token": token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(minutes=self.token_expiry_minutes),
            }

    def validate_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user"""
        try:
            # Require expiration to prevent indefinite token validity if a token
            # is ever minted without an exp claim.
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"require": ["exp"]},
            )
            user_id = payload.get("user_id")

            if not user_id:
                return None

            with self.db_service.get_session() as session:
                user = session.query(User).filter_by(id=user_id, active=True).first()
                return user

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt (delegates to canonical implementation)."""
        from ..security import hash_password

        return hash_password(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash (delegates to canonical implementation)."""
        from ..security import verify_password

        return verify_password(password, password_hash)

    def _generate_jwt_token(self, user: User) -> str:
        """Generate JWT token for user"""
        role_value = user.role.value if user.role else "unknown"
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": role_value,
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=self.token_expiry_minutes),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _is_account_locked(self, session: Session, user_id: int) -> bool:
        """Check if account is locked due to failed attempts"""
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return False

        # Check if account is explicitly locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return True

        # Check recent failed attempts within lockout window
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.lockout_duration_minutes
        )
        recent_failures = (
            session.query(AuthAttempt)
            .filter(
                AuthAttempt.user_id == user_id,
                AuthAttempt.success.is_(False),
                AuthAttempt.timestamp > cutoff_time,
            )
            .count()
        )

        return recent_failures >= self.max_failed_attempts

    def _record_failed_attempt(
        self, session: Session, user_id: int, username: str, ip_address: Optional[str]
    ):
        """Record failed login attempt"""
        # Record in audit log
        self._log_event(
            session, user_id, "auth.failed_login", {"ip_address": ip_address}
        )

        # Record in auth attempts table
        auth_attempt = AuthAttempt.record_attempt(
            username=username, success=False, user_id=user_id, ip_address=ip_address
        )
        session.add(auth_attempt)

        # Update user's failed login count
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1

            # Lock account if threshold reached
            recent_failures = (
                session.query(AuthAttempt)
                .filter(
                    AuthAttempt.user_id == user_id,
                    AuthAttempt.success.is_(False),
                    AuthAttempt.timestamp
                    > datetime.now(timezone.utc)
                    - timedelta(minutes=self.lockout_duration_minutes),
                )
                .count()
            )

            if recent_failures >= self.max_failed_attempts:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=self.lockout_duration_minutes
                )

    def _clear_failed_attempts(self, session: Session, user_id: int):
        """Clear failed login attempts"""
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.failed_login_count = 0
            user.locked_until = None

    def _check_rate_limit(
        self,
        session: Session,
        *,
        user_id: Optional[int],
        username: str,
        ip_address: Optional[str],
    ) -> bool:
        """Check rate limiting for login attempts.

        Uses configured window/max settings and tolerates unknown usernames.
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.rate_limit_window_minutes
        )

        query = session.query(AuthAttempt).filter(AuthAttempt.timestamp > cutoff_time)
        if user_id is not None:
            query = query.filter(AuthAttempt.user_id == user_id)
        else:
            query = query.filter(AuthAttempt.username == username)

        # If an IP is available, scope the limit tighter to reduce shared-user issues.
        if ip_address:
            query = query.filter(AuthAttempt.ip_address == ip_address)

        recent_attempts = query.count()
        return recent_attempts < self.rate_limit_max_attempts

    def validate_password(self, password: str) -> bool:
        """Validate password strength"""
        # Check minimum length
        if len(password) < 8:
            return False

        # Check for uppercase letters
        if not any(c.isupper() for c in password):
            return False

        # Check for lowercase letters
        if not any(c.islower() for c in password):
            return False

        # Check for numbers
        if not any(c.isdigit() for c in password):
            return False

        # Check for special characters
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False

        return True

    def reset_password(self, user_id: int, new_password: str) -> bool:
        """Reset user password"""
        if not self.validate_password(new_password):
            raise AuthenticationError("Password does not meet requirements")

        with self.db_service.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False

            user.password_hash = self._hash_password(new_password)
            session.commit()

            # Log password reset
            self._log_event(session, user_id, "auth.password_reset", {})
            return True

    def authorize_user(self, user_id: int, required_role: UserRole) -> bool:
        """Check if user has required role"""
        with self.db_service.get_session() as session:
            user = session.query(User).filter_by(id=user_id, active=True).first()
            if not user:
                return False
            return user.role == required_role

    def update_profile(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        grade_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update user profile fields"""
        with self.db_service.get_session() as session:
            user = session.query(User).filter_by(id=user_id, active=True).first()
            if not user:
                raise AuthenticationError("User not found")

            # Update fields if provided
            if first_name is not None:
                if not first_name.strip():
                    raise AuthenticationError("First name cannot be empty")
                user.first_name = first_name.strip()

            if last_name is not None:
                if not last_name.strip():
                    raise AuthenticationError("Last name cannot be empty")
                user.last_name = last_name.strip()

            if email is not None:
                email = email.strip().lower()
                # Check if email is already taken by another user
                existing = (
                    session.query(User)
                    .filter(User.email == email, User.id != user_id)
                    .first()
                )
                if existing:
                    raise AuthenticationError("Email already in use")
                user.email = email

            if grade_level is not None:
                user.grade_level = grade_level.strip() if grade_level else None

            session.commit()
            session.refresh(user)

            # Log profile update
            self._log_event(
                session,
                user_id,
                "auth.profile_update",
                {
                    "updated_fields": [
                        f
                        for f, v in [
                            ("first_name", first_name),
                            ("last_name", last_name),
                            ("email", email),
                            ("grade_level", grade_level),
                        ]
                        if v is not None
                    ]
                },
            )

            role_value = user.role.value if user.role else None
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": role_value,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "grade_level": user.grade_level,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }

    def generate_password_reset_token(self, user_id: int) -> str:
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        # In a full implementation, you'd store this token in the database
        # with an expiration time
        return token

    def _log_event(
        self,
        session: Session,
        user_id: Optional[int],
        event_key: str,
        details: Dict[str, Any],
    ):
        """Log authentication event"""
        event_type = EventType.AUTH
        if "login" in event_key:
            event_type = EventType.LOGIN
        elif "logout" in event_key:
            event_type = EventType.LOGOUT
        elif "password_reset" in event_key:
            event_type = EventType.PASSWORD_RESET
        elif "account_locked" in event_key:
            event_type = EventType.ACCOUNT_LOCKED
        elif "create" in event_key:
            event_type = EventType.CREATE
        elif "update" in event_key:
            event_type = EventType.UPDATE
        elif "delete" in event_key:
            event_type = EventType.DELETE

        log_entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            details={**details, "event_key": event_key},
        )
        session.add(log_entry)
        session.commit()


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global authentication service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
