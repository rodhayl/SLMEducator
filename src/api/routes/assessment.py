from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from src.api.dependencies import get_db, get_ai_service_dependency
from src.api.security import get_current_user, require_teacher_or_admin
from src.core.models import (
    User,
    Assessment,
    Question as Question,
    Submission as Submission,
    Rubric,
    RubricCriterion,
    QuestionType,
    SubmissionStatus,
    GradingMode,
    QuestionResponse,
)
from src.core.roles import is_admin, is_teacher_or_admin

router = APIRouter(prefix="/api/assessments", tags=["assessments"])

# --- Pydantic Models ---


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str  # Enum value
    points: int = 10
    correct_answer: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class RubricCriterionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_points: int = 10


class RubricCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: List[RubricCriterionCreate] = []


class AssessmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    study_plan_id: Optional[int] = None
    topic_id: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    passing_score: int = 70
    grading_mode: Optional[str] = "ai_assisted"  # ai_automatic, ai_assisted, manual
    questions: List[QuestionCreate] = []
    rubric: Optional[RubricCreate] = None


class AssessmentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_published: bool
    created_at: datetime
    question_count: int

    model_config = ConfigDict(from_attributes=True)


class QuestionResponseModel(BaseModel):
    id: int
    question_text: str
    question_type: str
    points: int
    options: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class FullAssessmentResponse(AssessmentResponse):
    questions: List[QuestionResponseModel]


class AnswerSubmission(BaseModel):
    question_id: int
    response_text: str


class SubmissionCreate(BaseModel):
    answers: List[AnswerSubmission]


class AnswerDetail(BaseModel):
    """Answer detail with question info for grading view"""

    response_id: int  # Added for per-question grading
    question_id: int
    question_text: str
    question_type: str
    given_answer: Optional[str]
    correct_answer: Optional[str]
    is_correct: Optional[bool]
    points: Optional[int]
    max_points: int
    # AI grading fields
    ai_suggested_score: Optional[int] = None
    ai_suggested_feedback: Optional[str] = None
    ai_confidence: Optional[float] = None
    teacher_override: bool = False


class SubmissionListItem(BaseModel):
    """Submission item for list view"""

    id: int
    assessment_id: int
    assessment_title: str
    student_id: int
    student_name: str
    status: str
    score: Optional[int]
    total_points: Optional[int]
    submitted_at: Optional[datetime]
    graded_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SubmissionDetail(BaseModel):
    """Full submission detail for grading"""

    id: int
    assessment_id: int
    assessment_title: str
    student_id: int
    student_name: str
    status: str
    score: Optional[int]
    total_points: Optional[int]
    feedback: Optional[str]
    submitted_at: Optional[datetime]
    graded_at: Optional[datetime]
    answers: List[AnswerDetail]


class GradeSubmit(BaseModel):
    """Grade submission input"""

    score: float
    feedback: Optional[str] = None


# --- Routes ---


