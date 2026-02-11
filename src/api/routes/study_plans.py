from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

from src.api.dependencies import get_db
from src.api.security import get_current_user
from src.core.models import (
    User,
    StudyPlan,
    Content,
    StudyPlanContent,
    ContentType,
    StudentStudyPlan,
    DailyGoal,
)
from src.core.roles import is_admin, is_student, is_teacher_or_admin

router = APIRouter(prefix="/api/study-plans", tags=["study-plans"])

# --- Permissions ---


def _is_assigned_student(db: Session, student_id: int, plan_id: int) -> bool:
    return (
        db.query(StudentStudyPlan)
        .filter(
            StudentStudyPlan.student_id == student_id,
            StudentStudyPlan.study_plan_id == plan_id,
        )
        .first()
        is not None
    )


def _can_view_plan(db: Session, user: User, plan: StudyPlan) -> bool:
    if is_admin(user):
        return True
    if is_teacher_or_admin(user) and plan.creator_id == user.id:
        return True
    if plan.is_public:
        return True
    # Students can view plans assigned to them
    if is_student(user):
        return _is_assigned_student(db, user.id, plan.id)
    return False


def _can_access_progress(db: Session, user: User, plan: StudyPlan) -> bool:
    if is_admin(user):
        return True
    if not is_student(user):
        return False
    if plan.is_public:
        return True
    return _is_assigned_student(db, user.id, plan.id)


# --- Progress Tracking Pydantic Models ---


class ProgressUpdate(BaseModel):
    """Request to update student's progress in a study plan."""

    completed_content_id: int
    current_phase_index: Optional[int] = None
    current_order_index: Optional[int] = None


class ProgressResponse(BaseModel):
    """Response with student's progress in a study plan."""

    study_plan_id: int
    completed_content_ids: List[int]
    last_content_id: Optional[int]
    last_phase_index: int
    last_order_index: int
    total_contents: int
    completion_percentage: float

    model_config = ConfigDict(from_attributes=True)


# --- Pydantic Models ---


class PhaseModel(BaseModel):
    name: str
    content_ids: List[int]


class StudyPlanCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_public: bool = False
    phases: List[PhaseModel] = []
    # We could also accept 'contents' list if not using phases, but explicit phases is better.


class StudyPlanResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_public: bool
    created_at: datetime
    # phases: Optional[List[Dict]] # Return raw JSON phases if needed

    model_config = ConfigDict(from_attributes=True)


# --- Assignment Models ---


class AssignStudentsRequest(BaseModel):
    student_ids: List[int]


class AssignStudentsResponse(BaseModel):
    study_plan_id: int
    assigned_student_ids: List[int]
    already_assigned_student_ids: List[int]


# --- Routes ---


@router.post("/", response_model=StudyPlanResponse)
async def create_study_plan(
    plan: StudyPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not is_teacher_or_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Only teachers/admins can create study plans"
            )

        # 1. Create Study Plan
        new_plan = StudyPlan(
            title=plan.title,
            description=plan.description,
            creator_id=current_user.id,
            is_public=plan.is_public,
            phases=[p.model_dump() for p in plan.phases],  # Store structure as JSON
            created_at=datetime.now(),
        )
        db.add(new_plan)
        db.flush()  # Get ID

        # 2. Create Associations (StudyPlanContent)
        # Flatten phases to linear contents if needed, or just store associations for query purposes.
        # We need StudyPlanContent to link Content to Plan for foreign key constraints and simple queries.

        association_order = 0
        for phase_idx, phase in enumerate(plan.phases):
            for content_id in phase.content_ids:
                # Verify content exists using proper SQLAlchemy 2.0 pattern
                content = db.query(Content).filter(Content.id == content_id).first()
                if not content:
                    continue  # Skip invalid IDs or raise? Skip for now.

                assoc = StudyPlanContent(
                    study_plan_id=new_plan.id,
                    content_id=content_id,
                    phase_index=phase_idx,
                    order_index=association_order,
                )
                db.add(assoc)
                association_order += 1

        db.commit()
        db.refresh(new_plan)
        return new_plan

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger(__name__).error(f"Error creating study plan: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create study plan. Please try again."
        )


