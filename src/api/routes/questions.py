"""Saved questions, AI answers and explicitly requested assigned-teacher replies."""
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.api.policies import require_content
from src.api.routes.ai import ChatRequest, chat_with_tutor, _authorized_source
from src.core.models import User
from src.core.models.models import TutorQuestion, TutorReply
from src.core.roles import is_student, is_teacher

router = APIRouter(prefix="/api/questions", tags=["questions"])


class NewQuestion(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_-]+$")
    question: str = Field(min_length=1, max_length=4000)
    content_id: Optional[int] = Field(default=None, gt=0)
    study_plan_id: Optional[int] = Field(default=None, gt=0)
    session_id: Optional[int] = Field(default=None, gt=0)
    source_version: Optional[str] = None
    section_ids: list[str] = Field(default_factory=list, max_length=12)


class AnswerRequest(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_-]+$")
    assistance: str = "explanation"


class TeacherTarget(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_-]+$")
    teacher_id: int = Field(gt=0)


class HumanReply(AnswerRequest):
    body: str = Field(min_length=1, max_length=50000)


def assigned_teacher(db: Session, owner: User):
    """Only an explicit active teacher assignment enables human help."""
    owner = db.get(User, owner.id) if owner else None
    if owner:
        db.refresh(owner)
    teacher = db.get(User, owner.teacher_id) if owner and owner.teacher_id else None
    return teacher if teacher and is_teacher(teacher) and teacher.active else None


def owned_question(db: Session, user: User, question_id: int):
    question = db.get(TutorQuestion, question_id)
    if question is None or question.owner_id != user.id:
        raise HTTPException(404, "Question not found")
    return question


def readable_question(db: Session, user: User, question_id: int):
    question = db.get(TutorQuestion, question_id)
    if question is None:
        raise HTTPException(404, "Question not found")
    if question.owner_id == user.id:
        return question
    owner = db.get(User, question.owner_id)
    teacher = assigned_teacher(db, owner)
    if (not is_teacher(user) or not teacher or teacher.id != user.id
            or question.teacher_id != user.id or question.teacher_status == "not_requested"):
        raise HTTPException(404, "Question not found")
    return question


def readable_ai_metadata(db: Session, question: TutorQuestion, reply: TutorReply, user: User):
    """Keep receipts/history, but never bypass current access via cached source text."""
    if reply.kind != "ai" or not reply.receipt or user.id != question.owner_id:
        return None
    response = reply.receipt.get("response")
    if not isinstance(response, dict) or not response.get("source"):
        return response
    source = response["source"]
    try:
        _authorized_source(db, user, question.context.get("content_id"),
                           question.context.get("study_plan_id"), [], question.question,
                           question.context.get("session_id"))
        # A course may have lost an item since the answer was saved. Rechecking
        # only its current graph cannot authorize historical sections/titles.
        references = list(source.get("references", []))
        references.extend(section["id"] for section in source.get("available_sections", []))
        matches = [re.fullmatch(r"content:([1-9][0-9]*)/.+", reference) for reference in references]
        if not matches or not all(matches):
            return {**response, "source": None}
        for content_id in {int(match.group(1)) for match in matches if match}:
            require_content(db, user, content_id)
    except (HTTPException, KeyError, TypeError, AttributeError):
        return {**response, "source": None}
    return response


def serialize(db: Session, question: TutorQuestion, user: User):
    owner = db.get(User, question.owner_id)
    teacher = assigned_teacher(db, owner)
    replies = db.query(TutorReply).filter_by(question_id=question.id).order_by(TutorReply.id).all()
    return {
        "id": question.id, "owner_id": question.owner_id, "owner_name": f"{owner.first_name} {owner.last_name}", "question": question.question,
        "created_at": question.created_at, "context": question.context,
        "teacher_status": question.teacher_status,
        "assigned_teacher_id": teacher.id if teacher else None, "shared_teacher_id": question.teacher_id,
        "teacher_available": bool(teacher),
        "teacher_name": f"{teacher.first_name} {teacher.last_name}" if teacher else None,
        "can_request_teacher": bool(is_student(user) and user.id == question.owner_id and teacher),
        "can_reply": bool(is_teacher(user) and teacher and teacher.id == user.id and question.teacher_id == user.id),
        "replies": [{"id": reply.id, "kind": reply.kind, "body": reply.body,
                     "author_id": reply.author_id,
                     "author_name": ((lambda author: f"{author.first_name} {author.last_name}" if author else "")
                                     (db.get(User, reply.author_id))) if reply.kind == "teacher" else "IA",
                     "created_at": reply.created_at,
                     "ai_metadata": readable_ai_metadata(db, question, reply, user)} for reply in replies],
    }


