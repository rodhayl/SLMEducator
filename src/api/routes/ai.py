from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.api.security import get_current_user
from src.api.dependencies import get_db, get_ai_service_dependency
from src.api.policies import require_content, require_plan
from src.core.models import User
from src.core.services.assistance_policy import effective_policy
from src.core.exceptions import AIResponseParseError, AIContentValidationError
from src.core.services.learning_context import (
    source_context,
    SourceContext,
    PROMPT_VERSION,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    context_id: Optional[int] = None
    study_plan_id: Optional[int] = None
    content_id: Optional[int] = None
    conversation_history: List[ChatMessage] = Field(default_factory=list, max_length=10)
    assistance: Literal["hint", "explanation", "example", "check_understanding"] = (
        "hint"
    )


class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None
    status: Literal["suggestion", "unavailable", "invalid_response"] = "suggestion"
    source: Optional[SourceContext] = None
    source_verified: bool = False
    prompt_version: str = PROMPT_VERSION
    assistance_policy: dict = Field(
        default_factory=lambda: {
            "mode": "explanations",
            "active_assessment_ids": [],
            "scope": "active_attempt",
            "reason": None,
        }
    )
    effective_assistance: str = "hint"


def _permitted_assistance(db: Session, user: User, requested: str) -> tuple[dict, str]:
    policy = effective_policy(db, user)
    if policy["mode"] == "disabled":
        raise HTTPException(status_code=403, detail=policy["reason"])
    return policy, "hint" if policy["mode"] == "hints_only" else requested


def _recheck_assistance(db: Session, user: User, used_mode: str) -> None:
    # A teacher's stricter choice while a provider was working also governs delivery.
    db.rollback()  # End any read snapshot before checking a concurrently saved policy.
    db.expire_all()
    current = effective_policy(db, user)
    if current["mode"] == "disabled" or (
        current["mode"] == "hints_only" and used_mode != "hint"
    ):
        raise HTTPException(status_code=403, detail=current["reason"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Use authorized, bounded source text; AI responses remain unverified suggestions."""
    policy, assistance = _permitted_assistance(db, current_user, request.assistance)
    source = None
    plan_context = None
    content_id = request.content_id or request.context_id
    if content_id:
        content = require_content(db, current_user, content_id)
        try:
            source = source_context(content)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    if request.study_plan_id:
        plan = require_plan(db, current_user, request.study_plan_id)
        plan_context = {
            "id": plan.id,
            "title": plan.title,
            "description": (plan.description or "")[:500],
        }
    ai_service = None
    try:
        # Authorization precedes service construction and every provider call.
        ai_service = get_ai_service_dependency(current_user, db)
        result = await run_in_threadpool(
            ai_service.provide_tutoring,
            user=current_user,
            question=request.message,
            context=f"Assistance mode: {assistance}. Teacher policy: {policy['mode']}. In hint mode give a hint only, without solving the current assessment. Invite an independent attempt. Never disclose hidden assessment answers.",
            study_plan_context=plan_context,
            content_context=source.model_dump() if source else None,
            conversation_history=[
                msg.model_dump() for msg in request.conversation_history
            ],
        )
        _recheck_assistance(db, current_user, assistance)
        response = (
            result.get("explanation") or result.get("answer") or result.get("response")
        )
        if not isinstance(response, str) or not response.strip():
            return ChatResponse(
                response="The provider returned no usable answer. Try again or ask your teacher.",
                status="invalid_response",
                source=source,
                assistance_policy=policy,
                effective_assistance=assistance,
            )
        suggestions = result.get("suggestions") or result.get("follow_up_questions")
        if not isinstance(suggestions, list) or not all(
            isinstance(item, str) for item in suggestions
        ):
            suggestions = None
        return ChatResponse(
            response=response,
            suggestions=suggestions,
            source=source,
            assistance_policy=policy,
            effective_assistance=assistance,
        )
    except HTTPException:
        raise
    except (AIResponseParseError, AIContentValidationError):
        return ChatResponse(
            response="The provider returned an invalid answer. Try again or ask your teacher.",
            status="invalid_response",
            source=source,
            assistance_policy=policy,
            effective_assistance=assistance,
        )
    except Exception:
        return ChatResponse(
            response="AI assistance is unavailable. Your lesson and notes are still available; try again or ask your teacher.",
            status="unavailable",
            source=source,
            assistance_policy=policy,
            effective_assistance=assistance,
        )
    finally:
        if ai_service is not None:
            ai_service.close()


class AnswerQuestionRequest(BaseModel):
    """Request to get AI-powered answer for a Q&A question."""

    question: str = Field(min_length=1, max_length=4000)
    assistance: Literal["hint", "explanation", "example", "check_understanding"] = (
        "explanation"
    )
    context: Optional[str] = Field(
        default=None, max_length=6000
    )  # Optional additional context


class AnswerQuestionResponse(BaseModel):
    """AI-generated answer for Q&A."""

    answer: str
    suggestions: Optional[List[str]] = None
    success: bool = True
    assistance_policy: dict = Field(
        default_factory=lambda: {
            "mode": "explanations",
            "active_assessment_ids": [],
            "scope": "active_attempt",
            "reason": None,
        }
    )
    effective_assistance: str = "explanation"


@router.post("/answer-question", response_model=AnswerQuestionResponse)
def answer_question(
    request: AnswerQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI-powered answer for a student question.

    This endpoint provides educational assistance for Q&A content.
    """
    import logging

    logger = logging.getLogger(__name__)

    policy, assistance = _permitted_assistance(db, current_user, request.assistance)
    ai_service = None
    try:
        ai_service = get_ai_service_dependency(current_user, db)

        # Build the prompt for answering the question
        system_context = """You are an educational AI assistant helping students understand concepts.
Provide clear, accurate, and educational answers. If the question is unclear, ask for clarification.
Keep answers concise but thorough enough to be helpful."""

        system_context += f"\nTeacher policy: {policy['mode']}. Assistance mode: {assistance}. In hint mode give only a hint and do not solve the assessment or reveal hidden answers."

        if request.context:
            system_context += f"\n\nAdditional context: {request.context}"

        # Use the tutoring method to get an educational response
        result = ai_service.provide_tutoring(
            user=current_user,
            question=request.question,
            context=system_context,
            study_plan_context=None,
            content_context=None,
            conversation_history=None,
        )

        _recheck_assistance(db, current_user, assistance)
        answer_text = (
            result.get("explanation") or result.get("answer") or result.get("response")
        )
        if not isinstance(answer_text, str) or not answer_text.strip():
            return AnswerQuestionResponse(
                answer="The provider returned no usable answer. Try again or ask your teacher.",
                success=False,
            )
        suggestions = result.get("suggestions", result.get("follow_up_questions", None))

        return AnswerQuestionResponse(
            answer=answer_text,
            suggestions=suggestions,
            success=True,
            assistance_policy=policy,
            effective_assistance=assistance,
        )

    except HTTPException:
        raise
    except Exception:
        logger.warning("AI answer generation unavailable")

        return AnswerQuestionResponse(
            answer=(
                "I apologize, but I couldn't generate an answer. "
                "Please check your AI configuration or try again later. "
            ),
            suggestions=["Check AI settings", "Try a simpler question"],
            success=False,
        )

    finally:
        if ai_service is not None:
            ai_service.close()
