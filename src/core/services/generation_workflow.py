"""Resumable per-item course generation in encrypted SQLite plan metadata.

The supported launcher uses one application process. A per-plan lock prevents
simultaneous requests from duplicating items; commits persist each ready/failure
state. Restarted calls reuse ready item IDs and retry only unfinished items.
"""

from hashlib import sha256
import json
import math
from decimal import Decimal
from threading import Lock

from src.core.models import (
    Assessment,
    AssessmentQuestion,
    Content,
    ContentType,
    GradingMode,
    QuestionType,
    Rubric,
    RubricCriterion,
    StudyPlanContent,
)
from src.core.services.content_schema import normalize_content
from src.core.services.course_workflow import (
    metadata,
    assert_plan_editable,
    invalidate_reviews,
    next_course_position,
)
from src.core.services.learning_context import GENERATION_PROMPT_VERSION, LESSON_GENERATION_PROMPT_VERSION
from src.core.exceptions import AIResponseParseError, AIContentValidationError
from src.core.services.source_documents import source_prompt, save_document

_LOCKS: dict[int, Lock] = {}
_REGISTRY_LOCK = Lock()


def _plan_lock(plan_id: int) -> Lock:
    with _REGISTRY_LOCK:
        return _LOCKS.setdefault(plan_id, Lock())


def _fingerprint(request) -> str:
    # This identifies a teacher's resumable request, not its prompt protocol.
    # Preserve ready IDs/edits across upgrades. Newly generated missing items
    # record their own protocol in _save_item; do not relabel earlier items.
    fields = request.model_dump(exclude={"auto_save"})
    # Preserve the identity of pre-selector mixed requests and their ready items.
    if fields.get("assessment_question_types") is None:
        fields.pop("assessment_question_types", None)
    else:
        fields["assessment_question_types"] = [getattr(kind, "value", kind) for kind in fields["assessment_question_types"]]
    return sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def _tasks(request) -> list[tuple[str, str, int]]:
    tasks = []
    if request.include_lesson:
        tasks.append(("lesson", "lesson", 0))
    if request.include_exercises:
        tasks.extend(
            (f"exercise-{i}", "exercise", i) for i in range(request.num_exercises)
        )
    if request.include_assessment:
        tasks.append(("assessment", "assessment", 0))
    return tasks


def _generate(service, request, kind: str, index: int) -> dict:
    _, usage = source_prompt(
        request.source_material,
        request.topic_name + " " + " ".join(request.learning_objectives),
    )
    if kind == "lesson":
        result = service.generate_lesson(
            topic=request.topic_name,
            grade_level=request.grade_level,
            learning_objectives=request.learning_objectives,
            duration_minutes=30,
            source_material=request.source_material,
        )
    elif kind == "exercise":
        result = service.generate_exercise(
            topic=request.topic_name,
            difficulty=request.exercise_difficulty,
            exercise_type=["multiple_choice", "true_false", "short_answer"][index % 3],
            source_material=request.source_material,
            grade_level=request.grade_level,
            learning_objectives=request.learning_objectives,
        )
    else:
        questions = service.generate_assessment_questions(
            topic=request.topic_name,
            learning_objectives=request.learning_objectives,
            question_types=[getattr(kind, "value", kind) for kind in request.assessment_question_types]
            if getattr(request, "assessment_question_types", None) else None,
            num_questions=request.num_assessment_questions,
            difficulty=request.assessment_difficulty,
            source_material=request.source_material,
            grade_level=request.grade_level,
        )
        result = {
            "title": f"Assessment: {request.topic_name}",
            "questions": questions,
            "passing_score": 70,
        }
    result.setdefault("_source_usage", usage)
    if kind == "lesson" and request.learning_objectives:
        result["objectives"] = list(request.learning_objectives)
    # Generated exam definitions are converted transactionally to Assessment;
    # only the resulting pointer is learner Content and uses that schema.
    return result if kind == "assessment" else normalize_content(kind, result)


def _generated_answer_text(answer: object) -> str:
    """Keep fresh JSON scalar answers consistent with the browser boundary."""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, bool):
        return "true" if answer else "false"
    if not isinstance(answer, (int, float)):
        # Provider data errors use the workflow's content-validation retry path.
        raise ValueError("Generated multiple-choice questions need an answer key")  # noqa: TRY004
    try:
        number = float(answer)
    except OverflowError as error:
        raise ValueError("Generated answer numbers must be finite") from error
    if not math.isfinite(number):
        raise ValueError("Generated answer numbers must be finite")
    if number == 0:
        return "0"
    # JavaScript displays finite numbers in fixed notation in this range.
    if 1e-6 <= abs(number) < 1e21:
        value = format(Decimal(repr(number)), "f")
        return value.rstrip("0").rstrip(".") if "." in value else value
    mantissa, exponent = repr(number).split("e")
    return f"{mantissa.removesuffix('.0')}e{int(exponent):+d}"