@router.post("/", response_model=AssessmentResponse)
async def create_assessment(
    assessment_data: AssessmentCreate,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new assessment with questions"""

    # Parse grading mode
    grading_mode_value = GradingMode.AI_ASSISTED
    if assessment_data.grading_mode:
        try:
            grading_mode_value = GradingMode(assessment_data.grading_mode)
        except ValueError:
            pass  # Use default

    # Create Assessment
    new_assessment = Assessment(
        title=assessment_data.title,
        description=assessment_data.description,
        study_plan_id=assessment_data.study_plan_id,
        topic_id=assessment_data.topic_id,
        time_limit_minutes=assessment_data.time_limit_minutes,
        passing_score=assessment_data.passing_score,
        grading_mode=grading_mode_value,
        created_by_id=current_user.id,
        is_published=True,  # Auto publish for now
    )
    db.add(new_assessment)
    db.flush()  # Get ID

    # Add Questions
    total_points = 0
    for idx, q_data in enumerate(assessment_data.questions):
        question = Question(
            assessment_id=new_assessment.id,
            question_text=q_data.question_text,
            question_type=QuestionType(q_data.question_type),
            points=q_data.points,
            order_index=idx,
            options=q_data.options,
        )
        if q_data.correct_answer:
            question.set_encrypted_correct_answer(q_data.correct_answer)

        db.add(question)
        total_points += q_data.points

    # Add Rubric if present
    if assessment_data.rubric:
        rubic_points = sum(c.max_points for c in assessment_data.rubric.criteria)
        new_rubric = Rubric(
            name=assessment_data.rubric.name,
            description=assessment_data.rubric.description,
            total_points=rubic_points,
            created_by_id=current_user.id,
            assessment_id=new_assessment.id,
        )
        db.add(new_rubric)
        db.flush()

        for idx, crit in enumerate(assessment_data.rubric.criteria):
            db.add(
                RubricCriterion(
                    rubric_id=new_rubric.id,
                    name=crit.name,
                    description=crit.description,
                    max_points=crit.max_points,
                    order_index=idx,
                )
            )

    new_assessment.total_points = total_points
    db.commit()
    db.refresh(new_assessment)

    # Manually map for response since question_count is computed
    return AssessmentResponse(
        id=new_assessment.id,
        title=new_assessment.title,
        description=new_assessment.description,
        is_published=new_assessment.is_published,
        created_at=new_assessment.created_at,
        question_count=len(assessment_data.questions),
    )


@router.get("/", response_model=List[AssessmentResponse])
async def list_assessments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List available assessments"""
    # Teacher sees created, Student sees assigned/public
    # Simplified: Everyone sees everything public for now
    assessments = db.query(Assessment).filter(Assessment.is_published == True).all()

    result = []
    for a in assessments:
        result.append(
            AssessmentResponse(
                id=a.id,
                title=a.title,
                description=a.description,
                is_published=a.is_published,
                created_at=a.created_at,
                question_count=len(a.questions),
            )
        )
    return result


class AssessmentUpdate(BaseModel):
    """Update model for assessments - all fields optional"""

    title: Optional[str] = None
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    passing_score: Optional[int] = None
    grading_mode: Optional[str] = None
    is_published: Optional[bool] = None
    questions: Optional[List[QuestionCreate]] = None


@router.put("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: int,
    update_data: AssessmentUpdate,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Update an existing assessment"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check ownership for non-admin
    if (not is_admin(current_user)) and assessment.created_by_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Can only edit your own assessments"
        )

    # Update basic fields
    if update_data.title is not None:
        assessment.title = update_data.title
    if update_data.description is not None:
        assessment.description = update_data.description
    if update_data.time_limit_minutes is not None:
        assessment.time_limit_minutes = update_data.time_limit_minutes
    if update_data.passing_score is not None:
        assessment.passing_score = update_data.passing_score
    if update_data.is_published is not None:
        assessment.is_published = update_data.is_published
    if update_data.grading_mode is not None:
        try:
            assessment.grading_mode = GradingMode(update_data.grading_mode)
        except ValueError:
            pass

    # Update questions if provided (replace all)
    if update_data.questions is not None:
        # Delete existing questions
        db.query(Question).filter(Question.assessment_id == assessment_id).delete()

        # Add new questions
        total_points = 0
        for idx, q_data in enumerate(update_data.questions):
            question = Question(
                assessment_id=assessment.id,
                question_text=q_data.question_text,
                question_type=QuestionType(q_data.question_type),
                points=q_data.points,
                order_index=idx,
                options=q_data.options,
            )
            if q_data.correct_answer:
                question.set_encrypted_correct_answer(q_data.correct_answer)
            db.add(question)
            total_points += q_data.points
        assessment.total_points = total_points

    db.commit()
    db.refresh(assessment)

    return AssessmentResponse(
        id=assessment.id,
        title=assessment.title,
        description=assessment.description,
        is_published=assessment.is_published,
        created_at=assessment.created_at,
        question_count=len(assessment.questions),
    )


# --- Grading Endpoints (for grading.js) ---
# NOTE: These routes MUST be defined BEFORE /{assessment_id} to avoid route conflicts


@router.get("/submissions", response_model=List[SubmissionListItem])
async def list_submissions(
    status: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List submissions for grading (teachers see all, students see theirs)"""
    query = db.query(Submission)

    # Role check
    teacher_view = is_teacher_or_admin(current_user)

    if not teacher_view:
        query = query.filter(Submission.student_id == current_user.id)

    # Status filter
    if status:
        status_enums = []
        for status_value in status:
            try:
                status_enums.append(SubmissionStatus(status_value))
            except ValueError:
                continue
        if status_enums:
            query = query.filter(Submission.status.in_(status_enums))

    submissions = query.order_by(Submission.submitted_at.desc()).all()

    result = []
    for sub in submissions:
        # Get assessment title
        assessment = (
            db.query(Assessment).filter(Assessment.id == sub.assessment_id).first()
        )
        assessment_title = (
            assessment.title if assessment else f"Assessment #{sub.assessment_id}"
        )

        # Get student name
        student = db.query(User).filter(User.id == sub.student_id).first()
        student_name = student.full_name if student else f"Student #{sub.student_id}"

        result.append(
            SubmissionListItem(
                id=sub.id,
                assessment_id=sub.assessment_id,
                assessment_title=assessment_title,
                student_id=sub.student_id,
                student_name=student_name,
                status=(
                    sub.status.value
                    if hasattr(sub.status, "value")
                    else str(sub.status)
                ),
                score=sub.score,
                total_points=sub.total_points,
                submitted_at=sub.submitted_at,
                graded_at=sub.graded_at,
            )
        )

    return result


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
async def get_submission_details(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full submission details for grading"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Permission check: teacher/admin or own submission
    teacher_view = is_teacher_or_admin(current_user)

    if not teacher_view and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get assessment and student info
    assessment = (
        db.query(Assessment).filter(Assessment.id == submission.assessment_id).first()
    )
    student = db.query(User).filter(User.id == submission.student_id).first()

    # Build answers list
    answers = []
    for resp in submission.responses:
        question = resp.question
        answers.append(
            AnswerDetail(
                response_id=resp.id,
                question_id=question.id,
                question_text=question.question_text,
                question_type=(
                    question.question_type.value
                    if hasattr(question.question_type, "value")
                    else str(question.question_type)
                ),
                given_answer=resp.get_decrypted_response(),
                correct_answer=(
                    question.get_decrypted_correct_answer() if teacher_view else None
                ),
                is_correct=resp.is_correct,
                points=resp.score,
                max_points=question.points,
                ai_suggested_score=resp.ai_suggested_score,
                ai_suggested_feedback=resp.ai_suggested_feedback,
                ai_confidence=resp.ai_confidence,
                teacher_override=(
                    resp.teacher_override if resp.teacher_override else False
                ),
            )
        )

    return SubmissionDetail(
        id=submission.id,
        assessment_id=submission.assessment_id,
        assessment_title=assessment.title if assessment else "",
        student_id=submission.student_id,
        student_name=student.full_name if student else "",
        status=(
            submission.status.value
            if hasattr(submission.status, "value")
            else str(submission.status)
        ),
        score=submission.score,
        total_points=submission.total_points,
        feedback=submission.feedback,
        submitted_at=submission.submitted_at,
        graded_at=submission.graded_at,
        answers=answers,
    )


@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: int,
    grade_data: GradeSubmit,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Submit a grade for a submission (teacher only)"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Update grade
    submission.score = int(grade_data.score)
    submission.feedback = grade_data.feedback
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now()
    submission.teacher_approved = True

    db.commit()

    return {"status": "ok", "message": "Grade saved successfully"}


@router.post("/submissions/{submission_id}/accept-ai")
async def accept_ai_grades(
    submission_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Accept all AI-suggested grades for a submission (teacher only)"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.status != SubmissionStatus.AI_GRADED:
        raise HTTPException(
            status_code=400, detail="Submission is not pending AI review"
        )

    # Accept all AI suggestions
    total_score = 0
    for response in submission.responses:
        if response.ai_suggested_score is not None:
            response.score = response.ai_suggested_score
            response.feedback = response.ai_suggested_feedback
            response.is_correct = response.score > 0
            response.graded_at = datetime.now()
        if response.score is not None:
            total_score += response.score

    submission.score = total_score
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now()
    submission.teacher_approved = True

    db.commit()

    return {"status": "ok", "message": "AI grades accepted", "final_score": total_score}


class QuestionGradeInput(BaseModel):
    """Input for grading a single question"""

    score: int
    feedback: Optional[str] = None


@router.post("/submissions/{submission_id}/responses/{response_id}/grade")
async def grade_single_response(
    submission_id: int,
    response_id: int,
    grade_data: QuestionGradeInput,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Grade a single question response (teacher only)"""
    response = (
        db.query(QuestionResponse)
        .filter(
            QuestionResponse.id == response_id,
            QuestionResponse.submission_id == submission_id,
        )
        .first()
    )

    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    # Mark as teacher override if AI had suggested something different
    if (
        response.ai_suggested_score is not None
        and response.ai_suggested_score != grade_data.score
    ):
        response.teacher_override = True

    response.score = grade_data.score
    response.feedback = grade_data.feedback
    response.is_correct = grade_data.score > 0
    response.graded_at = datetime.now()

    # Recalculate submission total
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if submission:
        total_score = sum(r.score or 0 for r in submission.responses)
        submission.score = total_score

        # Check if all questions are now graded
        all_graded = all(r.score is not None for r in submission.responses)
        if all_graded and submission.status in (
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.AI_GRADED,
        ):
            submission.status = SubmissionStatus.GRADED
            submission.graded_at = datetime.now()
            submission.teacher_approved = True

    db.commit()

    return {"status": "ok", "message": "Question graded", "score": grade_data.score}


# --- Assessment Detail Routes (parameterized, must come after static routes) ---


@router.get("/{assessment_id}", response_model=FullAssessmentResponse)
async def get_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full assessment details for taking it"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    questions = []
    for q in assessment.questions:
        questions.append(
            QuestionResponseModel(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                points=q.points,
                options=q.options,
            )
        )

    return FullAssessmentResponse(
        id=assessment.id,
        title=assessment.title,
        description=assessment.description,
        is_published=assessment.is_published,
        created_at=assessment.created_at,
        question_count=len(questions),
        questions=questions,
    )


@router.post("/{assessment_id}/submit")
async def submit_assessment(
    assessment_id: int,
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit an assessment attempt with intelligent grading.

    Grading behavior depends on assessment's grading_mode:
    - AI_AUTOMATIC: AI grades all questions, returns final grade immediately
    - AI_ASSISTED: AI suggests grades, teacher reviews (status=AI_GRADED)
    - MANUAL: Only objective questions auto-graded, subjective await teacher

    Objective questions (multiple_choice, true_false) are always auto-graded.
    """
    import logging

    logger = logging.getLogger(__name__)

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Get grading mode (default to AI_ASSISTED)
    grading_mode = (
        assessment.grading_mode
        if hasattr(assessment, "grading_mode") and assessment.grading_mode
        else GradingMode.AI_ASSISTED
    )

    # Objective question types that can always be auto-graded
    OBJECTIVE_TYPES = {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}

    # Create Submission
    submission = Submission(
        assessment_id=assessment_id,
        student_id=current_user.id,
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(),
        total_points=assessment.total_points,
    )
    db.add(submission)
    db.flush()

    # Track scores and pending review
    total_score = 0
    ai_graded_count = 0
    needs_review = False

    # Get AI service if needed for subjective questions
    ai_service = None
    use_ai = grading_mode in (GradingMode.AI_AUTOMATIC, GradingMode.AI_ASSISTED)

    try:
        if use_ai:
            try:
                ai_service = get_ai_service_dependency(current_user, db)
            except Exception as e:
                logger.warning(f"AI service unavailable for grading: {e}")
                ai_service = None

        # Process each answer
        for ans in submission_data.answers:
            question = db.query(Question).filter(Question.id == ans.question_id).first()
            if not question:
                continue

            response = QuestionResponse(
                submission_id=submission.id,
                question_id=ans.question_id,
            )
            response.set_encrypted_response(ans.response_text)

            correct_answer = question.get_decrypted_correct_answer()
            is_objective = question.question_type in OBJECTIVE_TYPES

            if is_objective:
                # Always auto-grade objective questions
                if (
                    correct_answer
                    and correct_answer.lower().strip()
                    == ans.response_text.lower().strip()
                ):
                    response.is_correct = True
                    response.score = question.points
                    total_score += question.points
                else:
                    response.is_correct = False
                    response.score = 0
            else:
                # Subjective question - handle based on grading mode
                if grading_mode == GradingMode.MANUAL:
                    # Manual mode: don't grade subjective questions
                    response.score = None
                    response.is_correct = None
                    needs_review = True
                elif ai_service:
                    # AI grading for subjective questions
                    try:
                        ai_result = ai_service.grade_answer(
                            question=question.question_text,
                            answer=ans.response_text,
                            question_type=question.question_type.value,
                            correct_answer=correct_answer,
                            max_points=question.points,
                        )

                        # Store AI suggestions
                        response.ai_suggested_score = ai_result.get("points_earned", 0)
                        response.ai_suggested_feedback = ai_result.get("feedback", "")
                        response.ai_confidence = (
                            ai_result.get("percentage", 0) / 100.0
                        )  # Normalize to 0-1

                        if grading_mode == GradingMode.AI_AUTOMATIC:
                            # Auto-accept AI grades
                            response.score = response.ai_suggested_score
                            response.feedback = response.ai_suggested_feedback
                            response.is_correct = response.score > 0
                            total_score += response.score
                        else:
                            # AI_ASSISTED: Store suggestions, await teacher review
                            response.score = None  # Not finalized
                            needs_review = True

                        ai_graded_count += 1
                    except Exception as e:
                        logger.error(
                            f"AI grading failed for question {question.id}: {e}"
                        )
                        response.score = None
                        needs_review = True
                else:
                    # No AI available, mark for manual review
                    response.score = None
                    response.is_correct = None
                    needs_review = True

            db.add(response)
    finally:
        if ai_service:
            try:
                ai_service.close()
            except Exception:
                pass

    # Set final status and score
    submission.score = total_score

    if grading_mode == GradingMode.AI_AUTOMATIC and not needs_review:
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.now()
    elif grading_mode == GradingMode.AI_ASSISTED and ai_graded_count > 0:
        submission.status = SubmissionStatus.AI_GRADED  # Pending teacher review
        submission.ai_draft_score = total_score
    elif grading_mode == GradingMode.MANUAL or needs_review:
        submission.status = SubmissionStatus.SUBMITTED  # Awaiting manual grading
    else:
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.now()

    db.commit()

    # Award XP and check badges (non-critical)
    try:
        from src.core.services.progress_tracking_service import (
            get_progress_tracking_service,
        )

        pts = get_progress_tracking_service()

        # Award XP based on score (10 XP per point, capped at 500)
        xp_earned = min(total_score * 10, 500) if total_score > 0 else 25
        pts.award_xp(current_user.id, xp_earned)

        # Update streak
        pts.update_streak(current_user.id)

        # Check for badges
        pts.check_and_award_badges(current_user.id)
    except Exception:
        pass

    return {
        "id": submission.id,
        "score": total_score,
        "status": submission.status.value,
        "grading_mode": grading_mode.value,
        "ai_graded_questions": ai_graded_count,
        "needs_review": needs_review,
    }


# --- Assessment Stats Endpoint ---
@router.get("/{assessment_id}/stats")
async def get_assessment_stats(
    assessment_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """
    Get statistics for an assessment (teacher/admin only).

    Returns:
        total_submissions, average_score, highest_score, lowest_score, pass_rate
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Get all graded submissions for this assessment
    submissions = (
        db.query(Submission)
        .filter(
            Submission.assessment_id == assessment_id,
            Submission.status == SubmissionStatus.GRADED,
        )
        .all()
    )

    if not submissions:
        return {
            "assessment_id": assessment_id,
            "total_submissions": 0,
            "average_score": None,
            "highest_score": None,
            "lowest_score": None,
            "pass_rate": None,
        }

    # Calculate statistics
    total_points = assessment.total_points or 100
    passing_score = assessment.passing_score or 70

    scores = []
    passed_count = 0

    for sub in submissions:
        if sub.score is not None:
            percentage = (sub.score / total_points) * 100 if total_points > 0 else 0
            scores.append(percentage)
            if percentage >= passing_score:
                passed_count += 1

    if scores:
        return {
            "assessment_id": assessment_id,
            "total_submissions": len(submissions),
            "average_score": sum(scores) / len(scores),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "pass_rate": (passed_count / len(scores)) * 100,
        }

    return {
        "assessment_id": assessment_id,
        "total_submissions": len(submissions),
        "average_score": None,
        "highest_score": None,
        "lowest_score": None,
        "pass_rate": None,
    }


# --- Delete Assessment Endpoint ---
@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """
    Delete an assessment (teacher/admin only).

    Only the creator or an admin can delete an assessment.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check ownership (creator or admin)
    if assessment.creator_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=403, detail="You can only delete assessments you created"
        )

    # Delete associated questions first
    db.query(Question).filter(Question.assessment_id == assessment_id).delete()

    # Delete the assessment
    db.delete(assessment)
    db.commit()

    return {"success": True, "message": "Assessment deleted successfully"}
