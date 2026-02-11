from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import User, Content, ContentType
from src.core.roles import is_admin, is_student, is_teacher, is_teacher_or_admin

import logging

router = APIRouter(prefix="/api/content", tags=["content"])


def _student_assigned_plan_ids(db: Session, student_id: int) -> List[int]:
    from src.core.models import StudentStudyPlan

    rows = (
        db.query(StudentStudyPlan.study_plan_id)
        .filter(StudentStudyPlan.student_id == student_id)
        .all()
    )
    return [r[0] for r in rows]


def _public_plan_ids(db: Session) -> List[int]:
    from src.core.models import StudyPlan

    rows = db.query(StudyPlan.id).filter(StudyPlan.is_public.is_(True)).all()
    return [r[0] for r in rows]


def _teacher_student_ids(db: Session, teacher_id: int) -> List[int]:
    """Students assigned to any study plan created by this teacher."""
    from src.core.models import StudentStudyPlan, StudyPlan

    rows = (
        db.query(StudentStudyPlan.student_id)
        .join(StudyPlan, StudyPlan.id == StudentStudyPlan.study_plan_id)
        .filter(StudyPlan.creator_id == teacher_id)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def _content_ids_for_plan_ids(db: Session, plan_ids: List[int]) -> List[int]:
    if not plan_ids:
        return []
    from src.core.models import StudyPlanContent

    rows = (
        db.query(StudyPlanContent.content_id)
        .filter(StudyPlanContent.study_plan_id.in_(plan_ids))
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def _can_view_content(db: Session, current_user: User, content: Content) -> bool:
    if is_admin(current_user):
        return True

    if is_teacher(current_user):
        if content.creator_id == current_user.id:
            return True

        # Teachers may view student-created personal Q&A if the student shared it
        # and that student is assigned to one of the teacher's plans.
        if (
            content.is_personal
            and content.shared_with_teacher
            and content.content_type == ContentType.QA
            and content.creator_id is not None
        ):
            return content.creator_id in set(_teacher_student_ids(db, current_user.id))

        return False

    # Students can view their own content, and any non-personal content that is
    # part of a study plan assigned to them (or public).
    if is_student(current_user):
        if content.creator_id == current_user.id:
            return True
        if content.is_personal:
            return False
        plan_ids = list(
            set(_student_assigned_plan_ids(db, current_user.id) + _public_plan_ids(db))
        )
        allowed_content_ids = set(_content_ids_for_plan_ids(db, plan_ids))
        if content.id in allowed_content_ids:
            return True
        if content.study_plan_id and content.study_plan_id in set(plan_ids):
            return True
        return False

    return False


def _require_student_can_create_content(
    db: Session, user: User, resolved_type: ContentType, study_plan_id: Optional[int]
):
    """
    Student content creation policy:
    - Students may only create personal Q&A items (ContentType.QA).
    - They may optionally attach it to a study plan that is assigned to them.
    - Visibility is controlled via `shared_with_teacher`.
    """
    if not is_student(user):
        return
    if resolved_type != ContentType.QA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only create Q&A content",
        )
    if study_plan_id is not None:
        assigned = set(_student_assigned_plan_ids(db, user.id))
        if study_plan_id not in assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Study plan is not assigned to you",
            )


logger = logging.getLogger(__name__)

# --- Pydantic Models ---


class ContentCreate(BaseModel):
    title: str
    content_type: Optional[str] = None  # Standard field name
    type: Optional[str] = None  # Alias for compatibility with frontend
    description: Optional[str] = None
    content_data: Optional[Dict[str, Any]] = None  # Standard field name
    data: Optional[Dict[str, Any]] = None  # Alias for compatibility
    difficulty: int = 1
    is_personal: bool = False
    shared_with_teacher: bool = False
    study_plan_id: Optional[int] = (
        None  # Link to study plan if generated via Course Designer
    )

    def get_content_type(self) -> str:
        """Get content type from either field."""
        return self.content_type or self.type or "lesson"

    def get_content_data(self) -> Dict[str, Any]:
        """Get content data from either field."""
        return self.content_data or self.data or {}


class ContentResponse(BaseModel):
    id: int
    title: str
    content_type: Any
    description: Optional[str]
    created_at: datetime
    difficulty: int
    is_personal: bool
    shared_with_teacher: bool = False
    creator_id: Optional[int] = None
    creator_username: Optional[str] = None
    creator_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---


