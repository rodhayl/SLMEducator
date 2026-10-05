from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.api.dependencies import get_db
from src.core.models import User
from src.core.services.ai_service import AIService
from src.core.services.content_schema import normalize_content
from src.api.security import require_teacher_or_admin
from src.api.policies import can_manage_plan, require_allowed
from src.api.dependencies import get_ai_service_dependency

router = APIRouter(prefix="/api/generate", tags=["generation"])

# Pydantic models for requests


class StudyPlanRequest(BaseModel):
    subject: str
    grade_level: str
    objectives: List[str]
    duration_weeks: int


class ExerciseRequest(BaseModel):
    topic: str
    difficulty: str  # easy, medium, hard
    exercise_type: str  # multiple_choice, true_false, short_answer
    source_material: Optional[str] = Field(default=None, max_length=100000)
    grade_level: Optional[str] = None
    learning_objectives: Optional[List[str]] = None


class EnhancementRequest(BaseModel):
    content_id: int
    enhancement_type: str  # explanation, examples, simplification


class LessonRequest(BaseModel):
    """Request model for AI lesson generation."""

    topic: str
    grade_level: str
    learning_objectives: List[str]
    duration_minutes: int = 30
    source_material: Optional[str] = None


class TopicContentRequest(BaseModel):
    """Request model for AI topic content package generation."""

    subject: str
    topic_name: str
    grade_level: str
    learning_objectives: List[str]
    content_types: Optional[List[str]] = None  # Default: ['lesson', 'exercise']
    source_material: Optional[str] = None


class CourseOutlineRequest(BaseModel):
    """Request model for AI course outline generation."""

    subject: str
    grade_level: str
    duration_weeks: int = 4
    source_material: Optional[str] = None


class AssessmentQuestionsRequest(BaseModel):
    """Request model for AI assessment question generation."""

    topic: str
    learning_objectives: List[str]
    question_types: Optional[List[str]] = None  # Default: mixed
    num_questions: int = 5
    difficulty: str = "medium"  # easy, medium, hard
    source_material: Optional[str] = Field(default=None, max_length=100000)
    grade_level: Optional[str] = None


