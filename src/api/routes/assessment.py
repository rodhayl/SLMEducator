from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timedelta

from src.core.services.assessed_review import record_assessed_mastery
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
from src.core.roles import is_teacher_or_admin, is_student
from src.api.policies import (
    can_access_submission,
    can_manage_assessment,
    can_manage_plan,
    can_view_assessment,
    can_reuse_content,
    require_allowed,
)
from src.core.models import StudyPlan, Content
from src.api.routes.gamification import award_activity_xp

router = APIRouter(prefix="/api/assessments", tags=["assessments"])

# --- Pydantic Models ---


class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionType
    points: int = Field(default=10, gt=0, le=10000)
    correct_answer: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class RubricCriterionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_points: int = Field(default=10, gt=0, le=10000)


class RubricCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: List[RubricCriterionCreate] = []


class AssessmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    study_plan_id: Optional[int] = None
    topic_id: Optional[int] = None
    time_limit_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    max_attempts: int = Field(default=1, ge=1, le=100)
    passing_score: int = Field(default=70, ge=0, le=100)
    grading_mode: GradingMode = GradingMode.AI_ASSISTED
    is_published: bool = False
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
    correct_answer: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FullAssessmentResponse(AssessmentResponse):
    questions: List[QuestionResponseModel]
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 1
    grading_mode: str = "ai_assisted"
    total_points: int = 0
    passing_score: int = 70
    rubric: Optional[RubricCreate] = None


class AnswerSubmission(BaseModel):
    question_id: int
    response_text: str


class SubmissionCreate(BaseModel):
    answers: List[AnswerSubmission]
    submission_id: Optional[int] = Field(default=None, gt=0)


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

    score: int = Field(ge=0, strict=True)
    feedback: Optional[str] = None


# --- Routes ---