def _generated_choices(options: object, answer: object) -> tuple[dict, str]:
    """Give only fresh provider choices explicit values without guessing a key.

    Historical rows keep their displayed-text answer semantics. Fresh outputs
    may supply either a value or a label, but conflicting interpretations must
    be reviewed/regenerated rather than silently picking one.
    """
    if isinstance(options, dict) and "choices" in options:
        options = options["choices"]
    if isinstance(options, list):
        options = {str(index + 1): label for index, label in enumerate(options)}
    if not isinstance(options, dict) or len(options) < 2:
        raise ValueError("Generated multiple-choice questions need at least two choices")
    if any(
        not isinstance(key, str) or not key.strip()
        or not isinstance(label, str) or not label.strip()
        for key, label in options.items()
    ):
        raise ValueError("Generated choices need nonempty text values and labels")
    # Match the fresh frontend boundary's conservative Unicode alias check.
    # Two upper/lower rounds also collapse capital sharp S through ß to ss.
    values = [key.strip().upper().lower().upper().lower() for key in options]
    scoring_values = [key.strip().casefold() for key in options]
    if len(set(values)) != len(values) or len(set(scoring_values)) != len(values):
        raise ValueError("Generated choice values must be distinct")
    answer_text = _generated_answer_text(answer)
    if not answer_text.strip():
        raise ValueError("Generated multiple-choice questions need an answer key")
    normalized_answer = answer_text.strip().lower()
    matches = [
        key for key, label in options.items()
        if normalized_answer in {key.strip().lower(), label.strip().lower()}
    ]
    if len(matches) != 1:
        raise ValueError("Generated answer must identify exactly one choice")
    return {"choices": dict(options)}, matches[0]


def _draft_assessment(db, user, request, data: dict) -> Assessment:
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("Assessment generation returned no questions")
    assessment = Assessment(
        title=data.get("title") or request.topic_name,
        created_by_id=user.id,
        study_plan_id=request.study_plan_id,
        is_published=False,
        grading_mode=GradingMode.AI_ASSISTED,
        total_points=0,
    )
    db.add(assessment)
    db.flush()
    total_points = 0
    for index, item in enumerate(questions):
        text = item.get("question_text") or item.get("question")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Generated assessment contains an empty question")
        points = item.get("points", 10)
        if (
            not isinstance(points, int)
            or isinstance(points, bool)
            or not 1 <= points <= 100
        ):
            raise ValueError("Generated question points must be between 1 and 100")
        kind = QuestionType(
            item.get("question_type") or item.get("type") or "short_answer"
        )
        options = item.get("options")
        answer = item.get("correct_answer")
        if kind == QuestionType.MULTIPLE_CHOICE:
            options, answer = _generated_choices(options, answer)
        elif isinstance(options, list):
            options = {str(i + 1): value for i, value in enumerate(options)}
        question = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text=text,
            question_type=kind,
            points=points,
            options=options,
            order_index=index,
            content_metadata={
                "explanation": item.get("explanation"),
                "hints": item.get("hints"),
            },
        )
        if answer is not None:
            question.set_encrypted_correct_answer(str(answer))
        db.add(question)
        db.flush()
        rubric_data = item.get("rubric")
        if rubric_data:
            if (
                not isinstance(rubric_data, dict)
                or not isinstance(rubric_data.get("criteria"), list)
                or not rubric_data["criteria"]
            ):
                raise ValueError("Generated rubric needs explicit criteria")
            criteria = rubric_data["criteria"]
            if any(
                not isinstance(criterion, dict)
                or not isinstance(criterion.get("max_points"), int)
                or isinstance(criterion["max_points"], bool)
                or criterion["max_points"] < 1
                or not criterion.get("name")
                for criterion in criteria
            ):
                raise ValueError(
                    "Generated rubric criteria need names and positive point limits"
                )
            if sum(criterion["max_points"] for criterion in criteria) != points:
                raise ValueError("Generated rubric points must match its question")
            rubric = Rubric(
                name=rubric_data.get("name") or "Generated draft rubric",
                created_by_id=user.id,
                assessment_id=assessment.id,
                question_id=question.id,
                total_points=points,
            )
            db.add(rubric)
            db.flush()
            for order, criterion in enumerate(criteria):
                db.add(
                    RubricCriterion(
                        rubric_id=rubric.id,
                        name=criterion["name"],
                        description=criterion.get("description"),
                        max_points=criterion["max_points"],
                        order_index=order,
                    )
                )
        total_points += points
        assessment.total_points = total_points
    return assessment