@router.post("/study-plan")
def generate_study_plan(
    request: StudyPlanRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """Generate a complete study plan with AI assistance."""
    try:
        plan = ai_service.generate_study_plan(
            user=current_user,
            subject=request.subject,
            grade_level=request.grade_level,
            learning_objectives=request.objectives,
            duration_weeks=request.duration_weeks,
        )
        return plan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exercise")
def generate_exercise(
    request: ExerciseRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """Generate a single exercise with AI assistance."""
    try:
        exercise = ai_service.generate_exercise(
            topic=request.topic,
            difficulty=request.difficulty,
            exercise_type=request.exercise_type,
            source_material=request.source_material,
            grade_level=request.grade_level,
            learning_objectives=request.learning_objectives,
        )
        return exercise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson")
def generate_lesson(
    request: LessonRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """
    Generate a structured lesson with AI assistance.

    Returns lesson with sections, key points, examples, vocabulary, and discussion questions.
    """
    try:
        lesson = ai_service.generate_lesson(
            topic=request.topic,
            grade_level=request.grade_level,
            learning_objectives=request.learning_objectives,
            duration_minutes=request.duration_minutes,
            source_material=request.source_material,
        )
        # Share package admission checks without changing valid legacy payloads.
        normalize_content("lesson", lesson)
        return lesson
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topic-content")
def generate_topic_content(
    request: TopicContentRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """
    Generate complete topic content package with AI assistance.

    Returns a package containing lesson, exercises, vocabulary, and metadata for a topic.
    """
    try:
        topic_content = ai_service.generate_topic_content(
            subject=request.subject,
            topic_name=request.topic_name,
            grade_level=request.grade_level,
            learning_objectives=request.learning_objectives,
            content_types=request.content_types,
            source_material=request.source_material,
        )
        return topic_content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/course-outline")
def generate_course_outline(
    request: CourseOutlineRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """
    Generate a hierarchical course outline (Units -> Lessons).
    Returns JSON structure with units and lessons for further editing/generation.
    """
    try:
        outline = ai_service.generate_course_outline(
            subject=request.subject,
            grade_level=request.grade_level,
            duration_weeks=request.duration_weeks,
            source_material=request.source_material,
        )
        return outline
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment-questions")
def generate_assessment_questions(
    request: AssessmentQuestionsRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """
    Generate assessment questions with AI assistance.

    Returns a list of questions with correct answers, options, and explanations.
    """
    try:
        questions = ai_service.generate_assessment_questions(
            topic=request.topic,
            learning_objectives=request.learning_objectives,
            question_types=request.question_types,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            source_material=request.source_material,
            grade_level=request.grade_level,
        )
        return {"questions": questions, "total": len(questions)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance")
async def enhance_content(
    request: EnhancementRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
):
    """Enhance existing content with AI (not yet connected to DB)."""
    raise HTTPException(
        status_code=501, detail="Content enhancement not yet connected to DB."
    )


# --- Unified Full Topic Package Generation ---


class FullTopicPackageRequest(BaseModel):
    """
    Request model for generating a complete topic package.
    Generates independently recoverable lesson, exercises and assessment items.
    """

    subject: str
    topic_name: str
    grade_level: str
    learning_objectives: List[str]

    # Content generation options
    include_lesson: bool = True
    include_exercises: bool = True
    include_assessment: bool = True

    # Exercise options
    num_exercises: int = Field(default=4, ge=0, le=12)
    exercise_difficulty: str = "medium"  # easy, medium, hard

    # Assessment options
    num_assessment_questions: int = Field(default=5, ge=1, le=20)
    assessment_difficulty: str = "medium"

    source_material: Optional[str] = Field(default=None, max_length=100000)
    source_document_id: Optional[str] = Field(default=None, pattern="^[a-f0-9]{64}$")

    # Auto-save options
    auto_save: bool = False
    study_plan_id: Optional[int] = None
    phase_index: int = Field(default=0, ge=0, le=100)


class GeneratedPackageResponse(BaseModel):
    """Response containing the full generated topic package."""

    success: bool
    topic_name: str
    lesson: Optional[Dict[str, Any]] = None
    exercises: Optional[List[Dict[str, Any]]] = None
    assessment: Optional[Dict[str, Any]] = None
    saved_content_ids: Optional[List[int]] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    job_key: Optional[str] = None


@router.post("/full-topic-package", response_model=GeneratedPackageResponse)
def generate_full_topic_package(
    request: FullTopicPackageRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
    db: Session = Depends(get_db),
):
    """Persist each generated item independently; retries reuse completed item IDs."""
    from src.core.models import StudyPlan
    from src.core.services.generation_workflow import generate_package

    plan = None
    if request.auto_save:
        if not request.study_plan_id:
            raise HTTPException(
                status_code=422,
                detail="Choose a course draft before saving a generation package",
            )
        plan = db.get(StudyPlan, request.study_plan_id)
        require_allowed(can_manage_plan(db, current_user, plan))
    try:
        return generate_package(db, current_user, plan, ai_service, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Generation could not be saved. Previously confirmed items remain available; retry safely.",
        )
    finally:
        ai_service.close()


@router.get("/courses/{plan_id}/jobs")
def list_course_generation_jobs(
    plan_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Reload durable generation state after refresh or an interrupted request."""
    from src.core.models import StudyPlan
    from src.core.services.course_workflow import metadata

    plan = db.get(StudyPlan, plan_id)
    require_allowed(can_manage_plan(db, current_user, plan))
    return {"jobs": metadata(plan).get("generation_jobs", {})}


@router.post("/courses/{plan_id}/jobs/{job_key}/cancel")
def cancel_course_generation(
    plan_id: int,
    job_key: str,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Stop at the next item boundary; an in-flight provider call may finish."""
    from src.core.models import StudyPlan
    from src.core.services.course_workflow import metadata

    plan = db.get(StudyPlan, plan_id)
    require_allowed(can_manage_plan(db, current_user, plan))
    data = metadata(plan)
    jobs = data.get("generation_jobs", {})
    if job_key not in jobs:
        raise HTTPException(status_code=404, detail="Generation request not found")
    jobs[job_key]["cancel_requested"] = True
    data["generation_jobs"] = jobs
    plan.set_encrypted_metadata(data)
    db.commit()
    return {"status": "cancellation_requested", "in_flight_call_may_finish": True}
