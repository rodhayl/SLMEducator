from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.core.services.temporal_service import utc_now

from src.core.services.auth import get_auth_service, AuthService, AuthenticationError
from src.core.models import UserRole, User
from src.api.policies import teacher_student_ids
from src.api.security import (
    get_current_user,
    get_optional_current_user,
    user_role_str,
    require_roles,
)

# Models


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    teacher_id: Optional[int] = Field(default=None, gt=0)
    role: str = (
        "teacher"  # Default to teacher for first user, validation logic handled in service or UI
    )


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    first_name: str
    last_name: str
    grade_level: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    grade_level: Optional[str] = None


class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    first_name: str
    last_name: str
    grade_level: Optional[str] = None
    active: bool = True
    xp: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    teacher_id: Optional[int] = None


router = APIRouter(prefix="/api/auth", tags=["auth"])

# NOTE: get_current_user/get_optional_current_user + oauth2 schemes live in src.api.security


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    current_user: Optional[User] = Depends(get_optional_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        # Convert string role to enum
        try:
            role_enum = UserRole(user_data.role.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid role")

        # Bootstrap creates the first administrator; all other accounts require approval.
        if current_user is None:
            raise HTTPException(
                status_code=403,
                detail="Account creation requires an administrator or teacher",
            )
        elif current_user.role == UserRole.ADMIN:
            pass
        elif current_user.role == UserRole.TEACHER:
            if role_enum != UserRole.STUDENT:
                raise HTTPException(
                    status_code=403, detail="Teachers can only create student accounts"
                )
            if user_data.teacher_id not in (None, current_user.id):
                raise HTTPException(
                    status_code=403,
                    detail="Teachers can only enroll their own learners",
                )
        else:
            raise HTTPException(
                status_code=403, detail="Students cannot create user accounts"
            )

        user = auth_service.register_user(
            username=user_data.username,
            email=str(user_data.email),
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=role_enum,
            teacher_id=(
                current_user.id
                if current_user.role == UserRole.TEACHER
                else user_data.teacher_id
            ),
        )
        return user
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    # Compatible with OAuth2 standard form data
    try:
        result = auth_service.login_user(form_data.username, form_data.password)
        return {
            "access_token": result["token"],
            "token_type": "bearer",
            "user": result["user"],
        }
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": user_role_str(current_user),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "grade_level": current_user.grade_level,
        "created_at": (
            current_user.created_at.isoformat() if current_user.created_at else None
        ),
        "last_login": (
            current_user.last_login.isoformat() if current_user.last_login else None
        ),
    }


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update current user's profile"""
    try:
        updated_user = auth_service.update_profile(
            user_id=current_user.id,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            email=str(profile_data.email) if profile_data.email else None,
            grade_level=profile_data.grade_level,
        )
        return updated_user
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    role: Optional[str] = Query(
        None, description="Filter by role: student, teacher, admin"
    ),
    limit: int = Query(200, ge=1, le=500),
    include_inactive: bool = False,
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service),
):
    """List users for admin/teacher management views."""
    with auth_service.db_service.get_session() as session:
        if include_inactive and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, detail="Only administrators can view inactive accounts"
            )
        query = session.query(User).filter(User.id != current_user.id)
        if not include_inactive:
            query = query.filter(User.active.is_(True))

        if current_user.role == UserRole.TEACHER:
            query = query.filter(
                User.id.in_(teacher_student_ids(session, current_user.id))
            )

        if role:
            try:
                role_enum = UserRole(role.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid role")
            query = query.filter(User.role == role_enum)

        users = query.order_by(User.first_name, User.last_name).limit(limit).all()
        return [
            UserListResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                role=user_role_str(u),
                first_name=u.first_name or "",
                last_name=u.last_name or "",
                grade_level=getattr(u, "grade_level", None),
                active=bool(getattr(u, "active", True)),
                xp=int(getattr(u, "xp", 0) or 0),
                level=int(getattr(u, "level", 1) or 1),
                current_streak=int(getattr(u, "current_streak", 0) or 0),
                longest_streak=int(getattr(u, "longest_streak", 0) or 0),
                teacher_id=u.teacher_id,
            )
            for u in users
        ]


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class AccountStatusChange(BaseModel):
    active: bool
    confirm: bool = False


class AccountPasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)
    confirm: bool = False


@router.patch("/users/{user_id}/status")
def change_account_status(
    user_id: int,
    request: AccountStatusChange,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Apply a confirmed administrator action while preserving account history."""
    if not request.confirm:
        raise HTTPException(
            status_code=409, detail="Confirm the selected account status change"
        )
    db.query(User).filter(User.role == UserRole.ADMIN).update(
        {User.xp: User.xp}, synchronize_session=False
    )
    actor = db.get(User, current_user.id)
    db.refresh(actor)
    if not actor.active or actor.role != UserRole.ADMIN:
        db.rollback()
        raise HTTPException(status_code=403, detail="Active administrator required")
    target = db.get(User, user_id)
    if not target:
        db.rollback()
        raise HTTPException(status_code=404, detail="Account not found")
    if not request.active and (
        target.id == actor.id
        or (
            target.role == UserRole.ADMIN
            and db.query(User).filter_by(role=UserRole.ADMIN, active=True).count() <= 1
        )
    ):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot deactivate yourself or the last active administrator",
        )
    settings = dict(target.settings or {})
    settings["auth_version"] = int(settings.get("auth_version", 0)) + 1
    history = list(settings.get("account_admin_history", []))
    history.append(
        {
            "action": "activate" if request.active else "deactivate",
            "actor_id": actor.id,
            "at": utc_now().isoformat(),
        }
    )
    settings["account_admin_history"] = history
    target.settings = settings
    target.active = request.active
    db.commit()
    return {"id": target.id, "active": target.active, "sessions_revoked": True}


@router.post("/users/{user_id}/reset-password")
def reset_account_password(
    user_id: int,
    request: AccountPasswordReset,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Accept an explicitly entered credential; never generate, send or return it."""
    if not request.confirm:
        raise HTTPException(
            status_code=409, detail="Confirm password recovery for the selected account"
        )
    if user_id == current_user.id:
        raise HTTPException(
            status_code=409,
            detail="Use the current-password change flow for your own account",
        )
    if len(request.new_password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=422, detail="Password must be at most 72 UTF-8 bytes"
        )
    try:
        if not auth_service.reset_password(
            user_id, request.new_password, actor_id=current_user.id
        ):
            raise HTTPException(status_code=404, detail="Account not found")
        return {"id": user_id, "reset": True, "sessions_revoked": True}
    except AuthenticationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Rotate a known password and invalidate previously issued sessions."""
    try:
        auth_service.change_password(
            current_user.id, data.current_password, data.new_password
        )
        return {"success": True, "reauthentication_required": True}
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