@router.post("/", response_model=AssessmentResponse)
async def create_assessment(
    assessment_data: AssessmentCreate,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new assessment with questions"""

    if assessment_data.study_plan_id is not None:
        plan = db.get(StudyPlan, assessment_data.study_plan_id)
        require_allowed(can_manage_plan(db, current_user, plan))
    if assessment_data.topic_id is not None:
        require_allowed(
            can_reuse_content(
                db, current_user, db.get(Content, assessment_data.topic_id)
            )
        )
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
        is_published=False,
        max_attempts=assessment_data.max_attempts,
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
    if assessment_data.is_published:
        db.flush()
        _validate_publish(new_assessment)
        new_assessment.is_published = True
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
    assessments = db.query(Assessment).all()

    result = []
    for a in assessments:
        if not can_view_assessment(db, current_user, a):
            continue
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
    time_limit_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    max_attempts: Optional[int] = Field(default=None, ge=1, le=100)
    passing_score: Optional[int] = Field(default=None, ge=0, le=100)
    grading_mode: Optional[GradingMode] = None
    is_published: Optional[bool] = None
    questions: Optional[List[QuestionCreate]] = None
    rubric: Optional[RubricCreate] = None


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

    require_allowed(can_manage_assessment(db, current_user, assessment))
    _lock_attempts(db, assessment_id)
    db.refresh(assessment)
    has_attempts = (
        db.query(Submission.id).filter_by(assessment_id=assessment_id).first()
    )
    grading_fields = {
        "questions",
        "rubric",
        "passing_score",
        "grading_mode",
        "time_limit_minutes",
    }
    if has_attempts and grading_fields.intersection(update_data.model_fields_set):
        raise HTTPException(
            status_code=409,
            detail="Assessment grading rules cannot change after an attempt starts; create a new assessment",
        )

    # Update basic fields
    if update_data.title is not None:
        assessment.title = update_data.title
    if update_data.description is not None:
        assessment.description = update_data.description
    if update_data.time_limit_minutes is not None:
        assessment.time_limit_minutes = update_data.time_limit_minutes
    if update_data.max_attempts is not None:
        assessment.max_attempts = update_data.max_attempts
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
        for question in list(assessment.questions):
            db.delete(question)
        db.flush()
        db.expire(assessment, ["questions"])

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

    if "rubric" in update_data.model_fields_set:
        for rubric in list(assessment.rubrics):
            db.delete(rubric)
        db.flush()
        if update_data.rubric is not None:
            data = update_data.rubric
            rubric = Rubric(
                name=data.name,
                description=data.description,
                total_points=sum(c.max_points for c in data.criteria),
                created_by_id=current_user.id,
                assessment_id=assessment.id,
            )
            db.add(rubric)
            db.flush()
            for index, criterion in enumerate(data.criteria):
                db.add(
                    RubricCriterion(
                        rubric_id=rubric.id,
                        name=criterion.name,
                        description=criterion.description,
                        max_points=criterion.max_points,
                        order_index=index,
                    )
                )
        db.expire(assessment, ["rubrics"])

    db.flush()
    if assessment.is_published:
        db.expire(assessment, ["questions"])
        _validate_publish(assessment)
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
    """List only an owner's assessments or the learner's own submissions."""
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
        if not can_access_submission(db, current_user, sub):
            continue
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

    require_allowed(can_access_submission(db, current_user, submission))
    teacher_view = can_manage_assessment(db, current_user, submission.assessment)

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

    require_allowed(can_manage_assessment(db, current_user, submission.assessment))
    _require_submitted(submission)
    _validate_score(grade_data.score, submission.total_points or 0)
    # Update grade
    submission.score = grade_data.score
    submission.feedback = grade_data.feedback
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now()
    submission.teacher_approved = True

    record_assessed_mastery(db, submission)
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

    require_allowed(can_manage_assessment(db, current_user, submission.assessment))
    if submission.status == SubmissionStatus.GRADED and submission.teacher_approved:
        return {
            "status": "ok",
            "message": "Grade already finalized",
            "final_score": submission.score,
        }
    if submission.status != SubmissionStatus.AI_GRADED:
        raise HTTPException(
            status_code=400, detail="Submission is not pending AI review"
        )

    # Validate everything before applying any suggestion.
    for response in submission.responses:
        proposed = (
            response.score
            if response.score is not None
            else response.ai_suggested_score
        )
        if proposed is None:
            raise HTTPException(
                status_code=409,
                detail="Every answer needs a valid score before finalization",
            )
        _validate_score(proposed, response.question.points)
    total_score = 0
    for response in submission.responses:
        if response.score is None and response.ai_suggested_score is not None:
            response.score = response.ai_suggested_score
            response.feedback = response.ai_suggested_feedback
            response.is_correct = response.score == response.question.points
            response.graded_at = datetime.now()
        if response.score is not None:
            total_score += response.score

    submission.score = total_score
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now()
    submission.teacher_approved = True

    record_assessed_mastery(db, submission)
    db.commit()

    return {"status": "ok", "message": "AI grades accepted", "final_score": total_score}


class QuestionGradeInput(BaseModel):
    """Input for grading a single question"""

    score: int = Field(ge=0, strict=True)
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

    submission = response.submission
    require_allowed(can_manage_assessment(db, current_user, submission.assessment))
    _require_submitted(submission)
    _validate_score(grade_data.score, response.question.points)
    # Mark as teacher override if AI had suggested something different
    if (
        response.ai_suggested_score is not None
        and response.ai_suggested_score != grade_data.score
    ):
        response.teacher_override = True

    response.score = grade_data.score
    response.feedback = grade_data.feedback
    response.is_correct = grade_data.score == response.question.points
    response.graded_at = datetime.now()

    # Recalculate submission total
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if submission:
        total_score = sum(r.score or 0 for r in submission.responses)
        submission.score = (
            total_score
            if all(r.score is not None for r in submission.responses)
            else None
        )

        # Check if all questions are now graded
        all_graded = all(r.score is not None for r in submission.responses)
        if all_graded:
            submission.status = SubmissionStatus.GRADED
            submission.graded_at = datetime.now()
            submission.teacher_approved = True
        else:
            submission.status = (
                SubmissionStatus.AI_GRADED
                if any(r.ai_suggested_score is not None for r in submission.responses)
                else SubmissionStatus.SUBMITTED
            )
            submission.graded_at = None
            submission.teacher_approved = False

    record_assessed_mastery(db, submission)
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

    require_allowed(can_view_assessment(db, current_user, assessment))

    questions = []
    for q in assessment.questions:
        questions.append(
            QuestionResponseModel(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                points=q.points,
                options=q.options,
                correct_answer=(
                    q.get_decrypted_correct_answer()
                    if can_manage_assessment(db, current_user, assessment)
                    else None
                ),
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
        time_limit_minutes=assessment.time_limit_minutes,
        max_attempts=assessment.max_attempts,
        grading_mode=assessment.grading_mode.value,
        total_points=assessment.total_points,
        passing_score=assessment.passing_score,
        rubric=(
            _rubric_for_editor(assessment)
            if can_manage_assessment(db, current_user, assessment)
            else None
        ),
    )


def _rubric_for_editor(assessment: Assessment) -> Optional[RubricCreate]:
    """Round-trip the assessment rubric without exposing grading assets to learners."""
    if not assessment.rubrics:
        return None
    rubric = assessment.rubrics[0]
    return RubricCreate(
        name=rubric.name,
        description=rubric.description,
        criteria=[
            RubricCriterionCreate(
                name=item.name, description=item.description, max_points=item.max_points
            )
            for item in sorted(rubric.criteria, key=lambda item: item.order_index)
        ],
    )


def _validate_score(score: int, maximum: int) -> None:
    """Reject invalid score units instead of clamping or truncating them."""
    if type(score) is not int or not 0 <= score <= maximum:
        raise HTTPException(
            status_code=422, detail=f"Score must be an integer between 0 and {maximum}"
        )


def _require_submitted(submission: Submission) -> None:
    """Protect drafts from accidental final grading."""
    if submission.status == SubmissionStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Attempt has not been submitted")


def _validate_publish(assessment: Assessment) -> None:
    """Ensure a published assessment has usable questions and answer keys."""
    if not assessment.questions or any(q.points <= 0 for q in assessment.questions):
        raise HTTPException(
            status_code=422,
            detail="Published assessments require positive-point questions",
        )
    objective = {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}
    for question in assessment.questions:
        if (
            question.question_type in objective
            and not question.get_decrypted_correct_answer()
        ):
            raise HTTPException(
                status_code=422,
                detail="Objective questions require an answer key before publication",
            )
    assessment.total_points = sum(q.points for q in assessment.questions)


@router.post("/{assessment_id}/publish")
async def publish_assessment(
    assessment_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    """Publish an author's reviewed draft after validating its scoring assets."""
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    require_allowed(can_manage_assessment(db, current_user, assessment))
    _validate_publish(assessment)
    assessment.is_published = True
    db.commit()
    return {"id": assessment.id, "is_published": True}


def _lock_attempts(db: Session, assessment_id: int) -> None:
    """Serialize attempt creation/finalization, including on SQLite."""
    db.query(Assessment).filter_by(id=assessment_id).update(
        {Assessment.updated_at: Assessment.updated_at}, synchronize_session=False
    )


def _student_assessment(db: Session, user: User, assessment_id: int) -> Assessment:
    """Authorize the learner before reading assessment material."""
    require_allowed(is_student(user))
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    require_allowed(can_view_assessment(db, user, assessment))
    return assessment


def _reserve_attempt(db: Session, user: User, assessment: Assessment) -> Submission:
    """Reuse the open attempt; enforce the persisted maximum attempt count."""
    attempts = db.query(Submission).filter_by(
        assessment_id=assessment.id, student_id=user.id
    )
    draft = attempts.filter(Submission.status == SubmissionStatus.DRAFT).first()
    if draft:
        return draft
    if attempts.count() >= assessment.max_attempts:
        raise HTTPException(
            status_code=409, detail="Maximum assessment attempts reached"
        )
    if not assessment.questions:
        raise HTTPException(status_code=409, detail="Assessment has no questions")
    submission = Submission(
        assessment_id=assessment.id,
        student_id=user.id,
        status=SubmissionStatus.DRAFT,
        started_at=datetime.now(),
        total_points=sum(q.points for q in assessment.questions),
    )
    db.add(submission)
    db.flush()
    return submission


@router.post("/{assessment_id}/start")
async def start_assessment_attempt(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reserve one durable attempt, returning the same draft on retry."""
    assessment = _student_assessment(db, current_user, assessment_id)
    _lock_attempts(db, assessment_id)
    submission = _reserve_attempt(db, current_user, assessment)
    db.commit()
    expires = (
        submission.started_at + timedelta(minutes=assessment.time_limit_minutes)
        if assessment.time_limit_minutes
        else None
    )
    return {
        "id": submission.id,
        "submission_id": submission.id,
        "status": submission.status.value,
        "started_at": submission.started_at.astimezone(),
        "time_limit_minutes": assessment.time_limit_minutes,
        "expires_at": expires.astimezone() if expires else None,
    }


def _submission_result(submission: Submission) -> dict:
    """Serialize persisted state consistently for initial responses and retries."""
    return {
        "id": submission.id,
        "submission_id": submission.id,
        "score": submission.score,
        "total_points": submission.total_points,
        "status": submission.status.value,
        "grading_mode": submission.assessment.grading_mode.value,
        "ai_graded_questions": sum(
            r.ai_suggested_score is not None for r in submission.responses
        ),
        "needs_review": submission.status != SubmissionStatus.GRADED,
    }


def _validate_answers(assessment: Assessment, answers: list) -> dict:
    """Allow partial attempts, but never repeated or foreign question IDs."""
    ids = [answer.question_id for answer in answers]
    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=422, detail="Each question may be answered only once"
        )
    allowed = {question.id for question in assessment.questions}
    if not set(ids).issubset(allowed):
        raise HTTPException(
            status_code=422, detail="Answer does not belong to this assessment"
        )
    return {answer.question_id: answer.response_text for answer in answers}


def _same_answers(submission: Submission, answers: dict) -> bool:
    """Recognize legacy retries without storing cleartext fingerprints."""
    submitted = {
        response.question_id: response.get_decrypted_response() or ""
        for response in submission.responses
    }
    return submitted == {
        question.id: answers.get(question.id, "")
        for question in submission.assessment.questions
    }


def _get_attempt(
    db: Session,
    user: User,
    assessment: Assessment,
    data: SubmissionCreate,
    answers: dict,
) -> Submission:
    """Resolve a durable attempt identity or the legacy idempotent path."""
    attempts = db.query(Submission).filter_by(
        assessment_id=assessment.id, student_id=user.id
    )
    if data.submission_id:
        submission = attempts.filter_by(id=data.submission_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if submission.status != SubmissionStatus.DRAFT and not _same_answers(
            submission, answers
        ):
            raise HTTPException(
                status_code=409, detail="A submitted attempt cannot be changed"
            )
        return submission
    previous = (
        attempts.filter(Submission.status != SubmissionStatus.DRAFT)
        .order_by(Submission.id.desc())
        .first()
    )
    if previous and _same_answers(previous, answers):
        return previous
    if assessment.time_limit_minutes:
        raise HTTPException(
            status_code=409, detail="Start a timed attempt before submitting"
        )
    return _reserve_attempt(db, user, assessment)


def _grading_rubric(assessment: Assessment, question: Question) -> Optional[dict]:
    """Use persisted question rubrics, falling back to assessment criteria."""
    rubrics = question.rubrics or assessment.rubrics
    if not rubrics:
        return None
    return {
        "rubrics": [
            {
                "name": rubric.name,
                "description": rubric.description,
                "total_points": rubric.total_points,
                "criteria": [
                    {
                        "name": criterion.name,
                        "description": criterion.description,
                        "max_points": criterion.max_points,
                    }
                    for criterion in sorted(
                        rubric.criteria, key=lambda item: item.order_index
                    )
                ],
            }
            for rubric in rubrics
        ],
        "question_max_points": question.points,
    }


def _score_response(
    response: QuestionResponse, question: Question, answer: str
) -> None:
    """Score only deterministic work while persisting the submitted answer."""
    response.set_encrypted_response(answer)
    if not answer.strip():
        response.score = 0
        response.is_correct = False
        response.feedback = "Unanswered question: zero points."
        return
    correct = question.get_decrypted_correct_answer()
    if question.question_type in {
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TRUE_FALSE,
    }:
        if correct is None:
            response.feedback = "Answer key unavailable; teacher review required."
            return
        response.is_correct = correct.strip().casefold() == answer.strip().casefold()
        response.score = question.points if response.is_correct else 0


def _collect_suggestions(ai_service, jobs: list[dict]) -> list[dict]:
    """Call the provider using detached values and no open DB transaction."""
    suggestions = []
    try:
        for job in jobs:
            result = {
                "response_id": job["response_id"],
                "points": None,
                "feedback": "Automatic grading was unavailable or invalid. Teacher review is required.",
            }
            try:
                suggestion = ai_service.grade_answer(**job["grading_input"])
                points = suggestion.get("points_earned")
                if suggestion.get("status") == "needs_review" or not isinstance(
                    suggestion.get("feedback"), str
                ):
                    raise ValueError("Invalid grading suggestion")
                if (
                    type(points) is not int
                    or not 0 <= points <= job["grading_input"]["max_points"]
                ):
                    raise ValueError("Invalid points")
                result.update(points=points, feedback=suggestion["feedback"])
            except Exception:
                pass
            suggestions.append(result)
    finally:
        try:
            ai_service.close()
        except Exception:
            pass
    return suggestions


def _save_suggestions(
    db: Session, submission_id: int, suggestions: list[dict], late: bool
) -> None:
    """Apply suggestions only if no final teacher decision superseded them."""
    claimed = (
        db.query(Submission)
        .filter(
            Submission.id == submission_id,
            Submission.status == SubmissionStatus.SUBMITTED,
            Submission.teacher_approved.is_(False),
        )
        .update(
            {Submission.updated_at: Submission.updated_at}, synchronize_session=False
        )
    )
    if not claimed:
        db.rollback()
        return
    submission = db.get(Submission, submission_id)
    db.refresh(submission)
    for item in suggestions:
        response = db.get(QuestionResponse, item["response_id"])
        db.refresh(response)
        if response.score is None:
            response.ai_suggested_score = item["points"]
            response.ai_suggested_feedback = item["feedback"]
            response.ai_confidence = None
    db.flush()
    if any(
        response.ai_suggested_score is not None for response in submission.responses
    ):
        submission.ai_draft_score = sum(
            response.score or response.ai_suggested_score or 0
            for response in submission.responses
        )
        if not late:
            submission.status = SubmissionStatus.AI_GRADED
    db.commit()


@router.post("/{assessment_id}/submit")
def submit_assessment(
    assessment_id: int,
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Finalize one attempt once; preserve pending and expired work for review.

    Omitted/blank answers explicitly earn zero. Subjective AI suggestions are
    never final, including legacy ai_automatic assessments. Late timed work is
    preserved with a teacher-review flag rather than silently failed or lost.
    """
    assessment = _student_assessment(db, current_user, assessment_id)
    answers = _validate_answers(assessment, submission_data.answers)
    _lock_attempts(db, assessment_id)
    submission = _get_attempt(db, current_user, assessment, submission_data, answers)
    if submission.status != SubmissionStatus.DRAFT:
        db.rollback()
        return _submission_result(submission)
    submission.status = SubmissionStatus.SUBMITTED
    submission.submitted_at = datetime.now()
    submission.time_spent_minutes = max(
        0, int((submission.submitted_at - submission.started_at).total_seconds() / 60)
    )
    late = bool(
        assessment.time_limit_minutes
        and submission.submitted_at
        > submission.started_at + timedelta(minutes=assessment.time_limit_minutes)
    )
    ai_service = None
    subjective = any(
        q.question_type not in {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}
        and answers.get(q.id, "").strip()
        for q in assessment.questions
    )
    if subjective and assessment.grading_mode != GradingMode.MANUAL:
        try:
            instructor = db.get(User, assessment.created_by_id)
            ai_service = (
                get_ai_service_dependency(instructor, db) if instructor else None
            )
        except Exception:
            ai_service = None
    jobs = []
    for question in assessment.questions:
        answer = answers.get(question.id, "")
        response = QuestionResponse(submission=submission, question=question)
        _score_response(response, question, answer)
        db.add(response)
        db.flush()
        if (
            response.score is None
            and ai_service
            and question.question_type
            not in {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}
        ):
            jobs.append(
                {
                    "response_id": response.id,
                    "grading_input": {
                        "question": question.question_text,
                        "answer": answer,
                        "question_type": question.question_type.value,
                        "correct_answer": question.get_decrypted_correct_answer(),
                        "rubric": _grading_rubric(assessment, question),
                        "max_points": question.points,
                    },
                }
            )
    complete = all(response.score is not None for response in submission.responses)
    if complete and not late:
        submission.score = sum(response.score for response in submission.responses)
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.now()
    else:
        submission.score = None
        if late:
            submission.feedback = (
                "Time limit exceeded. Answers preserved for teacher review."
            )
    # Persist the attempt and its reward before any potentially slow provider call.
    award_activity_xp(db, current_user.id, 25)
    record_assessed_mastery(db, submission)
    submission_id = submission.id
    db.commit()
    if ai_service:
        suggestions = _collect_suggestions(ai_service, jobs)
        _save_suggestions(db, submission_id, suggestions, late)
    db.expire_all()
    return _submission_result(db.get(Submission, submission_id))


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

    require_allowed(can_manage_assessment(db, current_user, assessment))

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
    passing_score = (
        assessment.passing_score if assessment.passing_score is not None else 70
    )

    scores = []
    passed_count = 0

    for sub in submissions:
        if sub.score is not None:
            percentage = (sub.score / sub.total_points) * 100 if sub.total_points else 0
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

    _lock_attempts(db, assessment_id)
    db.refresh(assessment)
    # Check ownership (creator or admin)
    if not can_manage_assessment(db, current_user, assessment):
        raise HTTPException(
            status_code=403, detail="You can only delete assessments you created"
        )

    if assessment.submissions:
        raise HTTPException(
            status_code=409,
            detail="Assessments with attempts cannot be deleted; unpublish instead",
        )

    # Delete the assessment
    db.delete(assessment)
    db.commit()

    return {"success": True, "message": "Assessment deleted successfully"}
