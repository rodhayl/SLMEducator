"""
Classroom API Routes

Provides messaging and help request functionality for the connected classroom.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    User,
    UserRole,
    TeacherMessage,
    HelpRequest,
    Content,
    StudyPlan,
    AssessmentQuestion,
)
from src.core.roles import is_teacher_or_admin, role_str

router = APIRouter(prefix="/api/classroom", tags=["classroom"])


# --- Pydantic Models ---


class UserListItem(BaseModel):
    """User item for recipient selection."""

    id: int
    username: str
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """Create a new message."""

    recipient_id: Optional[int] = None  # User ID
    to_username: Optional[str] = None  # Alternative: username lookup
    subject: str
    body: str


class MessageResponse(BaseModel):
    """Message response with sender/recipient info."""

    id: int
    from_id: int
    to_id: Optional[int]
    subject: str
    content: str
    read_at: Optional[datetime]
    sent_at: datetime
    archived_at: Optional[datetime] = None
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HelpRequestCreate(BaseModel):
    """Create a help request."""

    subject: str
    description: str
    urgency: int = 1  # 1-3
    # Context fields - auto-captured from student's current learning state
    content_id: Optional[int] = None  # What content the student was viewing
    study_plan_id: Optional[int] = None  # What study plan they're working on
    question_id: Optional[int] = None  # If stuck on a specific question


class HelpRequestResponse(BaseModel):
    """Help request response with full context."""

    id: int
    student_id: int
    request_text: str
    status: str
    created_at: datetime
    student_name: Optional[str] = None
    subject: Optional[str] = None
    priority: int = 1
    # Context fields - what the student was studying
    content_id: Optional[int] = None
    content_title: Optional[str] = None
    content_type: Optional[str] = None
    study_plan_id: Optional[int] = None
    study_plan_title: Optional[str] = None
    question_id: Optional[int] = None
    question_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---


@router.get("/users", response_model=List[UserListItem])
async def list_users_for_messaging(
    role: Optional[str] = Query(None, description="Filter by role: student, teacher"),
    search: Optional[str] = Query(None, description="Search by name or username"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List users available for messaging.

    Args:
        role: Optional filter by user role (student/teacher).
        search: Optional text search on username or name.
        limit: Maximum users to return (default 50).

    Returns:
        List of users with id, username, full_name, and role.
    """
    query = db.query(User).filter(
        User.active == True, User.id != current_user.id  # Exclude self
    )

    # Filter by role if specified
    if role:
        try:
            role_enum = UserRole(role.lower())
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {role}. Valid options: student, teacher, admin",
            )

    # Search by name or username
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
            )
        )

    # Order by name and limit
    users = query.order_by(User.first_name, User.last_name).limit(limit).all()

    return [
        UserListItem(
            id=u.id,
            username=u.username,
            full_name=f"{u.first_name} {u.last_name}",
            role=role_str(u),
        )
        for u in users
    ]


