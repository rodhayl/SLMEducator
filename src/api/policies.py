"""Object authorization for the supported single-installation teaching model.

Administrators manage the installation. Teachers own resources and their enrolled
learners; assignments never grant a teacher access to a different teacher's work.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.core.models import (
    Assessment,
    Content,
    ContentType,
    StudentStudyPlan,
    StudyPlan,
    StudyPlanContent,
    User,
    UserRole,
)
from src.core.roles import is_admin, is_student, is_teacher


def teacher_student_ids(db: Session, teacher_id: int | None) -> list[int]:
    """Return explicitly enrolled learners, including legacy unclaimed assignments."""
    if teacher_id is None:
        return []
    enrolled = {
        row[0]
        for row in db.query(User.id)
        .filter(User.teacher_id == teacher_id, User.role == UserRole.STUDENT)
        .all()
    }
    legacy = (
        db.query(User.id, User.settings)
        .join(StudentStudyPlan, StudentStudyPlan.student_id == User.id)
        .join(StudyPlan, StudyPlan.id == StudentStudyPlan.study_plan_id)
        .filter(
            User.teacher_id.is_(None),
            User.role == UserRole.STUDENT,
            StudyPlan.creator_id == teacher_id,
        )
        .all()
    )
    return sorted(
        enrolled
        | {row[0] for row in legacy if not (row[1] or {}).get("enrollment_explicit")}
    )


def can_manage_student(db: Session, user: User, student: User) -> bool:
    """Only administrators or the enrolled teacher manage a learner."""
    return bool(
        student
        and is_student(student)
        and (
            is_admin(user)
            or (is_teacher(user) and student.id in teacher_student_ids(db, user.id))
        )
    )


def can_manage_plan(db: Session, user: User, plan: StudyPlan) -> bool:
    """Check plan ownership without granting write access through visibility."""
    return bool(
        plan and (is_admin(user) or (is_teacher(user) and plan.creator_id == user.id))
    )


def can_view_plan(db: Session, user: User, plan: StudyPlan) -> bool:
    """Public or assigned plans are readable; private plans remain owner scoped."""
    if not plan:
        return False
    if can_manage_plan(db, user, plan) or plan.is_public:
        return True
    return bool(
        is_student(user)
        and db.query(StudentStudyPlan.student_id)
        .filter_by(study_plan_id=plan.id, student_id=user.id)
        .first()
    )


def _source_public(db: Session, content: Content) -> bool:
    """Only an original creator's public plan can grant public reuse."""
    return bool(
        db.query(StudyPlan.id)
        .outerjoin(StudyPlanContent)
        .filter(
            StudyPlan.creator_id == content.creator_id,
            StudyPlan.is_public.is_(True),
            (StudyPlanContent.content_id == content.id)
            | (StudyPlan.id == content.study_plan_id),
        )
        .first()
    )


def can_reuse_content(db: Session, user: User, content: Content) -> bool:
    """Sharing personal work with a teacher does not authorize republication."""
    return bool(
        content
        and (
            is_admin(user)
            or (
                is_teacher(user)
                and (
                    content.creator_id == user.id
                    or (not content.is_personal and _source_public(db, content))
                )
            )
        )
    )


def can_view_content(db: Session, user: User, content: Content) -> bool:
    """Enforce the same content visibility at every resource entry point."""
    if not content:
        return False
    if is_admin(user) or content.creator_id == user.id:
        return True
    if is_teacher(user):
        return bool(
            (not content.is_personal and _source_public(db, content))
            or (
                content.is_personal
                and content.shared_with_teacher
                and content.content_type == ContentType.QA
                and content.creator_id in teacher_student_ids(db, user.id)
            )
        )
    if not is_student(user) or content.is_personal:
        return False
    # Validate the link's provenance too: legacy unauthorized links cannot expose
    # private content merely because a learner can view the destination plan.
    plans = (
        db.query(StudyPlan)
        .outerjoin(StudyPlanContent)
        .filter(
            (StudyPlanContent.content_id == content.id)
            | (StudyPlan.id == content.study_plan_id)
        )
        .all()
    )
    return any(
        can_view_plan(db, user, plan)
        and (plan.creator_id == content.creator_id or _source_public(db, content))
        for plan in plans
    )


def can_manage_assessment(db: Session, user: User, assessment: Assessment) -> bool:
    """Only an assessment author or administrator can edit or grade it."""
    return bool(
        assessment
        and (
            is_admin(user) or (is_teacher(user) and assessment.created_by_id == user.id)
        )
    )


def can_view_assessment(db: Session, user: User, assessment: Assessment) -> bool:
    """Learners need publication and an authorized plan or enrolled teacher."""
    if can_manage_assessment(db, user, assessment):
        return True
    if not assessment or not is_student(user) or not assessment.is_published:
        return False
    if assessment.study_plan_id:
        plan = db.get(StudyPlan, assessment.study_plan_id)
        return bool(
            plan
            and plan.creator_id == assessment.created_by_id
            and can_view_plan(db, user, plan)
        )
    return user.id in teacher_student_ids(db, assessment.created_by_id)


def can_access_submission(db: Session, user: User, submission) -> bool:
    """Learners see their attempt; the assessment owner manages feedback."""
    return bool(
        submission
        and (
            submission.student_id == user.id
            or can_manage_assessment(db, user, submission.assessment)
        )
    )


def require_allowed(allowed: bool) -> None:
    """Return a consistent authorization failure without leaking object details."""
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")


def require_content(db: Session, user: User, content_id: int) -> Content:
    """Resolve and authorize a selected content item before reading its body."""
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    require_allowed(can_view_content(db, user, content))
    return content


def require_plan(db: Session, user: User, plan_id: int) -> StudyPlan:
    """Resolve and authorize a selected plan."""
    plan = db.get(StudyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    require_allowed(can_view_plan(db, user, plan))
    return plan


def can_message(db: Session, user: User, other: User) -> bool:
    """Local pilot contacts are staff/enrollment scoped, never a global directory."""
    if not other or not other.active or other.id == user.id:
        return False
    if is_admin(user) or is_admin(other):
        return True
    return can_manage_student(db, user, other) or can_manage_student(db, other, user)