def _save_item(
    db, user, plan, service, request, kind: str, index: int, data: dict, position: int
) -> dict:
    if db.query(StudyPlanContent).filter_by(
        study_plan_id=plan.id, phase_index=request.phase_index, order_index=position
    ).first():
        raise ValueError("Reserved course position changed; create a new generation request")
    data["generation"] = {
        "model": service.model,
        "provider": service.provider.value,
        "prompt_version": LESSON_GENERATION_PROMPT_VERSION if kind == "lesson" else GENERATION_PROMPT_VERSION,
        "source_version": sha256((request.source_material or "").encode()).hexdigest(),
        "review_status": "draft",
        "structural_status": "valid",
        "source_support": "unverified",
        "source_document_id": request.source_document_id,
        "source_origin": {
            key: value
            for key, value in metadata(plan).get("source_document", {}).items()
            if key not in {"sections", "extracted_text"}
        },
        "source_usage": data.pop("_source_usage", {}),
        "extraction_coverage": metadata(plan)
        .get("source_document", {})
        .get("extraction_coverage", "unknown"),
    }
    assessment_id = None
    if kind == "assessment":
        assessment = _draft_assessment(db, user, request, data)
        assessment_id = assessment.id
        # Learner content contains a link, never the hidden assessment answer key.
        data = {
            "schema_version": 1,
            "kind": "assessment",
            "assessment_id": assessment_id,
            "title": assessment.title,
            "generation": data["generation"],
        }
    content = Content(
        title=data.get("title") or f"{kind.title()}: {request.topic_name}",
        content_type=ContentType(kind),
        creator_id=user.id,
        study_plan_id=plan.id,
    )
    content.set_encrypted_content_data(data)
    db.add(content)
    db.flush()
    db.add(
        StudyPlanContent(
            study_plan_id=plan.id,
            content_id=content.id,
            phase_index=request.phase_index,
            order_index=position,
        )
    )
    invalidate_reviews(db, content)
    return {"status": "ready", "content_id": content.id, "assessment_id": assessment_id}


def _record(db, plan, job_key: str, job: dict) -> None:
    data = metadata(plan)
    jobs = data.get("generation_jobs", {})
    if job_key not in jobs and len(jobs) >= 100:
        raise ValueError(
            "This course reached its 100 generation-request limit; create a new draft"
        )
    if jobs.get(job_key, {}).get("cancel_requested"):
        job["cancel_requested"] = True
    if jobs.get(job_key, {}).get("obsolete_source"):
        job["obsolete_source"] = True
    jobs[job_key] = job
    data["generation_jobs"] = jobs
    plan.set_encrypted_metadata(data)
    db.commit()


def _reserve_positions(db, plan, request, job: dict, tasks: list) -> None:
    """Reserve each item's position before generation, including failed gaps."""
    if "item_positions" in job:
        if any(
            type(position) is not int or not 0 <= position <= 1000
            for position in job["item_positions"].values()
        ):
            raise ValueError("Course phase is full; create a new draft for this job")
        for key, position in job["item_positions"].items():
            occupied = db.query(StudyPlanContent).filter_by(
                study_plan_id=plan.id,
                phase_index=request.phase_index,
                order_index=position,
            ).first()
            if occupied and occupied.content_id != job["items"].get(key, {}).get("content_id"):
                raise ValueError("Reserved course position changed; create a new generation request")
        return
    links = (
        db.query(StudyPlanContent)
        .filter_by(study_plan_id=plan.id, phase_index=request.phase_index)
        .all()
    )
    prior = {
        item.get("content_id")
        for item in job["items"].values()
        if item.get("status") == "ready"
    }
    prior_positions = [link.order_index for link in links if link.content_id in prior]
    # Existing jobs from the draft implementation retain their first position.
    base = (
        min(prior_positions)
        if prior_positions
        else next_course_position(db, plan, request.phase_index, len(tasks))
    )
    if base < 0 or base + len(tasks) - 1 > 1000:
        raise ValueError("Course phase is full; create a new draft for this job")
    job["phase_index"] = request.phase_index
    job["item_positions"] = {
        item_key: base + offset for offset, (item_key, _, _) in enumerate(tasks)
    }
    # A legacy partial job may have appended later ready items ahead of a failure.
    for item_key, item in job["items"].items():
        for link in links:
            if (
                link.content_id == item.get("content_id")
                and item_key in job["item_positions"]
            ):
                link.order_index = job["item_positions"][item_key]


