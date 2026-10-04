"""Synthetic course portability and create-only encrypted recovery regressions."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.dependencies import get_db
from src.api.routes import portability
from src.api.security import get_current_user
from src.core.models import (
    Assessment, Book, Content, ContentType, GradingMode, Question, QuestionType,
    Rubric, RubricCriterion, StudyPlan, StudyPlanContent, User, UserRole,
)
from src.core.models.models import ENCRYPTION_KEY
from src.core.services.portability_service import export_course, import_course, preview_package
from src.core.services.recovery_service import create_backup, restore_backup, upgrade_database
from src.core.services.schema_migrations import REVISION, reconcile_database


@pytest.fixture
def course(db_session):
    users = []
    for name, role in (("author", UserRole.TEACHER), ("recipient", UserRole.TEACHER),
                       ("reader", UserRole.STUDENT), ("administrator", UserRole.ADMIN)):
        user = User(username=name, email=f"{name}@example.invalid", first_name=name, last_name="Synthetic",
                    role=role, password_hash="SYNTHETIC-ACCOUNT-DO-NOT-EXPORT")
        db_session.add(user)
        users.append(user)
    db_session.flush()
    author, recipient, reader, administrator = users
    reader.teacher_id = author.id
    plan = StudyPlan(title="Portable course", description="Synthetic", creator_id=author.id, is_public=True)
    db_session.add(plan)
    db_session.flush()
    lesson = Content(title="Lesson", content_type=ContentType.LESSON, creator_id=author.id, study_plan_id=plan.id)
    lesson.set_encrypted_content_data({"content": "Synthetic instructional text", "api_key": "SYNTHETIC-CONFIG-DO-NOT-EXPORT"})
    exercise = Content(title="Practice", content_type=ContentType.EXERCISE, creator_id=author.id, study_plan_id=plan.id)
    exercise.set_encrypted_content_data({"question": "Choose?", "answer": "SYNTHETIC-EXERCISE-KEY",
                                         "solution": "SYNTHETIC-SOLUTION", "options": {"A": "First", "correct_answer": "SYNTHETIC-OPTION-KEY"}})
    db_session.add_all([lesson, exercise])
    db_session.flush()
    exercise.difficulty_prerequisites = [lesson.id]
    exercise.remedial_for_content_id = lesson.id
    db_session.add_all([
        StudyPlanContent(study_plan_id=plan.id, content_id=lesson.id, phase_index=0, order_index=2),
        StudyPlanContent(study_plan_id=plan.id, content_id=exercise.id, phase_index=1, order_index=0, is_required=False),
    ])
    assessment = Assessment(title="Executable assessment", created_by_id=author.id, study_plan_id=plan.id,
                            topic_id=lesson.id, is_published=True, time_limit_minutes=20, max_attempts=2,
                            grading_mode=GradingMode.AI_ASSISTED, total_points=15)
    db_session.add(assessment)
    db_session.flush()
    one = Question(assessment_id=assessment.id, question_text="Choose", question_type=QuestionType.MULTIPLE_CHOICE,
                   points=5, order_index=1, options={"A": "First"})
    one.set_encrypted_correct_answer("SYNTHETIC-ASSESSMENT-KEY")
    two = Question(assessment_id=assessment.id, question_text="Explain", question_type=QuestionType.SHORT_ANSWER,
                   points=10, order_index=2)
    db_session.add_all([one, two])
    db_session.flush()
    for name, question_id in (("Assessment rubric", None), ("Question rubric", two.id)):
        rubric = Rubric(name=name, created_by_id=author.id, assessment_id=assessment.id,
                        question_id=question_id, total_points=10)
        db_session.add(rubric)
        db_session.flush()
        db_session.add(RubricCriterion(rubric_id=rubric.id, name="SYNTHETIC-RUBRIC-CRITERION", max_points=10, order_index=3))
    db_session.add(Book(study_plan_id=plan.id, title="Course book", chapters=[lesson.id, exercise.id]))
    plan.phases = [{"name": "Phase", "lessons": [{"id": lesson.id}, {"content_id": exercise.id}]}]
    plan.set_encrypted_metadata({"workflow": {"status": "published", "version": 7, "reviewed_by": author.id},
                                 "generation": {"items": [{"content_id": lesson.id, "status": "completed"}]}})
    db_session.commit()
    state = SimpleNamespace(db=db_session, author=author, recipient=recipient, reader=reader,
                            admin=administrator, plan=plan, lesson=lesson, exercise=exercise,
                            assessment=assessment, user=author)
    app = FastAPI()
    app.include_router(portability.router)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: state.user
    with TestClient(app) as client:
        state.client = client
        yield state


def test_audience_exports_do_not_leak_keys_or_student_records(course):
    learner = export_course(course.db, course.reader, course.plan, "learner")
    serialized = json.dumps(learner)
    for marker in ("SYNTHETIC-ASSESSMENT-KEY", "SYNTHETIC-EXERCISE-KEY", "SYNTHETIC-SOLUTION",
                   "SYNTHETIC-RUBRIC-CRITERION", "SYNTHETIC-OPTION-KEY", "SYNTHETIC-CONFIG-DO-NOT-EXPORT",
                   "SYNTHETIC-ACCOUNT-DO-NOT-EXPORT"):
        assert marker not in serialized
    assert "Synthetic instructional text" in serialized
    teacher = export_course(course.db, course.author, course.plan, "teacher")
    serialized = json.dumps(teacher)
    assert "SYNTHETIC-ASSESSMENT-KEY" in serialized and "SYNTHETIC-RUBRIC-CRITERION" in serialized
    assert "SYNTHETIC-CONFIG-DO-NOT-EXPORT" not in serialized and "SYNTHETIC-ACCOUNT-DO-NOT-EXPORT" not in serialized
    assert preview_package(teacher)["counts"] == {"contents": 2, "assessments": 1, "questions": 2, "books": 1}
    with pytest.raises(PermissionError):
        export_course(course.db, course.recipient, course.plan, "teacher")


def test_teacher_package_roundtrip_preserves_order_keys_rubrics_and_remaps_ids(course):
    package = export_course(course.db, course.author, course.plan, "teacher")
    imported = import_course(course.db, course.recipient, package)
    course.db.commit()
    assert imported.id != course.plan.id and imported.creator_id == course.recipient.id and not imported.is_public
    assert imported.decrypted_metadata["workflow"] == {"status": "draft", "version": 0}
    contents = course.db.query(Content).filter_by(study_plan_id=imported.id).order_by(Content.id).all()
    lesson, exercise = contents
    assert lesson.decrypted_content_data["content"] == "Synthetic instructional text"
    assert imported.phases[0]["content_ids"] == [lesson.id]
    assert imported.phases[1]["content_ids"] == [exercise.id]
    assert imported.decrypted_metadata["author_outline"][0]["lessons"][0]["id"] == lesson.id
    assert imported.decrypted_metadata["author_outline"][0]["lessons"][1]["content_id"] == exercise.id
    assert imported.decrypted_metadata["generation"]["items"][0]["content_id"] == lesson.id
    assert course.db.query(Book).filter_by(study_plan_id=imported.id).one().chapters == [lesson.id, exercise.id]
    assert exercise.difficulty_prerequisites == [lesson.id] and exercise.remedial_for_content_id == lesson.id
    links = course.db.query(StudyPlanContent).filter_by(study_plan_id=imported.id).order_by(StudyPlanContent.phase_index).all()
    assert [(item.phase_index, item.order_index, item.is_required) for item in links] == [(0, 2, True), (1, 0, False)]
    assessment = course.db.query(Assessment).filter_by(study_plan_id=imported.id).one()
    assert assessment.created_by_id == course.recipient.id and not assessment.is_published
    assert assessment.total_points == 15 and assessment.topic_id == lesson.id
    assert [item.order_index for item in assessment.questions] == [1, 2]
    assert assessment.questions[0].get_decrypted_correct_answer() == "SYNTHETIC-ASSESSMENT-KEY"
    assert len(assessment.rubrics) == 2
    assert next(item for item in assessment.rubrics if item.question_id).question_id == assessment.questions[1].id
    assert assessment.rubrics[0].criteria[0].order_index == 3


def test_import_rejects_invalid_references_atomically(course):
    package = export_course(course.db, course.author, course.plan, "teacher")
    package["contents"][0]["content_data"]["assessment_id"] = 999999
    before = course.db.query(StudyPlan).count(), course.db.query(Content).count()
    with pytest.raises(ValueError, match="outside"):
        import_course(course.db, course.recipient, package)
    course.db.commit()
    assert before == (course.db.query(StudyPlan).count(), course.db.query(Content).count())
    package = export_course(course.db, course.author, course.plan, "learner")
    with pytest.raises(ValueError, match="handouts"):
        import_course(course.db, course.recipient, package)


def test_export_and_import_preview_endpoints_scope_and_confirmation(course):
    base = f"/api/portability/plans/{course.plan.id}"
    preview = course.client.get(base + "/preview?audience=teacher")
    assert preview.status_code == 200 and "answer keys and rubrics" in preview.json()["includes"]
    download = course.client.get(base + "/export?audience=teacher")
    assert download.status_code == 200 and download.headers["cache-control"] == "no-store"
    package = download.json()
    course.user = course.reader
    assert course.client.get(base + "/export?audience=teacher").status_code == 403
    assert course.client.post("/api/portability/import/preview", json={"package": package}).status_code == 403
    course.user = course.recipient
    assert course.client.post("/api/portability/import/preview", json={"package": package}).status_code == 200
    assert course.client.post("/api/portability/import", json={"package": package}).status_code == 409
    created = course.client.post("/api/portability/import", json={"package": package, "confirm": True})
    assert created.status_code == 200 and created.json()["status"] == "draft"


def test_private_backup_roundtrip_key_checks_and_no_overwrite(course, tmp_path):
    source = Path(course.db.get_bind().url.database)
    original_rows = course.db.query(User).count()
    archive = create_backup(source, ENCRYPTION_KEY)
    assert ENCRYPTION_KEY not in archive and b"SYNTHETIC-ACCOUNT" not in archive
    destination = tmp_path / "restored.db"
    summary = restore_backup(archive, destination, ENCRYPTION_KEY)
    assert summary["row_counts"]["users"] == original_rows
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT password_hash FROM users LIMIT 1").fetchone()[0] == "SYNTHETIC-ACCOUNT-DO-NOT-EXPORT"
    preserved = destination.read_bytes()
    with pytest.raises(FileExistsError):
        restore_backup(archive, destination, ENCRYPTION_KEY)
    assert destination.read_bytes() == preserved
    with pytest.raises(ValueError, match="fingerprint"):
        restore_backup(archive, tmp_path / "wrong.db", Fernet.generate_key())
    assert not (tmp_path / "wrong.db").exists()
    with pytest.raises(ValueError, match="does not decrypt"):
        create_backup(source, Fernet.generate_key())
    damaged = json.loads(archive)
    damaged["database_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        restore_backup(json.dumps(damaged).encode(), tmp_path / "damaged.db", ENCRYPTION_KEY)
    assert not (tmp_path / "damaged.db").exists()


def test_private_backup_api_requires_admin_and_never_returns_key(course):
    assert course.client.get("/api/portability/backup/preview").status_code == 403
    course.user = course.admin
    preview = course.client.get("/api/portability/backup/preview")
    assert preview.status_code == 200 and "encryption key" in preview.json()["excludes"]
    assert ENCRYPTION_KEY.decode() not in preview.text
    assert course.client.post("/api/portability/backup", json={}).status_code == 409
    backup = course.client.post("/api/portability/backup", json={"confirm": True})
    assert backup.status_code == 200 and backup.json()["format"] == "slmeducator-private-backup"
    assert ENCRYPTION_KEY.decode() not in backup.text


def test_backup_captures_committed_wal(course, tmp_path):
    path = tmp_path / "wal.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE synthetic (value TEXT)")
        connection.execute("INSERT INTO synthetic VALUES ('committed-wal')")
        connection.commit()
        archive = create_backup(path, ENCRYPTION_KEY)
        destination = tmp_path / "wal-restored.db"
        restore_backup(archive, destination, ENCRYPTION_KEY)
        with sqlite3.connect(destination) as db:
            assert db.execute("SELECT value FROM synthetic").fetchone() == ("committed-wal",)
    finally:
        connection.close()


def test_upgrade_backs_up_and_reconciles_new_copy_only(course, tmp_path):
    archive = create_backup(Path(course.db.get_bind().url.database), ENCRYPTION_KEY)
    legacy = tmp_path / "legacy.db"
    restore_backup(archive, legacy, ENCRYPTION_KEY)
    with sqlite3.connect(legacy) as db:
        db.execute("ALTER TABLE users DROP COLUMN xp")
    before = sha256(legacy.read_bytes()).hexdigest()
    destination, backup = tmp_path / "upgraded.db", tmp_path / "before.slmbackup"
    result = upgrade_database(legacy, destination, backup, ENCRYPTION_KEY)
    assert result["changes"]["columns"] == {"users": ["xp"]}
    assert sha256(legacy.read_bytes()).hexdigest() == before
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT xp FROM users LIMIT 1").fetchone() == (0,)
        assert db.execute("SELECT password_hash FROM users LIMIT 1").fetchone() == ("SYNTHETIC-ACCOUNT-DO-NOT-EXPORT",)
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
    assert reconcile_database(destination) == {"tables": [], "columns": {}}
    with pytest.raises(FileExistsError):
        upgrade_database(legacy, destination, backup, ENCRYPTION_KEY)


def test_unknown_migration_revision_fails_without_relabeling(course, tmp_path):
    copy = tmp_path / "unknown.db"
    restore_backup(create_backup(Path(course.db.get_bind().url.database), ENCRYPTION_KEY), copy, ENCRYPTION_KEY)
    with sqlite3.connect(copy) as db:
        db.execute("CREATE TABLE alembic_version (version_num TEXT)")
        db.execute("INSERT INTO alembic_version VALUES ('unknown-future')")
    with pytest.raises(ValueError, match="Unknown"):
        reconcile_database(copy)
    with sqlite3.connect(copy) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("unknown-future",)


def test_cli_help_and_missing_key_do_not_create_home_key(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "recover_database.py"
    environment = dict(os.environ, HOME=str(tmp_path))
    environment.pop("SLM_ENCRYPTION_KEY", None)
    for args, expected in ((["--help"], 0), (["inspect", "--database", str(tmp_path / "absent.db")], 2)):
        result = subprocess.run([sys.executable, str(script), *args], env=environment, capture_output=True, text=True)
        assert result.returncode == expected, result.stderr
    assert not (tmp_path / ".slm_educator").exists()


def test_failure_after_import_writes_rolls_back_entire_course(course, monkeypatch):
    from src.core.services import portability_service
    package = export_course(course.db, course.author, course.plan, "teacher")
    before = course.db.query(StudyPlan).count(), course.db.query(Content).count(), course.db.query(Assessment).count()

    def fail(*args, **kwargs):
        raise ValueError("Synthetic failure after parent rows were inserted")

    monkeypatch.setattr(portability_service, "_import_questions", fail)
    with pytest.raises(ValueError, match="Synthetic failure"):
        import_course(course.db, course.recipient, package)
    course.db.commit()
    assert before == (course.db.query(StudyPlan).count(), course.db.query(Content).count(), course.db.query(Assessment).count())


def test_existing_incomplete_schema_requires_explicit_upgrade(course, tmp_path):
    from src.core.services.database import DatabaseService
    path = tmp_path / "incomplete.db"
    restore_backup(create_backup(Path(course.db.get_bind().url.database), ENCRYPTION_KEY), path, ENCRYPTION_KEY)
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE users DROP COLUMN xp")
    with pytest.raises(RuntimeError, match="explicit upgrade"):
        DatabaseService(str(path))
    with sqlite3.connect(path) as db:
        assert "xp" not in {column[1] for column in db.execute("PRAGMA table_info(users)")}
        assert db.execute("SELECT password_hash FROM users LIMIT 1").fetchone() == ("SYNTHETIC-ACCOUNT-DO-NOT-EXPORT",)


def test_unreadable_course_crypto_is_not_silently_exported(course):
    course.lesson.content_data = Fernet(Fernet.generate_key()).encrypt(b'{"content":"private"}').decode()
    course.db.commit()
    with pytest.raises(ValueError, match="decrypt"):
        export_course(course.db, course.author, course.plan, "teacher")