@router.get("/messages", response_model=List[MessageResponse])
async def get_messages(
    folder: str = "inbox",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get messages for current user.

    Args:
        folder: 'inbox' (received), 'sent', or 'archived'
    """
    if folder == "sent":
        # Sent messages - where current user is sender
        msgs = (
            db.query(TeacherMessage)
            .options(joinedload(TeacherMessage.recipient))
            .filter(
                TeacherMessage.from_id == current_user.id,
                TeacherMessage.archived_at.is_(None),
            )
            .order_by(TeacherMessage.sent_at.desc())
            .all()
        )

        result = []
        for msg in msgs:
            recipient_name = "Unknown"
            if msg.recipient:
                recipient_name = f"{msg.recipient.first_name} {msg.recipient.last_name}"

            result.append(
                MessageResponse(
                    id=msg.id,
                    from_id=msg.from_id,
                    to_id=msg.to_id,
                    subject=msg.subject,
                    content=msg.content,
                    read_at=msg.read_at,
                    sent_at=msg.sent_at,
                    archived_at=msg.archived_at,
                    sender_name=f"{current_user.first_name} {current_user.last_name}",
                    recipient_name=recipient_name,
                )
            )
        return result

    elif folder == "archived":
        # Archived messages - both sent and received
        msgs = (
            db.query(TeacherMessage)
            .options(
                joinedload(TeacherMessage.sender), joinedload(TeacherMessage.recipient)
            )
            .filter(
                or_(
                    TeacherMessage.to_id == current_user.id,
                    TeacherMessage.from_id == current_user.id,
                ),
                TeacherMessage.archived_at.isnot(None),
            )
            .order_by(TeacherMessage.archived_at.desc())
            .all()
        )

        result = []
        for msg in msgs:
            sender_name = "Unknown"
            recipient_name = "Unknown"
            if msg.sender:
                sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"
            if msg.recipient:
                recipient_name = f"{msg.recipient.first_name} {msg.recipient.last_name}"

            result.append(
                MessageResponse(
                    id=msg.id,
                    from_id=msg.from_id,
                    to_id=msg.to_id,
                    subject=msg.subject,
                    content=msg.content,
                    read_at=msg.read_at,
                    sent_at=msg.sent_at,
                    archived_at=msg.archived_at,
                    sender_name=sender_name,
                    recipient_name=recipient_name,
                )
            )
        return result

    else:
        # Inbox - received messages (default)
        msgs = (
            db.query(TeacherMessage)
            .options(joinedload(TeacherMessage.sender))
            .filter(
                TeacherMessage.to_id == current_user.id,
                TeacherMessage.archived_at.is_(None),
            )
            .order_by(TeacherMessage.sent_at.desc())
            .all()
        )

        result = []
        for msg in msgs:
            sender_name = "Unknown"
            if msg.sender:
                sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"

            result.append(
                MessageResponse(
                    id=msg.id,
                    from_id=msg.from_id,
                    to_id=msg.to_id,
                    subject=msg.subject,
                    content=msg.content,
                    read_at=msg.read_at,
                    sent_at=msg.sent_at,
                    archived_at=msg.archived_at,
                    sender_name=sender_name,
                    recipient_name=None,
                )
            )
        return result


@router.post("/messages", response_model=MessageResponse)
async def send_message(
    msg: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message to another user.

    Accepts either recipient_id (int) or to_username (string).
    """
    recipient_id = msg.recipient_id

    # If username provided instead of ID, look up the user
    if not recipient_id and msg.to_username:
        recipient = db.query(User).filter(User.username == msg.to_username).first()
        if not recipient:
            raise HTTPException(
                status_code=404, detail=f"User '{msg.to_username}' not found"
            )
        recipient_id = recipient.id

    if not recipient_id:
        raise HTTPException(
            status_code=400,
            detail="Recipient required. Provide either recipient_id or to_username.",
        )

    # Verify recipient exists
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    new_msg = TeacherMessage(
        from_id=current_user.id,
        to_id=recipient_id,
        subject=msg.subject,
        content=msg.body,
        sent_at=datetime.now(),
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    sender_name = f"{current_user.first_name} {current_user.last_name}"
    recipient_name = f"{recipient.first_name} {recipient.last_name}"

    return MessageResponse(
        id=new_msg.id,
        from_id=new_msg.from_id,
        to_id=new_msg.to_id,
        subject=new_msg.subject,
        content=new_msg.content,
        read_at=new_msg.read_at,
        sent_at=new_msg.sent_at,
        archived_at=new_msg.archived_at,
        sender_name=sender_name,
        recipient_name=recipient_name,
    )


# NOTE: This route MUST be defined BEFORE any /messages/{message_id} routes
# to avoid FastAPI matching "unread-count" as a message_id
@router.get("/messages/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get count of unread messages for the current user."""
    count = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.to_id == current_user.id,
            TeacherMessage.read_at.is_(None),
            TeacherMessage.archived_at.is_(None),
        )
        .count()
    )

    return {"unread_count": count}


@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a message as read."""
    msg = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.id == message_id, TeacherMessage.to_id == current_user.id
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if not msg.read_at:
        msg.read_at = datetime.now()
        db.commit()

    return {"status": "ok", "read_at": msg.read_at}


@router.post("/messages/{message_id}/unread")
async def mark_message_unread(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a message as unread."""
    msg = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.id == message_id, TeacherMessage.to_id == current_user.id
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.read_at = None
    db.commit()

    return {"status": "ok", "read_at": None}


@router.post("/messages/{message_id}/archive")
async def archive_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Archive a message. Works for both sent and received messages."""
    msg = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.id == message_id,
            or_(
                TeacherMessage.to_id == current_user.id,
                TeacherMessage.from_id == current_user.id,
            ),
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if not msg.archived_at:
        msg.archived_at = datetime.now()
        db.commit()

    return {"status": "ok", "archived_at": msg.archived_at}


@router.post("/messages/{message_id}/unarchive")
async def unarchive_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unarchive a message. Restores to inbox/sent."""
    msg = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.id == message_id,
            or_(
                TeacherMessage.to_id == current_user.id,
                TeacherMessage.from_id == current_user.id,
            ),
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.archived_at = None
    db.commit()

    return {"status": "ok", "archived_at": None}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a message permanently.

    Users can only delete messages they sent or received.
    """
    msg = (
        db.query(TeacherMessage)
        .filter(
            TeacherMessage.id == message_id,
            or_(
                TeacherMessage.to_id == current_user.id,
                TeacherMessage.from_id == current_user.id,
            ),
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(msg)
    db.commit()

    return {"status": "ok", "deleted": True}


@router.get("/help", response_model=List[HelpRequestResponse])
async def get_help_requests(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get help requests with full learning context. Teachers see all, Students see theirs."""
    query = db.query(HelpRequest).options(
        joinedload(HelpRequest.student),
        joinedload(HelpRequest.content),
        joinedload(HelpRequest.study_plan),
        joinedload(HelpRequest.question),
    )

    if not is_teacher_or_admin(current_user):
        query = query.filter(HelpRequest.student_id == current_user.id)

    requests = query.order_by(HelpRequest.created_at.desc()).all()

    result = []
    for req in requests:
        student_name = "Unknown"
        if req.student:
            student_name = f"{req.student.first_name} {req.student.last_name}"

        # Parse subject from request_text if it contains ": "
        subject = None
        if req.request_text and ": " in req.request_text:
            subject = req.request_text.split(": ", 1)[0]

        # Extract content context
        content_title = None
        content_type = None
        if req.content:
            content_title = req.content.title
            content_type = (
                req.content.content_type.value
                if hasattr(req.content.content_type, "value")
                else str(req.content.content_type)
            )

        # Extract study plan context
        study_plan_title = None
        if req.study_plan:
            study_plan_title = req.study_plan.title

        # Extract question context
        question_text = None
        if req.question:
            question_text = (
                req.question.question_text[:200] if req.question.question_text else None
            )

        result.append(
            HelpRequestResponse(
                id=req.id,
                student_id=req.student_id,
                request_text=req.request_text,
                status=req.status,
                created_at=req.created_at,
                student_name=student_name,
                subject=subject,
                priority=getattr(req, "priority", 1) or 1,
                # Context fields
                content_id=req.content_id,
                content_title=content_title,
                content_type=content_type,
                study_plan_id=req.study_plan_id,
                study_plan_title=study_plan_title,
                question_id=req.question_id,
                question_text=question_text,
            )
        )

    return result


@router.post("/help", response_model=HelpRequestResponse)
async def create_help_request(
    req: HelpRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Student raises a hand for help with automatic learning context capture."""
    new_req = HelpRequest(
        student_id=current_user.id,
        request_text=(
            f"{req.subject}: {req.description}" if req.subject else req.description
        ),
        priority=req.urgency,
        status="open",
        created_at=datetime.now(),
        # Store learning context
        content_id=req.content_id,
        study_plan_id=req.study_plan_id,
        question_id=req.question_id,
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    student_name = f"{current_user.first_name} {current_user.last_name}"

    # Load context titles for response
    content_title = None
    content_type = None
    if req.content_id:
        content = db.query(Content).filter(Content.id == req.content_id).first()
        if content:
            content_title = content.title
            content_type = (
                content.content_type.value
                if hasattr(content.content_type, "value")
                else str(content.content_type)
            )

    study_plan_title = None
    if req.study_plan_id:
        plan = db.query(StudyPlan).filter(StudyPlan.id == req.study_plan_id).first()
        if plan:
            study_plan_title = plan.title

    question_text = None
    if req.question_id:
        question = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.id == req.question_id)
            .first()
        )
        if question:
            question_text = (
                question.question_text[:200] if question.question_text else None
            )

    return HelpRequestResponse(
        id=new_req.id,
        student_id=new_req.student_id,
        request_text=new_req.request_text,
        status=new_req.status,
        created_at=new_req.created_at,
        student_name=student_name,
        subject=req.subject,
        priority=req.urgency,
        content_id=req.content_id,
        content_title=content_title,
        content_type=content_type,
        study_plan_id=req.study_plan_id,
        study_plan_title=study_plan_title,
        question_id=req.question_id,
        question_text=question_text,
    )


@router.post("/help/{request_id}/resolve")
async def resolve_help_request(
    request_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Teacher resolves a help request."""
    if not is_teacher_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Only teachers/admins can resolve help requests"
        )

    req = db.query(HelpRequest).filter(HelpRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Help request not found")

    req.status = "resolved"
    req.resolved_by_id = current_user.id
    req.resolved_at = datetime.now()
    if notes:
        req.resolution_notes = notes

    db.commit()

    return {"status": "resolved", "resolved_at": req.resolved_at}
