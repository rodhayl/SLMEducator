"""Audience-specific course packages and transactional draft-only imports.

Course packages never contain accounts, submissions, notes, or provider settings.
Private installation backups use the separate encrypted recovery service.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any, Literal

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.api.policies import (
    can_manage_assessment,
    can_manage_plan,
    can_reuse_content,
    can_view_assessment,
    can_view_content,
    can_view_plan,
)
from src.core.models import (
    Assessment,
    Book,
    Content,
    ContentType,
    GradingMode,
    Question,
    QuestionType,
    Rubric,
    RubricCriterion,
    StudyPlan,
    StudyPlanContent,
    User,
)
from src.core.models.models import ENCRYPTION_KEY
from src.core.services.assistance_policy import (
    AssistanceMode,
    assessment_policy,
    set_assessment_policy,
)

PACKAGE_VERSION = 1
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
COURSE_EXCLUSIONS = [
    "accounts and credentials",
    "student assignments and submissions",
    "learning notes, annotations and messages",
    "provider configuration",
]


class PackageModel(BaseModel):
    """Reject unknown package fields rather than interpreting executable metadata."""

    model_config = ConfigDict(extra="forbid")


class CriterionData(PackageModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    max_points: int = Field(gt=0, le=10000)
    order_index: int = Field(default=0, ge=0)


class RubricData(PackageModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    question_source_id: int | None = None
    criteria: list[CriterionData] = Field(default_factory=list, max_length=100)


class QuestionData(PackageModel):
    source_id: int = Field(gt=0)
    question_text: str = Field(min_length=1)
    question_type: QuestionType
    points: int = Field(gt=0, le=10000)
    order_index: int = Field(ge=0)
    options: Any = None
    correct_answer: str | None = None
    content_metadata: dict = Field(default_factory=dict)


class AssessmentData(PackageModel):
    source_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    instructions: str | None = None
    topic_source_id: int | None = None
    time_limit_minutes: int | None = Field(default=None, gt=0, le=1440)
    max_attempts: int = Field(default=1, ge=1, le=100)
    passing_score: int = Field(default=70, ge=0, le=100)
    grading_mode: GradingMode = GradingMode.AI_ASSISTED
    assistance_policy: AssistanceMode = "hints_only"
    questions: list[QuestionData] = Field(default_factory=list, max_length=500)
    rubrics: list[RubricData] = Field(default_factory=list, max_length=100)


class LinkData(PackageModel):
    phase_index: int = Field(ge=0)
    order_index: int = Field(ge=0)
    is_required: bool = True


class ContentData(PackageModel):
    source_id: int = Field(gt=0)
    kind: ContentType
    title: str = Field(min_length=1, max_length=200)
    difficulty: int = Field(default=1, ge=1, le=10)
    estimated_time_min: int = Field(default=15, ge=0, le=10000)
    content_data: dict = Field(default_factory=dict)
    links: list[LinkData] = Field(default_factory=list, max_length=1000)
    verification_required: bool = False
    remedial_source_id: int | None = None
    prerequisite_source_ids: list[int] = Field(default_factory=list)


class PlanData(PackageModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    phases: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class BookData(PackageModel):
    title: str = Field(min_length=1, max_length=200)
    chapter_source_ids: list[int] = Field(default_factory=list, max_length=1000)


class CoursePackage(PackageModel):
    format: Literal["slmeducator-course"] = "slmeducator-course"
    version: Literal[1] = PACKAGE_VERSION
    audience: Literal["learner", "teacher"]
    exported_at: str
    study_plan: PlanData
    contents: list[ContentData] = Field(default_factory=list, max_length=1000)
    assessments: list[AssessmentData] = Field(default_factory=list, max_length=100)
    books: list[BookData] = Field(default_factory=list, max_length=1000)
    exclusions: list[str] = Field(default_factory=list)


def _decrypt(value: str | None) -> str | None:
    """Detect a mismatched key instead of exporting ciphertext as an answer."""
    if not value:
        return None
    if value.startswith("gAAAA"):
        try:
            return Fernet(ENCRYPTION_KEY).decrypt(value.encode()).decode()
        except (InvalidToken, ValueError) as error:
            raise ValueError(
                "A course field cannot be decrypted with the current key"
            ) from error
    return value  # Explicit compatibility with legacy plaintext fields.


def _json_field(value: str | None) -> dict:
    """Read persisted course JSON without silently replacing damaged fields."""
    parsed = json.loads(_decrypt(value) or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("Course content must contain an object")
    return parsed


def _clean_metadata(value: Any) -> Any:
    """Omit configuration/identity keys accidentally embedded in authored metadata."""
    forbidden = {
        "api_key",
        "apikey",
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "secret",
        "credentials",
        "student_id",
        "user_id",
        "reviewed_by",
        "created_by_id",
        "assigned_snapshot",
        "submissions",
        "annotations",
        "messages",
        "notes",
        "creator_id",
        "teacher_id",
    }
    if isinstance(value, dict):
        return {
            key: _clean_metadata(item)
            for key, item in value.items()
            if key.lower() not in forbidden
        }
    if isinstance(value, list):
        return [_clean_metadata(item) for item in value]
    return value


def _learner_content(content: Content, data: dict) -> dict:
    """Handouts contain visible instructional fields, not hidden grading assets."""
    allowed = {
        ContentType.LESSON: {
            "title",
            "content",
            "text",
            "body",
            "sections",
            "summary",
            "objectives",
            "key_concepts",
        },
        ContentType.EXERCISE: {
            "question",
            "question_text",
            "type",
            "question_type",
            "options",
            "points",
        },
        ContentType.ASSESSMENT: {"assessment_id", "title", "instructions"},
        ContentType.QA: {"question", "answer", "content"},
    }[content.content_type]
    result = {key: deepcopy(value) for key, value in data.items() if key in allowed}
    if "sections" in result:
        result["sections"] = [
            {key: value for key, value in item.items() if key in {"title", "content"}}
            for item in result["sections"]
            if isinstance(item, dict)
        ]
    if "options" in result:
        result["options"] = _learner_options(result["options"])
    return result


def _learner_options(value: Any) -> Any:
    """Option labels cannot smuggle correctness flags or explanations."""
    if isinstance(value, list):
        return [
            (
                item
                if isinstance(item, str)
                else {key: item[key] for key in ("id", "text", "label") if key in item}
            )
            for item in value
            if isinstance(item, (str, dict))
        ]
    if isinstance(value, dict):
        return {
            key: item
            for key, item in value.items()
            if isinstance(item, str)
            and key.lower()
            not in {"answer", "correct_answer", "solution", "explanation"}
        }
    return None


def _rubric_data(rubric: Rubric) -> dict:
    return {
        "name": rubric.name,
        "description": rubric.description,
        "question_source_id": rubric.question_id,
        "criteria": [
            {
                "name": item.name,
                "description": item.description,
                "max_points": item.max_points,
                "order_index": item.order_index,
            }
            for item in sorted(rubric.criteria, key=lambda item: item.order_index)
        ],
    }


def _assessment_data(
    db: Session, item: Assessment, teacher: bool, content_ids: set[int]
) -> dict:
    questions = []
    for question in sorted(item.questions, key=lambda q: q.order_index):
        questions.append(
            {
                "source_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "points": question.points,
                "order_index": question.order_index,
                "options": (
                    question.options if teacher else _learner_options(question.options)
                ),
                "correct_answer": (
                    _decrypt(question.correct_answer) if teacher else None
                ),
                "content_metadata": (
                    _clean_metadata(question.content_metadata or {}) if teacher else {}
                ),
            }
        )
    rubrics = {rubric.id: rubric for rubric in item.rubrics}
    for question in item.questions:
        rubrics.update({rubric.id: rubric for rubric in question.rubrics})
    return {
        "source_id": item.id,
        "title": item.title,
        "description": item.description,
        "instructions": item.instructions,
        "topic_source_id": item.topic_id if item.topic_id in content_ids else None,
        "time_limit_minutes": item.time_limit_minutes,
        "max_attempts": item.max_attempts,
        "passing_score": item.passing_score,
        "grading_mode": item.grading_mode.value,
        "assistance_policy": assessment_policy(db, item),
        "questions": questions,
        "rubrics": (
            [_rubric_data(rubric) for rubric in rubrics.values()] if teacher else []
        ),
    }


def export_course(db: Session, user: User, plan: StudyPlan, audience: str) -> dict:
    """Create an authorized, audience-limited course package without user records."""
    if audience not in {"learner", "teacher"}:
        raise ValueError("Choose learner or teacher export")
    teacher = audience == "teacher"
    if not (
        can_manage_plan(db, user, plan) if teacher else can_view_plan(db, user, plan)
    ):
        raise PermissionError("Access denied")
    links = (
        db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan.id)
        .order_by(
            StudyPlanContent.phase_index,
            StudyPlanContent.order_index,
            StudyPlanContent.id,
        )
        .all()
    )
    linked = {link.content_id: link.content for link in links}
    linked.update(
        {
            content.id: content
            for content in db.query(Content).filter_by(study_plan_id=plan.id)
        }
    )
    contents = []
    for content in linked.values():
        allowed = (
            can_reuse_content(db, user, content)
            if teacher
            else can_view_content(db, user, content)
        )
        if content.is_personal or not allowed:
            raise PermissionError("Course contains content outside your export scope")
        data = _json_field(content.content_data)
        contents.append(
            {
                "source_id": content.id,
                "kind": content.content_type.value,
                "title": content.title,
                "difficulty": content.difficulty,
                "estimated_time_min": content.estimated_time_min,
                "content_data": (
                    _clean_metadata(data)
                    if teacher
                    else _learner_content(content, data)
                ),
                "links": [
                    {
                        "phase_index": link.phase_index,
                        "order_index": link.order_index,
                        "is_required": link.is_required,
                    }
                    for link in links
                    if link.content_id == content.id
                ],
                "verification_required": content.verification_required,
                "remedial_source_id": (
                    content.remedial_for_content_id
                    if content.remedial_for_content_id in linked
                    else None
                ),
                "prerequisite_source_ids": [
                    item
                    for item in content.difficulty_prerequisites or []
                    if item in linked
                ],
            }
        )
    assessments = []
    for item in (
        db.query(Assessment).filter_by(study_plan_id=plan.id).order_by(Assessment.id)
    ):
        allowed = (
            can_manage_assessment(db, user, item)
            if teacher
            else can_view_assessment(db, user, item)
        )
        if allowed and (teacher or item.is_published):
            assessments.append(_assessment_data(db, item, teacher, set(linked)))
    metadata = _clean_metadata(_json_field(plan.content_metadata)) if teacher else {}
    if "workflow" in metadata:
        metadata["workflow"] = {
            key: metadata["workflow"].get(key) for key in ("status", "version")
        }
    data = {
        "format": "slmeducator-course",
        "version": PACKAGE_VERSION,
        "audience": audience,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "study_plan": {
            "title": plan.title,
            "description": plan.description,
            "phases": (
                _clean_metadata(plan.phases or [])
                if teacher
                else _learner_phases(plan.phases or [])
            ),
            "metadata": metadata,
        },
        "contents": contents,
        "assessments": assessments,
        "books": [
            {"title": book.title, "chapter_source_ids": book.chapters or []}
            for book in db.query(Book)
            .filter_by(study_plan_id=plan.id)
            .order_by(Book.id)
        ],
        "exclusions": COURSE_EXCLUSIONS
        + (
            []
            if teacher
            else [
                "answer keys, rubrics and grading metadata",
                "draft assessments",
                "teacher workflow and generation state",
            ]
        ),
    }
    return CoursePackage.model_validate(data).model_dump(mode="json")


def _learner_phases(phases: list) -> list:
    """Only phase headings/objectives belong in a learner handout."""
    return [
        {
            key: deepcopy(item[key])
            for key in ("title", "name", "description", "objectives")
            if key in item
        }
        for item in phases
        if isinstance(item, dict)
    ]


def preview_package(package: dict) -> dict:
    """Describe exactly what is included before an export/import action."""
    parsed = validate_package(package)
    return {
        "audience": parsed.audience,
        "counts": {
            "contents": len(parsed.contents),
            "assessments": len(parsed.assessments),
            "books": len(parsed.books),
            "questions": sum(len(item.questions) for item in parsed.assessments),
        },
        "includes": [
            "course structure and ordered learning content",
            "assessment questions",
        ]
        + (["answer keys and rubrics"] if parsed.audience == "teacher" else []),
        "excludes": parsed.exclusions,
        "warnings": (
            [
                "Teacher packages contain answer keys; share only with intended instructors."
            ]
            if parsed.audience == "teacher"
            else ["Learner handouts are not restorable teacher course packages."]
        ),
    }


def validate_package(data: dict) -> CoursePackage:
    """Validate size, IDs and references before any import writes."""
    if len(json.dumps(data, ensure_ascii=False).encode()) > MAX_PACKAGE_BYTES:
        raise ValueError("Course package exceeds the 10 MB limit")
    package = CoursePackage.model_validate(data)
    content_ids = [item.source_id for item in package.contents]
    assessment_ids = [item.source_id for item in package.assessments]
    if len(content_ids) != len(set(content_ids)) or len(assessment_ids) != len(
        set(assessment_ids)
    ):
        raise ValueError("Duplicate package IDs")
    for item in package.contents:
        refs = item.prerequisite_source_ids + (
            [item.remedial_source_id] if item.remedial_source_id else []
        )
        if not set(refs).issubset(content_ids):
            raise ValueError("Content reference is outside this package")
    for book in package.books:
        if not set(book.chapter_source_ids).issubset(content_ids):
            raise ValueError("Book chapter is outside this package")
    for item in package.assessments:
        ids = [question.source_id for question in item.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate question IDs")
        if item.topic_source_id and item.topic_source_id not in content_ids:
            raise ValueError("Assessment topic is outside this package")
        if any(
            rubric.question_source_id and rubric.question_source_id not in ids
            for rubric in item.rubrics
        ):
            raise ValueError("Rubric question is outside this assessment")
    content_map = {source_id: source_id for source_id in content_ids}
    assessment_map = {source_id: source_id for source_id in assessment_ids}
    _remap(package.study_plan.phases, content_map, assessment_map)
    _remap(package.study_plan.metadata, content_map, assessment_map)
    for item in package.contents:
        _remap(item.content_data, content_map, assessment_map)
    return package


def _remap(
    value: Any, content_ids: dict, assessment_ids: dict, parent_key: str = ""
) -> Any:
    """Remap recognized local references without copying source account identities."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            mapping = (
                content_ids
                if key in {"content_id", "contentId", "remedial_for_content_id"}
                else (
                    assessment_ids if key in {"assessment_id", "assessmentId"} else None
                )
            )
            if mapping is not None and item is not None:
                if item not in mapping:
                    raise ValueError("Embedded reference is outside this package")
                result[key] = mapping[item]
            elif (
                key == "id"
                and parent_key in {"lessons", "content"}
                and isinstance(item, int)
            ):
                if item not in content_ids:
                    raise ValueError("Phase content reference is outside this package")
                result[key] = content_ids[item]
            else:
                result[key] = _remap(item, content_ids, assessment_ids, key)
        return result
    if isinstance(value, list):
        if parent_key in {"content_ids", "lessons", "content"}:
            return [
                (
                    content_ids[item]
                    if isinstance(item, int) and item in content_ids
                    else _remap(item, content_ids, assessment_ids, parent_key)
                )
                for item in value
            ]
        return [_remap(item, content_ids, assessment_ids, parent_key) for item in value]
    return value