def generate_package(db, user, plan, service, request) -> dict:
    """Generate the missing items and return truthful saved/failure state."""
    key = _fingerprint(request)
    result = {
        "success": True,
        "topic_name": request.topic_name,
        "lesson": None,
        "exercises": [],
        "assessment": None,
        "saved_content_ids": [],
        "items": [],
        "job_key": key,
    }
    lock = _plan_lock(plan.id) if plan is not None else Lock()
    if not lock.acquire(blocking=False):
        raise ValueError(
            "Generation is already running for this course; wait and retry"
        )
    try:
        expected_source = None
        if plan is not None:
            db.refresh(plan)
            assert_plan_editable(db, plan)
            document = metadata(plan).get("source_document")
            if not document and request.source_material:
                document = save_document(
                    db, plan, {"extracted_text": request.source_material}
                )
                db.commit()
            if document:
                if (
                    request.source_document_id
                    and request.source_document_id != document["document_id"]
                ):
                    raise ValueError(
                        "Source revision changed; reload or explicitly save a new source"
                    )
                if (
                    request.source_material
                    and request.source_material != document["extracted_text"]
                ):
                    raise ValueError(
                        "Save the changed source explicitly before generating content"
                    )
                request = request.model_copy(
                    update={
                        "source_material": document["extracted_text"],
                        "source_document_id": document["document_id"],
                    }
                )
                key = _fingerprint(request)
                result["job_key"] = key
            expected_source = document
        job = (
            metadata(plan).get("generation_jobs", {}).get(key, {"items": {}})
            if plan
            else {"items": {}}
        )
        # A new explicit request resumes an earlier cancelled package. It never
        # restarts a concurrent request because the per-course lock is held.
        if plan and job.get("cancel_requested"):
            job["cancel_requested"] = False
            current = metadata(plan)
            current.setdefault("generation_jobs", {})[key] = job
            plan.set_encrypted_metadata(current)
            db.commit()
        tasks = _tasks(request)
        if plan:
            job["source_document_id"] = request.source_document_id
            _reserve_positions(db, plan, request, job, tasks)
            _record(db, plan, key, job)
        for item_key, kind, index in tasks:
            item = job["items"].get(item_key, {})
            data = None
            if item.get("status") == "ready" and plan:
                saved = db.get(Content, item["content_id"])
                if saved:
                    data = saved.decrypted_content_data
                if data is None:
                    item = {
                        "status": "failed",
                        "error_code": "saved_content_unavailable",
                    }
            if data is None and item.get("error_code") != "saved_content_unavailable":
                try:
                    if plan:
                        db.refresh(plan)
                        latest = metadata(plan).get("generation_jobs", {}).get(key, {})
                        if latest.get("cancel_requested"):
                            item = {"status": "cancelled", "error_code": "cancelled"}
                            job["items"][item_key] = item
                            result["success"] = False
                            result["items"].append({"key": item_key, **item})
                            _record(db, plan, key, job)
                            continue
                        job["items"][item_key] = {"status": "running"}
                        _record(db, plan, key, job)
                        _require_current_generation_source(db, plan, expected_source)
                    data = _generate(service, request, kind, index)
                    if plan:
                        _require_current_generation_source(db, plan, expected_source)
                    item = (
                        _save_item(
                            db,
                            user,
                            plan,
                            service,
                            request,
                            kind,
                            index,
                            data,
                            job["item_positions"][item_key],
                        )
                        if plan
                        else {"status": "ready"}
                    )
                except Exception as exc:
                    db.rollback()
                    data = None
                    item = {
                        "status": "failed",
                        "error_code": (
                            "content_validation"
                            if isinstance(exc, (ValueError, AIContentValidationError))
                            else (
                                "parse_failure"
                                if isinstance(exc, AIResponseParseError)
                                else "provider_failure"
                            )
                        ),
                    }
            job["items"][item_key] = item
            if plan:
                # Content and its ready marker share this commit; no phantom save.
                _record(db, plan, key, job)
            result["items"].append({"key": item_key, **item})
            if item.get("status") != "ready":
                result["success"] = False
                continue
            if item.get("content_id"):
                result["saved_content_ids"].append(item["content_id"])
            if kind == "exercise":
                result["exercises"].append(data)
            else:
                result[kind] = data
        return result
    finally:
        lock.release()


def _require_current_generation_source(db, plan, expected_source: dict | None) -> None:
    """Do not save an old answer under changed source/provenance or assignment."""
    db.refresh(plan)
    assert_plan_editable(db, plan)
    current = metadata(plan).get("source_document")
    if current != expected_source:
        raise ValueError("Source revision changed during generation; review and retry")