@router.get("")
def list_questions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(TutorQuestion)
    if is_teacher(user):
        query = query.join(User, User.id == TutorQuestion.owner_id).filter(or_(
            TutorQuestion.owner_id == user.id,
            (TutorQuestion.teacher_id == user.id) & (User.teacher_id == user.id) &
            (TutorQuestion.teacher_status != "not_requested")))
    else:
        query = query.filter(TutorQuestion.owner_id == user.id)
    return [serialize(db, q, user) for q in query.order_by(TutorQuestion.id.desc()).all()]


@router.post("")
def create_question(data: NewQuestion, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.question.strip():
        raise HTTPException(422, "Write a question")
    context = data.model_dump(exclude={"question", "client_request_id"})
    source, _ = _authorized_source(db, user, data.content_id, data.study_plan_id,
                                   data.section_ids, data.question, data.session_id)
    context["source_version"] = source.source_version if source else None
    if data.source_version and (source is None or source.source_version != data.source_version):
        raise HTTPException(409, "Source changed; review it before asking")
    # Serialize duplicate creates before committing any user-visible result.
    db.query(User).filter_by(id=user.id).update({User.xp: User.xp}, synchronize_session=False)
    existing = db.query(TutorQuestion).filter_by(owner_id=user.id, client_request_id=data.client_request_id).first()
    if existing:
        if existing.question != data.question.strip() or existing.context != context:
            db.rollback()
            raise HTTPException(409, "Request ID belongs to a different question")
        return serialize(db, existing, user)
    question = TutorQuestion(owner_id=user.id, client_request_id=data.client_request_id,
                             question=data.question.strip(), context=context)
    db.add(question)
    db.commit()
    return serialize(db, question, user)


@router.get("/capabilities")
def capabilities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Expose availability, never credentials or administrator configuration."""
    from src.core.services.shared_ai_config import shared_ai_configuration
    try:
        config = shared_ai_configuration(db)
        configured = bool(config.model and config.model.strip())
    except HTTPException:
        configured = False
    teacher = assigned_teacher(db, user) if is_student(user) else None
    return {"ai_configured": configured, "teacher_available": bool(teacher),
            "teacher_name": f"{teacher.first_name} {teacher.last_name}" if teacher else None,
            "assigned_teacher_id": teacher.id if teacher else None}


@router.get("/{question_id}")
def get_question(question_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize(db, readable_question(db, user, question_id), user)


@router.post("/{question_id}/ai")
async def answer_question(question_id: int, data: AnswerRequest,
                          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = owned_question(db, user, question_id)
    if len(question.question) > 4000:
        raise HTTPException(422, "This historical question is too long for AI; create a shorter question. The original is preserved")
    if data.assistance not in {"hint", "explanation"}:
        raise HTTPException(422, "Unsupported assistance mode")
    previous = db.query(TutorReply).filter_by(question_id=question.id, kind="ai", client_request_id=data.client_request_id).first()
    if previous:
        # A completed durable answer survives process restart; never reinvoke it.
        if previous.receipt.get("requested_assistance") != data.assistance:
            raise HTTPException(409, "Request ID belongs to different assistance")
        from src.api.routes.ai import _permitted_assistance
        _, effective = _permitted_assistance(db, user, data.assistance)
        cached = previous.receipt["response"]
        if cached.get("effective_assistance") != effective:
            raise HTTPException(409, "Assistance policy changed; review the current policy")
        current_source, _ = _authorized_source(db, user, question.context.get("content_id"),
                           question.context.get("study_plan_id"), question.context.get("section_ids", []),
                           question.question, question.context.get("session_id"))
        if (current_source.source_version if current_source else None) != (cached.get("source") or {}).get("source_version"):
            raise HTTPException(409, "Source changed; saved answers remain historical, create a new question")
        return readable_ai_metadata(db, question, previous, user)
    request = ChatRequest(client_request_id=data.client_request_id, message=question.question,
                          assistance=data.assistance, **question.context)
    result = await chat_with_tutor(request, user, db)
    if result.status == "suggestion" and result.receipt and result.receipt.get("status") == "completed":
        # Lifecycle completion has already rechecked policy/source and cancellation.
        owned_question(db, user, question_id)
        reply = TutorReply(question_id=question_id, author_id=user.id, kind="ai",
                           body=result.response, client_request_id=data.client_request_id,
                           receipt={"requested_assistance": data.assistance, "response": result.model_dump(mode="json")})
        db.add(reply)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            previous = db.query(TutorReply).filter_by(question_id=question_id, kind="ai", client_request_id=data.client_request_id).first()
            if previous is None:
                raise
    return result


@router.post("/{question_id}/teacher")
def request_teacher(question_id: int, target: TeacherTarget, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(User).filter_by(id=user.id).update({User.xp: User.xp}, synchronize_session=False)
    question = owned_question(db, user, question_id)
    user = db.get(User, user.id)
    db.refresh(user)
    teacher = assigned_teacher(db, user)
    if not is_student(user) or not teacher:
        raise HTTPException(409, "No assigned teacher. Your question is saved; AI remains available")
    if teacher.id != target.teacher_id:
        raise HTTPException(409, "Your assigned teacher changed; review the recipient before sharing")
    requests = dict(question.teacher_request_ids or {})
    if target.client_request_id in requests:
        if requests[target.client_request_id] != target.teacher_id:
            raise HTTPException(409, "Request ID belongs to a different teacher")
        return serialize(db, question, user)
    if len(requests) >= 1000:
        raise HTTPException(409, "Create a new question before requesting more teacher help")
    requests[target.client_request_id] = teacher.id
    question.teacher_request_ids = requests
    question.teacher_id = teacher.id
    question.teacher_status = "pending"
    db.commit()
    return serialize(db, question, user)


@router.post("/{question_id}/reply")
def reply_to_question(question_id: int, data: HumanReply,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.get(TutorQuestion, question_id)
    if candidate:
        db.query(User).filter_by(id=candidate.owner_id).update({User.xp: User.xp}, synchronize_session=False)
    question = readable_question(db, user, question_id)
    if not is_teacher(user) or question.owner_id == user.id:
        raise HTTPException(403, "Only the explicitly requested assigned teacher may reply")
    if not data.body.strip():
        raise HTTPException(422, "Write a reply")
    previous = db.query(TutorReply).filter_by(question_id=question.id, kind="teacher", client_request_id=data.client_request_id).first()
    if previous:
        if previous.body != data.body.strip() or previous.author_id != user.id:
            raise HTTPException(409, "Request ID belongs to a different reply")
        return serialize(db, question, user)
    else:
        db.add(TutorReply(question_id=question.id, author_id=user.id, kind="teacher",
                          body=data.body.strip(), client_request_id=data.client_request_id))
    question.teacher_status = "answered"
    db.commit()
    return serialize(db, question, user)


@router.post("/{question_id}/resolve")
def resolve_question(question_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = readable_question(db, user, question_id)
    if question.teacher_status == "not_requested":
        raise HTTPException(409, "No teacher help was requested")
    question.teacher_status = "resolved"
    db.commit()
    return serialize(db, question, user)


class AskQuestion(NewQuestion):
    assistance: str = "explanation"


@router.post("/ask")
async def ask_question(data: AskQuestion, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save first, then answer; one explicit submit with no hidden background retry."""
    saved = create_question(NewQuestion.model_validate(data.model_dump()), user, db)
    result = await answer_question(saved["id"], AnswerRequest(client_request_id=data.client_request_id,
                                                           assistance=data.assistance), user, db)
    body = result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
    return {**body, "question_id": saved["id"]}
