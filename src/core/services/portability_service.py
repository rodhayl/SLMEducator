"""Audience-specific course packages and transactional draft-only imports.

Course packages never contain accounts, submissions, notes, or provider settings.
Private installation backups use the separate encrypted recovery service.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from hashlib import sha256
from uuid import uuid4
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
from src.core.services.content_schema import normalize_content, learner_content

PACKAGE_VERSION: Literal[2] = 2
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
COURSE_EXCLUSIONS = [
    "accounts and credentials",
    "student assignments and submissions",
    "learning notes, annotations and messages",
    "provider configuration",
    "original source binaries, external media and linked files",
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
    phase_index: int = Field(ge=0, le=100)
    order_index: int = Field(ge=0, le=1000)
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
    version: Literal[1, 2] = PACKAGE_VERSION
    manifest: dict = Field(default_factory=dict)
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
    result = learner_content(content.content_type.value, data, handout=True)
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
    # Ordered links are authoritative. Direct associations are a legacy fallback
    # only when the course has no link graph at all.
    if not links:
        linked.update(
            {
                content.id: content
                for content in db.query(Content).filter_by(study_plan_id=plan.id)
            }
        )
    contents = []
    for content in linked.values():
        references = list(content.difficulty_prerequisites or []) + (
            [content.remedial_for_content_id] if content.remedial_for_content_id else []
        )
        if teacher and not set(references).issubset(linked):
            raise ValueError(
                "Include prerequisite/remedial content in the course graph before exporting a teacher package"
            )
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
    if not links:
        for index, item in enumerate(contents):
            item["links"] = [
                {"phase_index": 0, "order_index": index, "is_required": True}
            ]
    assessments = []
    for item in (
        db.query(Assessment).filter_by(study_plan_id=plan.id).order_by(Assessment.id)
    ):
        if teacher and item.topic_id and item.topic_id not in linked:
            raise ValueError(
                "Include the assessment topic in the course graph before exporting"
            )
        allowed = (
            can_manage_assessment(db, user, item)
            if teacher
            else can_view_assessment(db, user, item)
        )
        if allowed and (teacher or item.is_published):
            assessments.append(_assessment_data(db, item, teacher, set(linked)))
    if not teacher:
        visible_assessments = {item["source_id"] for item in assessments}
        contents = [
            item
            for item in contents
            if item["kind"] != "assessment"
            or item["content_data"].get("assessment_id") in visible_assessments
        ]
        visible_contents = {item["source_id"] for item in contents}
        for item in contents:
            item["prerequisite_source_ids"] = [
                ref
                for ref in item["prerequisite_source_ids"]
                if ref in visible_contents
            ]
            if item["remedial_source_id"] not in visible_contents:
                item["remedial_source_id"] = None
        for item in assessments:
            if item["topic_source_id"] not in visible_contents:
                item["topic_source_id"] = None
    metadata = _clean_metadata(_json_field(plan.content_metadata)) if teacher else {}
    author_metadata = _json_field(plan.content_metadata)
    course_reference = (
        author_metadata.get("course_identity")
        or sha256(
            f"legacy:{plan.id}:{plan.creator_id}:{plan.created_at}".encode()
        ).hexdigest()
    )
    ordered = [item["source_id"] for item in contents]
    phases = _canonical_package_phases(plan.phases or [], contents)
    if teacher and phases != (plan.phases or []):
        metadata["author_outline"] = _clean_metadata(plan.phases or [])
    if "workflow" in metadata:
        metadata["workflow"] = {
            key: metadata["workflow"].get(key) for key in ("status", "version")
        }
    data = {
        "format": "slmeducator-course",
        "version": PACKAGE_VERSION,
        "manifest": {
            "course_reference": course_reference,
            "identity_provenance": (
                "persisted"
                if author_metadata.get("course_identity")
                else "derived_legacy_reference"
            ),
            "ordered_content_ids": ordered,
            "source_document_id": (
                author_metadata.get("source_document", {}).get("document_id")
                if teacher
                else None
            ),
            "review_version": author_metadata.get("workflow", {}).get("version", 0),
            "graph_provenance": (
                "ordered_links" if links else "legacy_direct_associations_id_order"
            ),
        },
        "audience": audience,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "study_plan": {
            "title": plan.title,
            "description": plan.description,
            "phases": phases if teacher else _learner_phases(phases),
            "metadata": metadata,
        },
        "contents": contents,
        "assessments": assessments,
        "books": [
            {
                "title": book.title,
                "chapter_source_ids": [
                    ref
                    for ref in book.chapters or []
                    if teacher or ref in visible_contents
                ],
            }
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
    return validate_package(data).model_dump(mode="json")


def _canonical_package_phases(phases: list, contents: list[dict]) -> list[dict]:
    """Use the same phase/order graph as rendering; preserve author outline separately."""
    indexes = {link["phase_index"] for item in contents for link in item["links"]}
    result = []
    for index in range(max(indexes | {len(phases) - 1}, default=-1) + 1):
        original = (
            phases[index]
            if index < len(phases) and isinstance(phases[index], dict)
            else {}
        )
        phase = {
            key: deepcopy(original[key])
            for key in ("name", "title", "description", "objectives")
            if key in original
        }
        phase.setdefault("name", f"Phase {index + 1}")
        ordered = sorted(
            (link["order_index"], item["source_id"])
            for item in contents
            for link in item["links"]
            if link["phase_index"] == index
        )
        phase["content_ids"] = [content_id for _, content_id in ordered]
        result.append(phase)
    return result


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
        "package_version": parsed.version,
        "compatible_versions": [1, 2],
        "validation": {
            "valid": True,
            "content_graph": "checked",
            "source": "reported provenance; original binary excluded",
        },
        "import_effect": "Creates an independent private draft; no existing course or assignment is overwritten",
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
    if type(data.get("version")) is not int or data["version"] not in {1, 2}:
        raise ValueError("Unsupported course package version")
    if len(package.study_plan.phases) > 101 or any(
        not isinstance(phase, dict) for phase in package.study_plan.phases
    ):
        raise ValueError("Course phases must be a list of at most 101 objects")
    for phase in package.study_plan.phases:
        for key in ("content_ids", "lessons"):
            if key in phase and not isinstance(phase[key], list):
                raise ValueError("Phase references must be lists")
    content_ids = [item.source_id for item in package.contents]
    assessment_ids = [item.source_id for item in package.assessments]
    if len(content_ids) != len(set(content_ids)) or len(assessment_ids) != len(
        set(assessment_ids)
    ):
        raise ValueError("Duplicate package IDs")
    positions = set()
    for item in package.contents:
        # Every ingress shares creation/editing semantics; validate before writes.
        item.content_data = normalize_content(item.kind.value, item.content_data)
        if len(item.links) > 1:
            raise ValueError(
                "A course item may appear only once in the canonical graph"
            )
        for link in item.links:
            position = (link.phase_index, link.order_index)
            if position in positions:
                raise ValueError("Course positions must be unique within each phase")
            positions.add(position)
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
    if package.version == 2:
        order = package.manifest.get("ordered_content_ids")
        if (
            not isinstance(order, list)
            or any(type(value) is not int for value in order)
            or len(order) != len(content_ids)
            or set(order) != set(content_ids)
        ):
            raise ValueError(
                "Version 2 manifest must include each content ID exactly once"
            )
        if (
            not isinstance(package.manifest.get("course_reference"), str)
            or not package.manifest["course_reference"]
        ):
            raise ValueError("Version 2 requires an explicit course reference")
        canonical_order = [
            content_id
            for _, _, content_id in sorted(
                (link.phase_index, link.order_index, item.source_id)
                for item in package.contents
                for link in item.links
            )
        ]
        if order != canonical_order:
            raise ValueError("Manifest order must match the canonical course graph")
        if package.audience == "teacher":
            expected = _canonical_package_phases(
                package.study_plan.phases,
                [item.model_dump(mode="json") for item in package.contents],
            )
            if [
                phase.get("content_ids", []) for phase in package.study_plan.phases
            ] != [phase["content_ids"] for phase in expected]:
                raise ValueError(
                    "Phase content references must match the canonical course graph"
                )
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
                if type(item) is not int or item <= 0:
                    raise ValueError("Embedded reference must be a positive integer")
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
            mapped_list = []
            for item in value:
                if type(item) is int:
                    if item not in content_ids:
                        raise ValueError(
                            "Phase content reference is outside this package"
                        )
                    mapped_list.append(content_ids[item])
                elif parent_key == "content_ids":
                    raise ValueError("Content references must be positive integers")
                else:
                    mapped_list.append(_remap(item, content_ids, assessment_ids, parent_key))
            return mapped_list
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
                        **link.model_dump(),
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
                topic_id=content_ids.get(item.topic_source_id) if item.topic_source_id is not None else None,
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
            content.remedial_for_content_id = content_ids.get(item.remedial_source_id) if item.remedial_source_id is not None else None
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
        metadata["course_identity"] = str(uuid4())
        metadata["import_lineage"] = {
            "source_course_reference": package.manifest.get("course_reference"),
            "package_version": package.version,
            "package_digest": sha256(
                json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
        }
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
            question_id=questions.get(source.question_source_id) if source.question_source_id is not None else None,
            total_points=sum(criterion.max_points for criterion in source.criteria),
        )
        db.add(rubric)
        db.flush()
        for criterion in source.criteria:
            db.add(RubricCriterion(rubric_id=rubric.id, **criterion.model_dump()))


def render_handout(package: dict, format_name: str) -> str:
    """Render the validated learner graph as inert, readable text with no external assets."""
    from html import escape

    parsed = validate_package(package)
    if parsed.audience != "learner" or format_name not in {"html", "markdown"}:
        raise ValueError("Readable formats require a learner handout")
    lines = [
        parsed.study_plan.title,
        parsed.study_plan.description or "",
        "Learner handout: not a restorable teacher package. External media and original files are excluded.",
    ]
    for item in parsed.contents:
        data = item.content_data
        lines.extend(["", item.title])
        sections = data.get("sections")
        if sections:
            for section in sections:
                lines.extend([section.get("title", ""), section.get("content", "")])
        else:
            for key in (
                "content",
                "text",
                "body",
                "question",
                "question_text",
                "instructions",
                "answer",
            ):
                if isinstance(data.get(key), str):
                    lines.append(data[key])
        for key in ("objectives", "key_concepts", "summary", "options"):
            value = data.get(key)
            if value:
                lines.append(
                    value
                    if isinstance(value, str)
                    else json.dumps(value, ensure_ascii=False)
                )
        for term in data.get("vocabulary", []):
            lines.append(f"{term.get('term', '')}: {term.get('definition', '')}")
    for assessment in parsed.assessments:
        lines.extend(["", assessment.title, assessment.instructions or ""])
        for question in sorted(
            assessment.questions, key=lambda question: question.order_index
        ):
            lines.append(f"{question.question_text} ({question.points} points)")
            if question.options:
                lines.append(
                    json.dumps(_learner_options(question.options), ensure_ascii=False)
                )
    text = "\n\n".join(str(line) for line in lines if line is not None)
    if format_name == "markdown":
        return escape(text)
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'
        + escape(parsed.study_plan.title)
        + "</title><body><main><h1>"
        + escape(parsed.study_plan.title)
        + "</h1><pre>"
        + escape(text)
        + "</pre></main></body></html>"
    )
