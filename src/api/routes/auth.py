from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from fastapi.security import OAuth2PasswordRequestForm

from src.core.services.auth import get_auth_service, AuthService, AuthenticationError
from src.core.models import UserRole, User
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
            role_enum = UserRole.TEACHER  # Fallback

        # Role-based creation policy:
        # - Unauthenticated self-registration: teacher/student only
        # - Admins can create admin/teacher/student
        # - Teachers can create students only
        # - Students cannot create users
        if current_user is None:
            if role_enum == UserRole.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail="Admin account creation requires authentication",
                )
        elif current_user.role == UserRole.ADMIN:
            pass
        elif current_user.role == UserRole.TEACHER:
            if role_enum != UserRole.STUDENT:
                raise HTTPException(
                    status_code=403, detail="Teachers can only create student accounts"
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
    current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service),
):
    """List users for admin/teacher management views."""
    with auth_service.db_service.get_session() as session:
        query = session.query(User).filter(
            User.active.is_(True), User.id != current_user.id
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
            )
            for u in users
        ]
