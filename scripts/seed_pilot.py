"""Create a new disposable synthetic installation for the reviewed pilot journey."""

import argparse
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def seed_pilot(database: Path) -> dict:
    """Refuse existing data and create two teachers, two learners and three lessons."""
    database = database.resolve()
    if (
        database.exists()
        or Path(str(database) + "-wal").exists()
        or Path(str(database) + "-shm").exists()
    ):
        raise FileExistsError(
            "Pilot destination must be new; existing installation is never changed"
        )
    database.parent.mkdir(parents=True, exist_ok=True)
    os.environ["SLM_DB_PATH"] = str(database)
    from src.core.services.database import init_db_service, get_db_service
    from src.core.services.auth import AuthService
    from src.core.models import (
        UserRole,
        StudyPlan,
        Content,
        ContentType,
        StudyPlanContent,
        Assessment,
        AssessmentQuestion,
        QuestionType,
        GradingMode,
    )
    from src.core.services.content_schema import normalize_content
    from scripts.seed_admin import seed_admin_user

    init_db_service(str(database))
    if seed_admin_user() != 0:
        raise RuntimeError("Pilot administrator bootstrap failed")
    auth = AuthService()
    accounts, credentials = {}, []
    for name, role in [
        ("teacher_a", UserRole.TEACHER),
        ("teacher_b", UserRole.TEACHER),
        ("learner_a", UserRole.STUDENT),
        ("learner_b", UserRole.STUDENT),
    ]:
        password = secrets.token_urlsafe(24) + "A1!"
        teacher_id = (
            accounts.get(name.replace("learner", "teacher"), {}).get("id")
            if role == UserRole.STUDENT
            else None
        )
        accounts[name] = auth.register_user(
            name,
            name + "@example.test",
            password,
            "Synthetic",
            name,
            role,
            teacher_id=teacher_id,
        )
        credentials.append({"username": name, "password": password, "role": role.value})
    fixture = json.loads(
        (ROOT / "tests/fixtures/pilot/fractions_course.json").read_text()
    )
    with get_db_service().get_session() as db:
        plan = StudyPlan(
            title=fixture["title"],
            description=fixture["audience"],
            creator_id=accounts["teacher_a"]["id"],
            phases=[{"name": "Study and practice", "content_ids": []}],
            is_public=False,
        )
        plan.set_encrypted_metadata(
            {
                "workflow": {"status": "draft", "version": 0},
                "synthetic_scenario": fixture["scenario"],
            }
        )
        db.add(plan)
        db.flush()
        ids = []
        for index, data in enumerate(fixture["lessons"]):
            content = Content(
                title=data["title"],
                creator_id=accounts["teacher_a"]["id"],
                study_plan_id=plan.id,
                content_type=ContentType.LESSON,
            )
            content.set_encrypted_content_data(normalize_content("lesson", data))
            db.add(content)
            db.flush()
            ids.append(content.id)
            db.add(
                StudyPlanContent(
                    study_plan_id=plan.id,
                    content_id=content.id,
                    phase_index=0,
                    order_index=index,
                )
            )
        plan.phases = [{"name": "Study and practice", "content_ids": ids}]
        assessment = Assessment(
            title="Synthetic reviewed feedback practice",
            created_by_id=accounts["teacher_a"]["id"],
            study_plan_id=plan.id,
            is_published=False,
            grading_mode=GradingMode.MANUAL,
            total_points=10,
        )
        db.add(assessment)
        db.flush()
        question = AssessmentQuestion(
            assessment_id=assessment.id,
            question_text="Compare 3/8 and 5/8 and explain why. / Compara 3/8 y 5/8 y explica por qué.",
            question_type=QuestionType.SHORT_ANSWER,
            points=10,
            order_index=0,
        )
        question.set_encrypted_correct_answer(
            "5/8 is larger: both are equal eighths of the same whole and five exceeds three."
        )
        db.add(question)
        db.commit()
        return {
            "scenario": fixture["scenario"],
            "database": str(database),
            "plan_id": plan.id,
            "assessment_id": assessment.id,
            "credentials": credentials,
            "next": "Sign in as teacher_a; inspect lessons, review/publish/assign the course to learner_a, then publish the assessment. Credentials printed once; keep output private.",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(seed_pilot(args.database), indent=2))
        return 0
    except (ValueError, RuntimeError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
