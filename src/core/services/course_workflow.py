"""Small, durable teacher review/publication workflow using existing metadata."""

from hashlib import sha256
import json
from sqlalchemy.orm import Session
from src.core.models import Content, StudyPlan, StudyPlanContent, StudentStudyPlan
from .content_schema import normalize_content


def metadata(plan: StudyPlan) -> dict:
    """Read metadata without treating a decryption failure as an empty course."""
    data = plan.decrypted_metadata
    if data is None and plan.content_metadata:
        raise ValueError("Course metadata cannot be decrypted with the current key")
    return data or {}


def workflow(plan: StudyPlan) -> dict:
    """Legacy courses remain readable but need review before new assignment."""
    return metadata(plan).get("workflow", {"status": "draft", "version": 0})


def course_items(db: Session, plan_id: int) -> list[StudyPlanContent]:
    """Return canonical phase/order links."""
    return (
        db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan_id)
        .order_by(
            StudyPlanContent.phase_index,
            StudyPlanContent.order_index,
            StudyPlanContent.id,
        )
        .all()
    )


def course_snapshot(db: Session, plan: StudyPlan) -> list[dict]:
    """Validate and fingerprint the exact reviewed content and its order."""
    result = []
    for link in course_items(db, plan.id):
        content = link.content
        if not content or content.is_personal:
            raise ValueError("Course items must reference nonpersonal content")
        data = normalize_content(
            content.content_type.value, content.decrypted_content_data or {}
        )
        result.append(
            {
                "content_id": content.id,
                "title": content.title,
                "phase_index": link.phase_index,
                "order_index": link.order_index,
                "digest": sha256(
                    json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
            }
        )
    if not result:
        raise ValueError("Add at least one lesson before review")
    return result


def assert_plan_editable(db: Session, plan: StudyPlan) -> None:
    """An assigned course stays stable; author a separate draft for changes."""
    if db.query(StudentStudyPlan.student_id).filter_by(study_plan_id=plan.id).first():
        raise ValueError(
            "Assigned material is immutable. Copy the course to a new draft before editing."
        )


def assert_content_editable(db: Session, content: Content) -> None:
    """Protect shared content already used in an assigned course."""
    plan_ids = {
        row[0]
        for row in db.query(StudyPlanContent.study_plan_id).filter_by(
            content_id=content.id
        )
    }
    if content.study_plan_id:
        plan_ids.add(content.study_plan_id)
    if (
        plan_ids
        and db.query(StudentStudyPlan.student_id)
        .filter(StudentStudyPlan.study_plan_id.in_(plan_ids))
        .first()
    ):
        raise ValueError(
            "This content belongs to an assigned course. Copy it to a new draft before editing."
        )


def invalidate_reviews(db: Session, content: Content) -> None:
    """A changed item requires another teacher review before publication."""
    plans = (
        db.query(StudyPlan)
        .outerjoin(StudyPlanContent)
        .filter(
            (StudyPlanContent.content_id == content.id)
            | (StudyPlan.id == content.study_plan_id)
        )
        .all()
    )
    for plan in plans:
        data = metadata(plan)
        previous = data.get("workflow", {})
        data["workflow"] = {"status": "draft", "version": previous.get("version", 0)}
        plan.set_encrypted_metadata(data)
        plan.is_public = False


def transition(
    db: Session, plan: StudyPlan, action: str, teacher_id: int, public: bool = False
) -> dict:
    """Review and publish explicit teacher decisions with version fingerprints."""
    data = metadata(plan)
    old = workflow(plan)
    snapshot = course_snapshot(db, plan)
    if action == "review":
        assert_plan_editable(db, plan)
        state = {
            "status": "reviewed",
            "version": old.get("version", 0),
            "reviewed_by": teacher_id,
            "snapshot": snapshot,
        }
    elif action == "publish":
        if old.get("status") == "published" and old.get("snapshot") == snapshot:
            return old
        if old.get("status") != "reviewed" or old.get("snapshot") != snapshot:
            raise ValueError("Review the current course before publishing")
        state = {**old, "status": "published", "version": old.get("version", 0) + 1}
        plan.is_public = public
    else:
        raise ValueError("Unknown course action")
    data["workflow"] = state
    plan.set_encrypted_metadata(data)
    return state


def require_published(db: Session, plan: StudyPlan) -> dict:
    """Only the reviewed exact version can be assigned."""
    state = workflow(plan)
    if state.get("status") != "published" or state.get("snapshot") != course_snapshot(
        db, plan
    ):
        raise ValueError("Review and publish the current course before assigning it")
    return state