@router.get("/", response_model=List[ContentResponse])
async def list_content(
    content_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Role-aware content listing:
    - Students: content from assigned/public study plans + their own personal content.
    - Teachers: their own content + student-shared personal Q&A from their assigned students.
    - Admins: all content.
    """
    from sqlalchemy import or_, and_

    query = db.query(Content)

    if content_type:
        query = query.filter(Content.content_type == ContentType(content_type))

    if is_admin(current_user):
        items = query.order_by(Content.created_at.desc()).all()
    elif is_teacher(current_user):
        student_ids = _teacher_student_ids(db, current_user.id)
        teacher_filter = or_(
            Content.creator_id == current_user.id,
            and_(
                Content.creator_id.in_(student_ids) if student_ids else False,
                Content.is_personal.is_(True),
                Content.shared_with_teacher.is_(True),
                Content.content_type == ContentType.QA,
            ),
        )
        items = query.filter(teacher_filter).order_by(Content.created_at.desc()).all()
    else:
        plan_ids = list(
            set(_student_assigned_plan_ids(db, current_user.id) + _public_plan_ids(db))
        )
        plan_content_ids = set(_content_ids_for_plan_ids(db, plan_ids))
        student_filter = or_(
            Content.creator_id == current_user.id,
            and_(
                Content.is_personal.is_(False),
                or_(
                    Content.study_plan_id.in_(plan_ids) if plan_ids else False,
                    Content.id.in_(plan_content_ids) if plan_content_ids else False,
                ),
            ),
        )
        items = query.filter(student_filter).order_by(Content.created_at.desc()).all()

    # Manual conversion to avoid Pydantic issues with missing 'description' attribute on Content model
    creator_ids = {i.creator_id for i in items if i.creator_id is not None}
    creator_map: Dict[int, Dict[str, str]] = {}
    if creator_ids:
        from src.core.models import User as DbUser

        users = db.query(DbUser).filter(DbUser.id.in_(list(creator_ids))).all()
        for u in users:
            creator_map[u.id] = {
                "username": u.username,
                "name": f"{u.first_name} {u.last_name}".strip(),
            }

    result = []
    for item in items:
        ctype = (
            item.content_type.value
            if hasattr(item.content_type, "value")
            else str(item.content_type)
        )
        creator_meta = creator_map.get(item.creator_id or -1, {})
        result.append(
            {
                "id": item.id,
                "title": item.title,
                "content_type": ctype,
                "description": None,
                "created_at": item.created_at,
                "difficulty": item.difficulty,
                "is_personal": item.is_personal,
                "shared_with_teacher": item.shared_with_teacher,
                "creator_id": item.creator_id,
                "creator_username": creator_meta.get("username"),
                "creator_name": creator_meta.get("name"),
            }
        )
    return result


# --- Hierarchical Tree View ---
# NOTE: This route MUST be placed before /{content_id} to avoid FastAPI matching "tree" as a content_id


class ContentTreeItem(BaseModel):
    """Content item with study plan context."""

    id: int
    title: str
    content_type: str
    difficulty: int
    created_at: datetime
    study_plan_id: Optional[int]
    study_plan_title: Optional[str]
    is_personal: bool = False
    shared_with_teacher: bool = False
    creator_id: Optional[int] = None
    creator_username: Optional[str] = None
    creator_name: Optional[str] = None


class ContentTree(BaseModel):
    """Hierarchical content organized by study plan."""

    standalone: List[ContentTreeItem]
    by_study_plan: Dict[int, Any]  # {plan_id: {title, contents: []}}


@router.get("/tree", response_model=ContentTree)
async def get_content_tree(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get content organized by study plan hierarchy.
    Returns standalone content and content grouped by study plan.
    """
    from src.core.models import StudyPlan, StudyPlanContent

    try:
        standalone: List[ContentTreeItem] = []
        by_plan: Dict[int, Dict[str, Any]] = {}

        if is_admin(current_user):
            plan_ids = [p[0] for p in db.query(StudyPlan.id).all()]
            plan_content_ids = _content_ids_for_plan_ids(db, plan_ids)
            content_rows = (
                db.query(StudyPlanContent.study_plan_id, Content)
                .join(Content, Content.id == StudyPlanContent.content_id)
                .filter(
                    StudyPlanContent.study_plan_id.in_(plan_ids) if plan_ids else False
                )
                .order_by(
                    StudyPlanContent.study_plan_id,
                    StudyPlanContent.phase_index,
                    StudyPlanContent.order_index,
                )
                .all()
            )
            extra = (
                db.query(Content)
                .filter(
                    Content.id.notin_(plan_content_ids) if plan_content_ids else True
                )
                .order_by(Content.created_at.desc())
                .all()
            )
        elif is_teacher(current_user):
            plan_ids = [
                p[0]
                for p in db.query(StudyPlan.id)
                .filter(StudyPlan.creator_id == current_user.id)
                .all()
            ]
            plan_content_ids = _content_ids_for_plan_ids(db, plan_ids)
            content_rows = (
                db.query(StudyPlanContent.study_plan_id, Content)
                .join(Content, Content.id == StudyPlanContent.content_id)
                .filter(
                    StudyPlanContent.study_plan_id.in_(plan_ids) if plan_ids else False
                )
                .order_by(
                    StudyPlanContent.study_plan_id,
                    StudyPlanContent.phase_index,
                    StudyPlanContent.order_index,
                )
                .all()
            )
            extra = (
                db.query(Content)
                .filter(Content.creator_id == current_user.id)
                .filter(
                    Content.id.notin_(plan_content_ids) if plan_content_ids else True
                )
                .order_by(Content.created_at.desc())
                .all()
            )

            # Add student-shared personal Q&A as standalone items
            student_ids = _teacher_student_ids(db, current_user.id)
            if student_ids:
                shared_qa = (
                    db.query(Content)
                    .filter(
                        Content.creator_id.in_(student_ids),
                        Content.is_personal.is_(True),
                        Content.shared_with_teacher.is_(True),
                        Content.content_type == ContentType.QA,
                    )
                    .order_by(Content.created_at.desc())
                    .all()
                )
                extra = list(extra) + list(shared_qa)
        else:
            plan_ids = list(
                set(
                    _student_assigned_plan_ids(db, current_user.id)
                    + _public_plan_ids(db)
                )
            )
            plan_content_ids = _content_ids_for_plan_ids(db, plan_ids)
            content_rows = (
                db.query(StudyPlanContent.study_plan_id, Content)
                .join(Content, Content.id == StudyPlanContent.content_id)
                .filter(
                    StudyPlanContent.study_plan_id.in_(plan_ids) if plan_ids else False
                )
                .order_by(
                    StudyPlanContent.study_plan_id,
                    StudyPlanContent.phase_index,
                    StudyPlanContent.order_index,
                )
                .all()
            )
            extra = (
                db.query(Content)
                .filter(Content.creator_id == current_user.id)
                .order_by(Content.created_at.desc())
                .all()
            )

        # Preload creator metadata
        creator_ids: set[int] = set()
        for _, c in content_rows:
            if c.creator_id is not None:
                creator_ids.add(c.creator_id)
        for c in extra:
            if c.creator_id is not None:
                creator_ids.add(c.creator_id)

        creator_map: Dict[int, Dict[str, str]] = {}
        if creator_ids:
            from src.core.models import User as DbUser

            users = db.query(DbUser).filter(DbUser.id.in_(list(creator_ids))).all()
            for u in users:
                creator_map[u.id] = {
                    "username": u.username,
                    "name": f"{u.first_name} {u.last_name}".strip(),
                }

        # Group content by study plan based on StudyPlanContent associations
        for plan_id, content in content_rows:
            if not _can_view_content(db, current_user, content):
                continue
            meta = creator_map.get(content.creator_id or -1, {})
            content_item = ContentTreeItem(
                id=content.id,
                title=content.title,
                content_type=(
                    content.content_type.value
                    if hasattr(content.content_type, "value")
                    else str(content.content_type)
                ),
                difficulty=content.difficulty,
                created_at=content.created_at,
                study_plan_id=plan_id,
                study_plan_title=None,
                is_personal=content.is_personal,
                shared_with_teacher=content.shared_with_teacher,
                creator_id=content.creator_id,
                creator_username=meta.get("username"),
                creator_name=meta.get("name"),
            )
            if plan_id not in by_plan:
                plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
                by_plan[plan_id] = {
                    "id": plan_id,
                    "title": plan.title if plan else "Unknown Plan",
                    "contents": [],
                }
            by_plan[plan_id]["contents"].append(content_item.model_dump())

        # Add standalone items
        for content in extra:
            if not _can_view_content(db, current_user, content):
                continue
            meta = creator_map.get(content.creator_id or -1, {})
            standalone.append(
                ContentTreeItem(
                    id=content.id,
                    title=content.title,
                    content_type=(
                        content.content_type.value
                        if hasattr(content.content_type, "value")
                        else str(content.content_type)
                    ),
                    difficulty=content.difficulty,
                    created_at=content.created_at,
                    study_plan_id=content.study_plan_id,
                    study_plan_title=None,
                    is_personal=content.is_personal,
                    shared_with_teacher=content.shared_with_teacher,
                    creator_id=content.creator_id,
                    creator_username=meta.get("username"),
                    creator_name=meta.get("name"),
                )
            )

        return ContentTree(standalone=standalone, by_study_plan=by_plan)
    except Exception as e:
        logger.error(f"Error in get_content_tree: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to load content tree: {str(e)}"
        )


@router.get("/{content_id}")
async def get_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get content by ID with decrypted content_data."""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if not _can_view_content(db, current_user, content):
        raise HTTPException(status_code=403, detail="Access denied")

    # Return with decrypted content data for viewing
    # If decryption fails or content_data is null, provide a meaningful fallback
    try:
        decrypted_data = content.decrypted_content_data
    except Exception as e:
        logger.warning(f"Failed to decrypt content {content_id}: {e}")
        decrypted_data = None

    # Provide fallback content if decrypted_data is None
    if decrypted_data is None:
        # Check if title/description can provide context
        fallback_content = f"# {content.title}\n\n"
        fallback_content += (
            "This content is currently unavailable or being prepared.\n\n"
        )
        fallback_content += (
            "Please contact your instructor if this content should be accessible."
        )
        decrypted_data = {"content": fallback_content}

    creator_username = None
    creator_name = None
    if content.creator_id:
        from src.core.models import User as DbUser

        u = db.query(DbUser).filter(DbUser.id == content.creator_id).first()
        if u:
            creator_username = u.username
            creator_name = f"{u.first_name} {u.last_name}".strip()

    return {
        "id": content.id,
        "title": content.title,
        "content_type": content.content_type,
        "description": None,
        "created_at": content.created_at,
        "difficulty": content.difficulty,
        "is_personal": content.is_personal,
        "shared_with_teacher": content.shared_with_teacher,
        "creator_id": content.creator_id,
        "creator_username": creator_username,
        "creator_name": creator_name,
        "content_data": decrypted_data,
    }


@router.post("/", response_model=ContentResponse)
async def create_content(
    content_data: ContentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Use helper methods to get values from either field name
        resolved_type = content_data.get_content_type()
        resolved_data = content_data.get_content_data()

        resolved_enum = ContentType(resolved_type)

        if is_student(current_user):
            _require_student_can_create_content(
                db, current_user, resolved_enum, content_data.study_plan_id
            )
            is_personal = True
            shared_with_teacher = bool(content_data.shared_with_teacher)
        else:
            if not is_teacher_or_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
                )
            is_personal = bool(content_data.is_personal)
            shared_with_teacher = bool(content_data.shared_with_teacher)

        new_content = Content(
            title=content_data.title,
            content_type=resolved_enum,
            difficulty=content_data.difficulty,
            creator_id=current_user.id,
            study_plan_id=content_data.study_plan_id,  # Link to study plan if provided
            is_personal=is_personal,
            shared_with_teacher=shared_with_teacher,
            created_at=datetime.now(),
        )
        new_content.set_encrypted_content_data(resolved_data)

        db.add(new_content)
        db.commit()
        db.refresh(new_content)

        # Manual conversion to avoid Pydantic/SQLAlchemy issues
        return {
            "id": new_content.id,
            "title": new_content.title,
            "content_type": new_content.content_type,
            "description": None,
            "created_at": new_content.created_at,
            "difficulty": new_content.difficulty,
            "is_personal": new_content.is_personal,
            "shared_with_teacher": new_content.shared_with_teacher,
            "creator_id": new_content.creator_id,
        }
    except ValueError as ve:
        db.rollback()
        logger.warning(f"Validation error creating content: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating content: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create content. Please try again."
        )


class ContentUpdate(BaseModel):
    """Pydantic model for updating content."""

    title: Optional[str] = None
    difficulty: Optional[int] = None
    content_data: Optional[Dict[str, Any]] = None
    is_personal: Optional[bool] = None
    shared_with_teacher: Optional[bool] = None


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    update_data: ContentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update content by ID. Only the creator can update their content."""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Ownership / permissions
    if is_admin(current_user):
        pass
    elif is_teacher(current_user):
        if content.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only edit your own content"
            )
    else:
        # Students can only edit their own personal Q&A content
        if content.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only edit your own content"
            )
        if not (content.is_personal and content.content_type == ContentType.QA):
            raise HTTPException(
                status_code=403, detail="Students can only edit their own Q&A content"
            )

    try:
        # Update fields if provided
        if update_data.title is not None:
            content.title = update_data.title
        if update_data.difficulty is not None:
            content.difficulty = update_data.difficulty
        if update_data.is_personal is not None:
            # Prevent students from toggling visibility flags that would leak content.
            if is_student(current_user):
                raise HTTPException(
                    status_code=403, detail="Students cannot change personal visibility"
                )
            content.is_personal = update_data.is_personal
        if update_data.shared_with_teacher is not None:
            # Students may toggle whether their personal Q&A is visible to their teacher.
            content.shared_with_teacher = bool(update_data.shared_with_teacher)
        if update_data.content_data is not None:
            content.set_encrypted_content_data(update_data.content_data)

        db.commit()
        db.refresh(content)

        return {
            "id": content.id,
            "title": content.title,
            "content_type": content.content_type,
            "description": None,
            "created_at": content.created_at,
            "difficulty": content.difficulty,
            "is_personal": content.is_personal,
            "shared_with_teacher": content.shared_with_teacher,
            "creator_id": content.creator_id,
        }
    except ValueError as ve:
        db.rollback()
        logger.warning(f"Validation error updating content {content_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating content {content_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update content. Please try again."
        )


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete content by ID. Only the creator can delete their content."""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if is_admin(current_user):
        pass
    elif is_teacher(current_user):
        if content.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only delete your own content"
            )
    else:
        if content.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only delete your own content"
            )
        if not (content.is_personal and content.content_type == ContentType.QA):
            raise HTTPException(
                status_code=403, detail="Students can only delete their own Q&A content"
            )

    try:
        db.delete(content)
        db.commit()
        return {"message": "Content deleted successfully", "id": content_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting content {content_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete content. Please try again."
        )


# --- Batch Operations ---


class BatchContentItem(BaseModel):
    """Single item for batch content creation."""

    title: str
    content_type: str = "lesson"
    content_data: Optional[Dict[str, Any]] = None
    difficulty: int = 1


class BatchContentCreate(BaseModel):
    """Batch create multiple content items."""

    items: List[BatchContentItem]
    study_plan_id: Optional[int] = None
    phase_index: int = 0


@router.post("/batch", response_model=Dict[str, Any])
async def create_content_batch(
    batch_data: BatchContentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create multiple content items at once.
    Useful for AI-generated content packages (lesson + exercises).
    """
    from src.core.models import StudyPlan, StudyPlanContent

    if not is_teacher_or_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    # Verify study plan if provided
    if batch_data.study_plan_id:
        plan = (
            db.query(StudyPlan).filter(StudyPlan.id == batch_data.study_plan_id).first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")
        if (not is_admin(current_user)) and plan.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only add content to your own study plans",
            )

    created_items = []

    try:
        # Get starting order index
        if batch_data.study_plan_id:
            max_order = (
                db.query(StudyPlanContent)
                .filter(
                    StudyPlanContent.study_plan_id == batch_data.study_plan_id,
                    StudyPlanContent.phase_index == batch_data.phase_index,
                )
                .count()
            )
        else:
            max_order = 0

        for idx, item in enumerate(batch_data.items):
            new_content = Content(
                title=item.title,
                content_type=ContentType(item.content_type),
                difficulty=item.difficulty,
                creator_id=current_user.id,
                study_plan_id=batch_data.study_plan_id,
                created_at=datetime.now(),
            )

            if item.content_data:
                new_content.set_encrypted_content_data(item.content_data)

            db.add(new_content)
            db.flush()

            # Create association if study plan is specified
            if batch_data.study_plan_id:
                assoc = StudyPlanContent(
                    study_plan_id=batch_data.study_plan_id,
                    content_id=new_content.id,
                    phase_index=batch_data.phase_index,
                    order_index=max_order + idx,
                )
                db.add(assoc)

            created_items.append(
                {
                    "id": new_content.id,
                    "title": new_content.title,
                    "content_type": item.content_type,
                }
            )

        db.commit()

        return {
            "success": True,
            "created_count": len(created_items),
            "items": created_items,
            "study_plan_id": batch_data.study_plan_id,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error in batch content creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create content batch")