@router.get("/", response_model=List[StudyPlanResponse])
async def list_study_plans(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # Teachers see plans they created; students see plans assigned to them.
    if is_teacher_or_admin(current_user):
        return db.query(StudyPlan).filter(StudyPlan.creator_id == current_user.id).all()

    assignments = (
        db.query(StudentStudyPlan.study_plan_id)
        .filter(StudentStudyPlan.student_id == current_user.id)
        .all()
    )
    plan_ids = [row[0] for row in assignments]
    if not plan_ids:
        return []
    return db.query(StudyPlan).filter(StudyPlan.id.in_(plan_ids)).all()


@router.post("/{plan_id}/assign", response_model=AssignStudentsResponse)
async def assign_students_to_plan(
    plan_id: int,
    req: AssignStudentsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_teacher_or_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Only teachers/admins can assign study plans"
        )

    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not is_admin(current_user) and plan.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    student_ids = sorted({int(sid) for sid in (req.student_ids or [])})
    if not student_ids:
        return AssignStudentsResponse(
            study_plan_id=plan_id,
            assigned_student_ids=[],
            already_assigned_student_ids=[],
        )

    students = db.query(User).filter(User.id.in_(student_ids)).all()
    by_id = {u.id: u for u in students}

    missing_ids = [sid for sid in student_ids if sid not in by_id]
    if missing_ids:
        raise HTTPException(
            status_code=400, detail=f"Unknown student_ids: {missing_ids}"
        )

    non_student_ids = [sid for sid in student_ids if not is_student(by_id[sid])]
    if non_student_ids:
        raise HTTPException(
            status_code=400, detail=f"Not student role: {non_student_ids}"
        )

    existing = (
        db.query(StudentStudyPlan.student_id)
        .filter(
            StudentStudyPlan.study_plan_id == plan_id,
            StudentStudyPlan.student_id.in_(student_ids),
        )
        .all()
    )
    already_assigned = sorted({row[0] for row in existing})
    to_assign = [sid for sid in student_ids if sid not in set(already_assigned)]

    for sid in to_assign:
        db.add(StudentStudyPlan(student_id=sid, study_plan_id=plan_id, progress={}))

    db.commit()

    return AssignStudentsResponse(
        study_plan_id=plan_id,
        assigned_student_ids=to_assign,
        already_assigned_student_ids=already_assigned,
    )


# --- Extended Pydantic Models for Hierarchical Operations ---


class ContentItemTree(BaseModel):
    """Content item for tree view."""

    id: int
    title: str
    content_type: str
    difficulty: int
    phase_index: int
    order_index: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudyPlanTree(BaseModel):
    """Study plan with nested content structure."""

    id: int
    title: str
    description: Optional[str]
    is_public: bool
    created_at: datetime
    phases: List[Dict[str, Any]]
    contents: List[ContentItemTree]
    content_count: int

    model_config = ConfigDict(from_attributes=True)


class TopicCreate(BaseModel):
    """Create a topic (Content) linked to a study plan."""

    title: str
    content_type: str = "lesson"  # Default to lesson
    description: Optional[str] = None
    difficulty: int = 1
    content_data: Optional[Dict[str, Any]] = None
    phase_index: int = 0


class GradeSummary(BaseModel):
    """Aggregate grade summary for a study plan or topic."""

    total_assessments: int
    graded_submissions: int
    pending_submissions: int
    average_score: Optional[float]
    passing_rate: Optional[float]


# --- Hierarchical Routes ---


@router.get("/{plan_id}", response_model=StudyPlanResponse)
async def get_study_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single study plan by ID."""
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not _can_view_plan(db, current_user, plan):
        raise HTTPException(status_code=403, detail="Access denied")

    return plan


@router.get("/{plan_id}/tree", response_model=StudyPlanTree)
async def get_study_plan_tree(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get study plan with full nested content structure.
    Returns hierarchical view for tree display in UI.
    """
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not _can_view_plan(db, current_user, plan):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all content associations ordered by phase and order
    associations = (
        db.query(StudyPlanContent)
        .filter(StudyPlanContent.study_plan_id == plan_id)
        .order_by(StudyPlanContent.phase_index, StudyPlanContent.order_index)
        .all()
    )

    contents = []
    for assoc in associations:
        content = assoc.content
        if content:
            contents.append(
                ContentItemTree(
                    id=content.id,
                    title=content.title,
                    content_type=(
                        content.content_type.value
                        if hasattr(content.content_type, "value")
                        else str(content.content_type)
                    ),
                    difficulty=content.difficulty,
                    phase_index=assoc.phase_index,
                    order_index=assoc.order_index,
                    created_at=content.created_at,
                )
            )

    return StudyPlanTree(
        id=plan.id,
        title=plan.title,
        description=plan.description,
        is_public=plan.is_public,
        created_at=plan.created_at,
        phases=plan.phases or [],
        contents=contents,
        content_count=len(contents),
    )


@router.post("/{plan_id}/topics", response_model=Dict[str, Any])
async def add_topic_to_study_plan(
    plan_id: int,
    topic: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a new topic (Content) to a study plan.
    Creates the content and links it to the study plan.
    """
    import logging

    logger = logging.getLogger(__name__)

    # Verify study plan exists and user has access
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not is_teacher_or_admin(current_user) or (
        not is_admin(current_user) and plan.creator_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    if plan.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can add topics")

    try:
        # Create the content
        content_type_enum = ContentType(topic.content_type)

        new_content = Content(
            title=topic.title,
            content_type=content_type_enum,
            difficulty=topic.difficulty,
            creator_id=current_user.id,
            study_plan_id=plan_id,
            created_at=datetime.now(),
        )

        if topic.content_data:
            new_content.set_encrypted_content_data(topic.content_data)

        db.add(new_content)
        db.flush()

        # Get max order index for this phase
        max_order = (
            db.query(StudyPlanContent)
            .filter(
                StudyPlanContent.study_plan_id == plan_id,
                StudyPlanContent.phase_index == topic.phase_index,
            )
            .count()
        )

        # Create association
        assoc = StudyPlanContent(
            study_plan_id=plan_id,
            content_id=new_content.id,
            phase_index=topic.phase_index,
            order_index=max_order,
        )
        db.add(assoc)

        db.commit()
        db.refresh(new_content)

        return {
            "success": True,
            "content_id": new_content.id,
            "title": new_content.title,
            "content_type": topic.content_type,
            "phase_index": topic.phase_index,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error adding topic to study plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to add topic")


@router.get("/{plan_id}/grades", response_model=GradeSummary)
async def get_study_plan_grades(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregate grade summary for a study plan.
    Returns total assessments, submission counts, and averages.
    """
    from src.core.models import Assessment, AssessmentSubmission, SubmissionStatus

    # Verify access
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if plan.creator_id != current_user.id and not plan.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all assessments linked to this study plan
    assessments = db.query(Assessment).filter(Assessment.study_plan_id == plan_id).all()
    assessment_ids = [a.id for a in assessments]

    if not assessment_ids:
        return GradeSummary(
            total_assessments=0,
            graded_submissions=0,
            pending_submissions=0,
            average_score=None,
            passing_rate=None,
        )

    # Get submission stats
    submissions = (
        db.query(AssessmentSubmission)
        .filter(AssessmentSubmission.assessment_id.in_(assessment_ids))
        .all()
    )

    graded = [
        s
        for s in submissions
        if s.status == SubmissionStatus.GRADED
        or (hasattr(s.status, "value") and s.status.value == "graded")
    ]
    pending = [
        s
        for s in submissions
        if s.status == SubmissionStatus.SUBMITTED
        or (hasattr(s.status, "value") and s.status.value == "submitted")
    ]

    # Calculate average score
    scores = [s.score for s in graded if s.score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Calculate passing rate
    if graded:
        passing = sum(
            1
            for s in graded
            if s.score and s.assessment and s.score >= s.assessment.passing_score
        )
        passing_rate = (passing / len(graded)) * 100
    else:
        passing_rate = None

    return GradeSummary(
        total_assessments=len(assessments),
        graded_submissions=len(graded),
        pending_submissions=len(pending),
        average_score=round(avg_score, 1) if avg_score else None,
        passing_rate=round(passing_rate, 1) if passing_rate else None,
    )


@router.get("/{plan_id}/topics/{topic_id}/grades", response_model=GradeSummary)
async def get_topic_grades(
    plan_id: int,
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregate grade summary for a specific topic within a study plan.
    """
    from src.core.models import Assessment, AssessmentSubmission, SubmissionStatus

    # Verify access
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if plan.creator_id != current_user.id and not plan.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify topic exists in this plan
    content = db.query(Content).filter(Content.id == topic_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get assessments linked to this topic
    assessments = db.query(Assessment).filter(Assessment.topic_id == topic_id).all()
    assessment_ids = [a.id for a in assessments]

    if not assessment_ids:
        return GradeSummary(
            total_assessments=0,
            graded_submissions=0,
            pending_submissions=0,
            average_score=None,
            passing_rate=None,
        )

    # Get submission stats (same logic as plan-level)
    submissions = (
        db.query(AssessmentSubmission)
        .filter(AssessmentSubmission.assessment_id.in_(assessment_ids))
        .all()
    )

    graded = [
        s
        for s in submissions
        if s.status == SubmissionStatus.GRADED
        or (hasattr(s.status, "value") and s.status.value == "graded")
    ]
    pending = [
        s
        for s in submissions
        if s.status == SubmissionStatus.SUBMITTED
        or (hasattr(s.status, "value") and s.status.value == "submitted")
    ]

    scores = [s.score for s in graded if s.score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    if graded:
        passing = sum(
            1
            for s in graded
            if s.score and s.assessment and s.score >= s.assessment.passing_score
        )
        passing_rate = (passing / len(graded)) * 100
    else:
        passing_rate = None

    return GradeSummary(
        total_assessments=len(assessments),
        graded_submissions=len(graded),
        pending_submissions=len(pending),
        average_score=round(avg_score, 1) if avg_score else None,
        passing_rate=round(passing_rate, 1) if passing_rate else None,
    )


# --- Progress Tracking Routes ---


@router.get("/{plan_id}/my-progress", response_model=ProgressResponse)
async def get_my_progress(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's progress in a study plan.
    Returns completed content IDs, current position, and completion percentage.
    """
    # Verify study plan exists
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not _can_access_progress(db, current_user, plan):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get total content count
    total_contents = (
        db.query(StudyPlanContent)
        .filter(StudyPlanContent.study_plan_id == plan_id)
        .count()
    )

    # Get or create student study plan record
    student_plan = (
        db.query(StudentStudyPlan)
        .filter(
            StudentStudyPlan.study_plan_id == plan_id,
            StudentStudyPlan.student_id == current_user.id,
        )
        .first()
    )

    if not student_plan:
        # No progress yet - return defaults
        return ProgressResponse(
            study_plan_id=plan_id,
            completed_content_ids=[],
            last_content_id=None,
            last_phase_index=0,
            last_order_index=0,
            total_contents=total_contents,
            completion_percentage=0.0,
        )

    # Extract progress data from JSON field
    progress_data = student_plan.progress or {}
    completed_ids = progress_data.get("completed_content_ids", [])

    completion_pct = (
        (len(completed_ids) / total_contents * 100) if total_contents > 0 else 0.0
    )

    return ProgressResponse(
        study_plan_id=plan_id,
        completed_content_ids=completed_ids,
        last_content_id=progress_data.get("last_content_id"),
        last_phase_index=progress_data.get("last_phase_index", 0),
        last_order_index=progress_data.get("last_order_index", 0),
        total_contents=total_contents,
        completion_percentage=round(completion_pct, 1),
    )


@router.post("/{plan_id}/progress", response_model=ProgressResponse)
async def update_progress(
    plan_id: int,
    progress_update: ProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update student's progress in a study plan.
    Marks a content item as completed and updates last position.
    """
    import logging

    logger = logging.getLogger(__name__)

    # Verify study plan exists
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if not _can_access_progress(db, current_user, plan):
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify content exists in this plan
    content_assoc = (
        db.query(StudyPlanContent)
        .filter(
            StudyPlanContent.study_plan_id == plan_id,
            StudyPlanContent.content_id == progress_update.completed_content_id,
        )
        .first()
    )

    if not content_assoc:
        raise HTTPException(
            status_code=404, detail="Content not found in this study plan"
        )

    # Get total content count
    total_contents = (
        db.query(StudyPlanContent)
        .filter(StudyPlanContent.study_plan_id == plan_id)
        .count()
    )

    try:
        # Get or create student study plan record
        student_plan = (
            db.query(StudentStudyPlan)
            .filter(
                StudentStudyPlan.study_plan_id == plan_id,
                StudentStudyPlan.student_id == current_user.id,
            )
            .first()
        )

        if not student_plan:
            # Create new assignment/progress record
            student_plan = StudentStudyPlan(
                student_id=current_user.id, study_plan_id=plan_id, progress={}
            )
            db.add(student_plan)
            db.flush()

        # Update progress data
        # NOTE: SQLAlchemy JSON fields don't reliably detect in-place mutations
        # without MutableDict/MutableList. Always work on fresh copies.
        progress_data = dict(student_plan.progress or {})
        completed_ids = list(progress_data.get("completed_content_ids", []))

        # Add new completed content if not already in list
        if progress_update.completed_content_id not in completed_ids:
            completed_ids.append(progress_update.completed_content_id)

        # Update progress JSON
        progress_data["completed_content_ids"] = completed_ids
        progress_data["last_content_id"] = progress_update.completed_content_id
        progress_data["last_phase_index"] = (
            progress_update.current_phase_index or content_assoc.phase_index
        )
        progress_data["last_order_index"] = (
            progress_update.current_order_index or content_assoc.order_index
        )
        progress_data["completed"] = len(completed_ids)
        progress_data["score"] = (
            (len(completed_ids) / total_contents) if total_contents > 0 else 0.0
        )

        student_plan.progress = progress_data

        # Mark as completed if all content done
        if len(completed_ids) >= total_contents:
            # from datetime import datetime
            student_plan.completed_at = datetime.now()

        db.commit()

        # Update Daily Goal
        today = date.today()
        daily_goal = (
            db.query(DailyGoal)
            .filter(DailyGoal.user_id == current_user.id, DailyGoal.goal_date == today)
            .first()
        )

        if daily_goal and not daily_goal.completed:
            # Basic logic: always increment.
            # Ideally we check goal_type, but let's assume 'lessons' or count any content for now.
            daily_goal.current_value += 1
            if daily_goal.current_value >= daily_goal.target_value:
                daily_goal.completed = True
                # Optional: Award bonus XP for goal completion? (Handled by awardXP separately?)

        db.commit()

        completion_pct = (
            (len(completed_ids) / total_contents * 100) if total_contents > 0 else 0.0
        )

        return ProgressResponse(
            study_plan_id=plan_id,
            completed_content_ids=completed_ids,
            last_content_id=progress_data["last_content_id"],
            last_phase_index=progress_data["last_phase_index"],
            last_order_index=progress_data["last_order_index"],
            total_contents=total_contents,
            completion_percentage=round(completion_pct, 1),
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to update progress")
