"""
Annotations API Routes

Provides endpoints for Phase 2 content annotations:
- Create annotations on content
- List annotations for content
- Delete annotations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import User, Content, Annotation
from src.core.roles import is_teacher_or_admin

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


# --- Pydantic Models ---


class AnnotationCreate(BaseModel):
    """Create new annotation"""

    content_id: int
    annotation_text: str
    annotation_type: str = "comment"  # comment, question, highlight
    text_selection_start: Optional[int] = None
    text_selection_end: Optional[int] = None
    is_public: bool = True


class AnnotationResponse(BaseModel):
    """Annotation response"""

    id: int
    content_id: int
    user_id: int
    user_name: str
    annotation_text: str
    annotation_type: str
    text_selection_start: Optional[int]
    text_selection_end: Optional[int]
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---


@router.get("/", response_model=List[AnnotationResponse])
async def list_annotations(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get annotations for a specific content item"""
    # Query annotations for this content
    query = db.query(Annotation).filter(Annotation.content_id == content_id)

    # Filter: public ones OR user's own
    query = query.filter(
        (Annotation.is_public == True) | (Annotation.user_id == current_user.id)
    )

    annotations = query.order_by(Annotation.created_at.desc()).all()

    result = []
    for ann in annotations:
        user = db.query(User).filter(User.id == ann.user_id).first()
        result.append(
            AnnotationResponse(
                id=ann.id,
                content_id=ann.content_id,
                user_id=ann.user_id,
                user_name=user.full_name if user else f"User #{ann.user_id}",
                annotation_text=ann.annotation_text,
                annotation_type=ann.annotation_type,
                text_selection_start=ann.text_selection_start,
                text_selection_end=ann.text_selection_end,
                is_public=ann.is_public,
                created_at=ann.created_at,
            )
        )

    return result


@router.post("/", response_model=AnnotationResponse)
async def create_annotation(
    data: AnnotationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new annotation on content"""
    # Verify content exists
    content = db.query(Content).filter(Content.id == data.content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    annotation = Annotation(
        content_id=data.content_id,
        user_id=current_user.id,
        annotation_text=data.annotation_text,
        annotation_type=data.annotation_type,
        text_selection_start=data.text_selection_start,
        text_selection_end=data.text_selection_end,
        is_public=data.is_public,
        created_at=datetime.now(),
    )

    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    return AnnotationResponse(
        id=annotation.id,
        content_id=annotation.content_id,
        user_id=annotation.user_id,
        user_name=current_user.full_name,
        annotation_text=annotation.annotation_text,
        annotation_type=annotation.annotation_type,
        text_selection_start=annotation.text_selection_start,
        text_selection_end=annotation.text_selection_end,
        is_public=annotation.is_public,
        created_at=annotation.created_at,
    )


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an annotation (owner or teacher only)"""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Permission check (owner, teacher, or admin)
    if annotation.user_id != current_user.id and not is_teacher_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Cannot delete this annotation")

    db.delete(annotation)
    db.commit()

    return {"status": "ok", "message": "Annotation deleted"}