def import_course(db: Session, user: User, data: dict) -> StudyPlan:
    """Import one complete course atomically as a new private, unpublished draft.

    Caller commits only after success. A savepoint rolls back all imported rows
    on any invalid reference, even when the caller already has a transaction.
    """
    from src.core.roles import is_teacher_or_admin

    if not is_teacher_or_admin(user):
        raise PermissionError("Only instructors can import teacher packages")
    package = validate_package(data)
    if package.audience != "teacher":
        raise ValueError("Learner handouts cannot restore a teacher course")
    with db.begin_nested():
        plan = StudyPlan(
            title=package.study_plan.title,
            description=package.study_plan.description,
            creator_id=user.id,
            is_public=False,
            phases=[],
        )
        db.add(plan)
        db.flush()
        content_ids, assessment_ids = {}, {}
        for item in package.contents:
            content = Content(
                title=item.title,
                creator_id=user.id,
                study_plan_id=plan.id,
                content_type=item.kind,
                difficulty=item.difficulty,
                estimated_time_min=item.estimated_time_min,
                is_personal=False,
                verification_required=item.verification_required,
            )
            db.add(content)
            db.flush()
            content_ids[item.source_id] = content.id
            for link in item.links:
                db.add(
                    StudyPlanContent(
                        study_plan_id=plan.id,
                        content_id=content.id,
                        **link.model_dump()
                    )
                )
        for item in package.assessments:
            assessment = Assessment(
                title=item.title,
                description=item.description,
                instructions=item.instructions,
                time_limit_minutes=item.time_limit_minutes,
                max_attempts=item.max_attempts,
                passing_score=item.passing_score,
                grading_mode=item.grading_mode,
                total_points=sum(q.points for q in item.questions),
                is_published=False,
                created_by_id=user.id,
                study_plan_id=plan.id,
                topic_id=content_ids.get(item.topic_source_id),
            )
            db.add(assessment)
            db.flush()
            assessment_ids[item.source_id] = assessment.id
            set_assessment_policy(db, assessment, item.assistance_policy)
        for item in package.assessments:
            assessment = db.get(Assessment, assessment_ids[item.source_id])
            _import_questions(
                db, assessment, item, user.id, content_ids, assessment_ids
            )
        for item in package.contents:
            content = db.get(Content, content_ids[item.source_id])
            content.set_encrypted_content_data(
                _remap(_clean_metadata(item.content_data), content_ids, assessment_ids)
            )
            content.remedial_for_content_id = content_ids.get(item.remedial_source_id)
            content.difficulty_prerequisites = [
                content_ids[source_id] for source_id in item.prerequisite_source_ids
            ]
        for item in package.books:
            db.add(
                Book(
                    study_plan_id=plan.id,
                    title=item.title,
                    chapters=[
                        content_ids[source_id] for source_id in item.chapter_source_ids
                    ],
                )
            )
        metadata = _remap(
            _clean_metadata(package.study_plan.metadata), content_ids, assessment_ids
        )
        metadata["workflow"] = {"status": "draft", "version": 0}
        plan.set_encrypted_metadata(metadata)
        plan.phases = _remap(package.study_plan.phases, content_ids, assessment_ids)
        db.flush()
    return plan


def _import_questions(
    db: Session,
    assessment: Assessment,
    item: AssessmentData,
    owner_id: int,
    content_ids: dict,
    assessment_ids: dict,
) -> None:
    """Preserve question order, encrypted keys, and both rubric scopes."""
    questions = {}
    for source in item.questions:
        question = Question(
            assessment_id=assessment.id,
            question_text=source.question_text,
            question_type=source.question_type,
            points=source.points,
            order_index=source.order_index,
            options=source.options,
            content_metadata=_remap(
                _clean_metadata(source.content_metadata), content_ids, assessment_ids
            ),
        )
        question.set_encrypted_correct_answer(source.correct_answer)
        db.add(question)
        db.flush()
        questions[source.source_id] = question.id
    for source in item.rubrics:
        rubric = Rubric(
            name=source.name,
            description=source.description,
            created_by_id=owner_id,
            assessment_id=assessment.id,
            question_id=questions.get(source.question_source_id),
            total_points=sum(criterion.max_points for criterion in source.criteria),
        )
        db.add(rubric)
        db.flush()
        for criterion in source.criteria:
            db.add(RubricCriterion(rubric_id=rubric.id, **criterion.model_dump()))
