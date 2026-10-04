from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.api.security import get_current_user
from src.api.dependencies import get_db, get_ai_service_dependency
from src.api.policies import require_content, require_plan
from src.core.models import User
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


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Use authorized, bounded source text; AI responses remain unverified suggestions."""
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
            context=f"Assistance mode: {request.assistance}. Start with a hint and invite an independent attempt. Do not disclose hidden assessment answers.",
            study_plan_context=plan_context,
            content_context=source.model_dump() if source else None,
            conversation_history=[
                msg.model_dump() for msg in request.conversation_history
            ],
        )
        response = (
            result.get("explanation") or result.get("answer") or result.get("response")
        )
        if not isinstance(response, str) or not response.strip():
            return ChatResponse(
                response="The provider returned no usable answer. Try again or ask your teacher.",
                status="invalid_response",
                source=source,
            )
        suggestions = result.get("suggestions") or result.get("follow_up_questions")
        if not isinstance(suggestions, list) or not all(
            isinstance(item, str) for item in suggestions
        ):
            suggestions = None
        return ChatResponse(response=response, suggestions=suggestions, source=source)
    except HTTPException:
        raise
    except Exception:
        return ChatResponse(
            response="AI assistance is unavailable. Your lesson and notes are still available; try again or ask your teacher.",
            status="unavailable",
            source=source,
        )
    finally:
        if ai_service is not None:
            ai_service.close()


class AnswerQuestionRequest(BaseModel):
    """Request to get AI-powered answer for a Q&A question."""

    question: str = Field(min_length=1, max_length=4000)
    context: Optional[str] = Field(
        default=None, max_length=6000
    )  # Optional additional context


class AnswerQuestionResponse(BaseModel):
    """AI-generated answer for Q&A."""

    answer: str
    suggestions: Optional[List[str]] = None
    success: bool = True


@router.post("/answer-question", response_model=AnswerQuestionResponse)
async def answer_question(
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

    try:
        ai_service = get_ai_service_dependency(current_user, db)

        # Build the prompt for answering the question
        system_context = """You are an educational AI assistant helping students understand concepts.
Provide clear, accurate, and educational answers. If the question is unclear, ask for clarification.
Keep answers concise but thorough enough to be helpful."""

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

        # Extract the answer
        answer_text = result.get(
            "explanation",
            result.get(
                "response",
                "I couldn't generate an answer. Please try rephrasing your question.",
            ),
        )
        suggestions = result.get("suggestions", result.get("follow_up_questions", None))

        return AnswerQuestionResponse(
            answer=answer_text, suggestions=suggestions, success=True
        )

    except Exception as e:
        logger.error(f"AI Answer Question error: {e}")

        return AnswerQuestionResponse(
            answer=(
                "I apologize, but I couldn't generate an answer. "
                "Please check your AI configuration or try again later. "
            ),
            suggestions=["Check AI settings", "Try a simpler question"],
            success=False,
        )
