from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from src.api.security import get_current_user
from src.api.dependencies import get_db, get_ai_service_dependency
from src.core.models import User, Content, StudyPlan

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    message: str
    context_id: Optional[int] = None  # Legacy field
    study_plan_id: Optional[int] = None  # Selected study plan for context
    content_id: Optional[int] = (
        None  # Selected content item (lesson/exercise/assessment)
    )
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Chat with AI Tutor using real AI service.

    Supports conversation history and content context for context-aware responses.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        ai_service = get_ai_service_dependency(current_user, db)

        # Convert conversation history to expected format
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Build content context from selected items
        content_context = None
        study_plan_context = None

        # Fetch content context if content_id provided
        if request.content_id:
            content = db.query(Content).filter(Content.id == request.content_id).first()
            if content:
                content_data = content.decrypted_content_data or {}
                content_context = {
                    "id": content.id,
                    "title": content.title,
                    "type": (
                        content.content_type.value
                        if hasattr(content.content_type, "value")
                        else str(content.content_type)
                    ),
                    "summary": _extract_content_summary(content_data),
                }
                logger.info(f"AI Tutor using content context: {content.title}")

        # Fetch study plan context if study_plan_id provided
        if request.study_plan_id:
            plan = (
                db.query(StudyPlan)
                .filter(StudyPlan.id == request.study_plan_id)
                .first()
            )
            if plan:
                study_plan_context = {
                    "id": plan.id,
                    "title": plan.title,
                    "description": plan.description[:500] if plan.description else "",
                }
                logger.info(f"AI Tutor using study plan context: {plan.title}")

        # Get tutoring response with context
        result = ai_service.provide_tutoring(
            user=current_user,
            question=request.message,
            context=None,
            study_plan_context=study_plan_context,
            content_context=content_context,
            conversation_history=history,
        )

        # Extract response from result
        response_text = result.get(
            "explanation", result.get("response", "I'm here to help!")
        )

        # Extract any follow-up suggestions if available
        suggestions = result.get("suggestions", result.get("follow_up_questions", None))

        return ChatResponse(response=response_text, suggestions=suggestions)

    except Exception as e:
        logger.error(f"AI Chat error: {e}")

        return ChatResponse(
            response=(
                "I apologize, but I encountered an issue processing your request. "
                "Please try again or check your AI configuration in Settings. "
                f"Error: {str(e)}"
            ),
            suggestions=["Check AI settings", "Try a simpler question"],
        )


def _extract_content_summary(content_data: Dict) -> str:
    """Extract a readable summary from content data for AI context."""
    if not content_data:
        return ""

    # Direct text fields
    if content_data.get("content"):
        return content_data["content"][:1000]
    if content_data.get("text"):
        return content_data["text"][:1000]
    if content_data.get("body"):
        return content_data["body"][:1000]

    # AI-generated format with sections
    if content_data.get("sections"):
        summary_parts = []
        for section in content_data["sections"][:3]:  # First 3 sections
            if section.get("title"):
                summary_parts.append(
                    f"**{section['title']}**: {section.get('content', '')[:200]}"
                )
        if content_data.get("summary"):
            summary_parts.append(f"Summary: {content_data['summary']}")
        return "\n".join(summary_parts)[:1000]

    return str(content_data)[:500]


class AnswerQuestionRequest(BaseModel):
    """Request to get AI-powered answer for a Q&A question."""

    question: str
    context: Optional[str] = None  # Optional additional context


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
                f"Error: {str(e)}"
            ),
            suggestions=["Check AI settings", "Try a simpler question"],
            success=False,
        )
