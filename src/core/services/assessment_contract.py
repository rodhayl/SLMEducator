"""Shared executable-assessment validation and deterministic review identity."""

from hashlib import sha256
import json
from typing import Optional

from src.core.models import Assessment, Question, QuestionType


def usable_answer_key(question: Question) -> Optional[str]:
    """Require actual decryption before a persisted key can govern a result."""
    try:
        answer = question.get_decrypted_correct_answer()
    except Exception:
        return None
    if (
        not isinstance(answer, str)
        or not answer.strip()
        or answer == question.correct_answer
    ):
        return None
    return answer


def validate_definition(assessment: Assessment) -> None:
    """Reject incomplete definitions before assessment or course publication."""
    if not assessment.questions or any(q.points <= 0 for q in assessment.questions):
        raise ValueError("Published assessments require positive-point questions")
    for question in assessment.questions:
        if question.question_type in {
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.TRUE_FALSE,
        } and not usable_answer_key(question):
            raise ValueError(
                "Objective questions require an answer key before publication"
            )


def definition_digest(assessment: Assessment) -> str:
    """Fingerprint questions, grading rules and rubrics without exposing keys."""
    data = {
        "id": assessment.id,
        "title": assessment.title,
        "instructions": assessment.instructions,
        "topic_id": assessment.topic_id,
        "time_limit_minutes": assessment.time_limit_minutes,
        "max_attempts": assessment.max_attempts,
        "passing_score": assessment.passing_score,
        "grading_mode": assessment.grading_mode.value,
        "is_published": assessment.is_published,
        "questions": [
            {
                "id": q.id,
                "text": q.question_text,
                "type": q.question_type.value,
                "points": q.points,
                "order": q.order_index,
                "options": q.options,
                "metadata": q.content_metadata,
                "key": usable_answer_key(q),
            }
            for q in sorted(assessment.questions, key=lambda q: (q.order_index, q.id))
        ],
        "rubrics": [
            {
                "question_id": r.question_id,
                "name": r.name,
                "description": r.description,
                "criteria": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "points": c.max_points,
                        "order": c.order_index,
                    }
                    for c in sorted(r.criteria, key=lambda c: (c.order_index, c.id))
                ],
            }
            for r in sorted(assessment.rubrics, key=lambda r: r.id)
        ],
    }
    return sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
