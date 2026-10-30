from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.api.dependencies import get_db
from src.core.models import User
from src.core.services.ai_service import AIService
from src.api.security import require_teacher_or_admin
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
    Creates lesson, exercises, and assessment in one AI call.
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
    num_exercises: int = 4
    exercise_difficulty: str = "medium"  # easy, medium, hard

    # Assessment options
    num_assessment_questions: int = 5
    assessment_difficulty: str = "medium"

    # Auto-save options
    auto_save: bool = False
    study_plan_id: Optional[int] = None
    phase_index: int = 0


class GeneratedPackageResponse(BaseModel):
    """Response containing the full generated topic package."""

    success: bool
    topic_name: str
    lesson: Optional[Dict[str, Any]] = None
    exercises: Optional[List[Dict[str, Any]]] = None
    assessment: Optional[Dict[str, Any]] = None
    saved_content_ids: Optional[List[int]] = None


@router.post("/full-topic-package", response_model=GeneratedPackageResponse)
def generate_full_topic_package(
    request: FullTopicPackageRequest,
    current_user: User = Depends(require_teacher_or_admin),
    ai_service: AIService = Depends(get_ai_service_dependency),
    db: Session = Depends(get_db),
):
    """
    Generate a complete topic package with AI assistance.

    This unified endpoint generates:
    - A structured lesson (if include_lesson=True)
    - Multiple exercises (if include_exercises=True)
    - An assessment with questions (if include_assessment=True)

    Optionally auto-saves to the database and links to a study plan.

    Returns all generated content for review before final save.
    """
    import logging
    from src.core.models import Content, ContentType, StudyPlan, StudyPlanContent
    from datetime import datetime

    logger = logging.getLogger(__name__)

    result = {
        "success": True,
        "topic_name": request.topic_name,
        "lesson": None,
        "exercises": None,
        "assessment": None,
        "saved_content_ids": None,
    }

    try:
        # 1. Generate Lesson
        if request.include_lesson:
            try:
                lesson = ai_service.generate_lesson(
                    topic=request.topic_name,
                    grade_level=request.grade_level,
                    learning_objectives=request.learning_objectives,
                    duration_minutes=30,
                    source_material=None,
                )
                result["lesson"] = lesson
            except Exception as e:
                logger.warning(f"Lesson generation failed: {e}")
                result["lesson"] = {
                    "error": str(e),
                    "title": f"Lesson: {request.topic_name}",
                    "content": "AI generation failed. Please try again or write manually.",
                }

        # 2. Generate Exercises
        if request.include_exercises:
            exercises = []
            exercise_types = ["multiple_choice", "true_false", "short_answer"]

            for i in range(request.num_exercises):
                try:
                    exercise_type = exercise_types[i % len(exercise_types)]
                    exercise = ai_service.generate_exercise(
                        topic=request.topic_name,
                        difficulty=request.exercise_difficulty,
                        exercise_type=exercise_type,
                    )
                    exercises.append(exercise)
                except Exception as e:
                    logger.warning(f"Exercise {i+1} generation failed: {e}")
                    exercises.append(
                        {
                            "error": str(e),
                            "title": f"Exercise {i+1}: {request.topic_name}",
                            "type": exercise_type,
                        }
                    )

            result["exercises"] = exercises

        # 3. Generate Assessment
        if request.include_assessment:
            try:
                questions = ai_service.generate_assessment_questions(
                    topic=request.topic_name,
                    learning_objectives=request.learning_objectives,
                    question_types=None,  # Mixed types
                    num_questions=request.num_assessment_questions,
                    difficulty=request.assessment_difficulty,
                )
                result["assessment"] = {
                    "title": f"Assessment: {request.topic_name}",
                    "topic": request.topic_name,
                    "questions": questions,
                    "total_questions": len(questions),
                    "passing_score": 70,
                }
            except Exception as e:
                logger.warning(f"Assessment generation failed: {e}")
                result["assessment"] = {
                    "error": str(e),
                    "title": f"Assessment: {request.topic_name}",
                    "questions": [],
                }

        # 4. Auto-save if requested (using injected db session)
        if request.auto_save:
            try:
                saved_ids = []
                order_idx = 0

                # Verify study plan if provided
                if request.study_plan_id:
                    plan = (
                        db.query(StudyPlan)
                        .filter(StudyPlan.id == request.study_plan_id)
                        .first()
                    )
                    if not plan or plan.creator_id != current_user.id:
                        request.study_plan_id = None  # Reset if invalid
                    else:
                        order_idx = (
                            db.query(StudyPlanContent)
                            .filter(
                                StudyPlanContent.study_plan_id == request.study_plan_id,
                                StudyPlanContent.phase_index == request.phase_index,
                            )
                            .count()
                        )

                # Save lesson
                if result["lesson"] and "error" not in result["lesson"]:
                    lesson_content = Content(
                        title=result["lesson"].get(
                            "title", f"Lesson: {request.topic_name}"
                        ),
                        content_type=ContentType.LESSON,
                        difficulty=2,
                        creator_id=current_user.id,
                        study_plan_id=request.study_plan_id,
                        created_at=datetime.now(),
                    )
                    lesson_content.set_encrypted_content_data(result["lesson"])
                    db.add(lesson_content)
                    db.flush()
                    saved_ids.append(lesson_content.id)

                    if request.study_plan_id:
                        db.add(
                            StudyPlanContent(
                                study_plan_id=request.study_plan_id,
                                content_id=lesson_content.id,
                                phase_index=request.phase_index,
                                order_index=order_idx,
                            )
                        )
                        order_idx += 1

                # Save exercises
                if result["exercises"]:
                    for i, ex in enumerate(result["exercises"]):
                        if "error" not in ex:
                            ex_content = Content(
                                title=ex.get(
                                    "title", f"Exercise {i+1}: {request.topic_name}"
                                ),
                                content_type=ContentType.EXERCISE,
                                difficulty={"easy": 1, "medium": 2, "hard": 3}.get(
                                    request.exercise_difficulty, 2
                                ),
                                creator_id=current_user.id,
                                study_plan_id=request.study_plan_id,
                                created_at=datetime.now(),
                            )
                            ex_content.set_encrypted_content_data(ex)
                            db.add(ex_content)
                            db.flush()
                            saved_ids.append(ex_content.id)

                            if request.study_plan_id:
                                db.add(
                                    StudyPlanContent(
                                        study_plan_id=request.study_plan_id,
                                        content_id=ex_content.id,
                                        phase_index=request.phase_index,
                                        order_index=order_idx,
                                    )
                                )
                                order_idx += 1

                # Save assessment (NEW - was missing before)
                if result["assessment"] and "error" not in result["assessment"]:
                    assessment_content = Content(
                        title=result["assessment"].get(
                            "title", f"Assessment: {request.topic_name}"
                        ),
                        content_type=ContentType.ASSESSMENT,
                        difficulty={"easy": 1, "medium": 2, "hard": 3}.get(
                            request.assessment_difficulty, 2
                        ),
                        creator_id=current_user.id,
                        study_plan_id=request.study_plan_id,
                        created_at=datetime.now(),
                    )
                    assessment_content.set_encrypted_content_data(result["assessment"])
                    db.add(assessment_content)
                    db.flush()
                    saved_ids.append(assessment_content.id)

                    if request.study_plan_id:
                        db.add(
                            StudyPlanContent(
                                study_plan_id=request.study_plan_id,
                                content_id=assessment_content.id,
                                phase_index=request.phase_index,
                                order_index=order_idx,
                            )
                        )

                db.commit()
                result["saved_content_ids"] = saved_ids

            except Exception as e:
                db.rollback()
                logger.error(f"Auto-save failed: {e}")

        return GeneratedPackageResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full topic package generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
