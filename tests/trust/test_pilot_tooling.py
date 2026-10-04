"""Pilot tooling validates inputs and cannot promote mocked runs to efficacy."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from scripts.evaluate_pilot import summarize

ROOT = Path(__file__).parents[2]


def test_empty_and_mocked_evidence_never_pass_the_human_gate():
    record = json.loads((ROOT / "docs/pilot/observation_template.json").read_text())
    assert summarize(record)["decision"] == "awaiting_human_evidence"
    cases = json.loads((ROOT / "docs/pilot/evaluation_cases.json").read_text())["cases"]
    record.update(
        teacher_reviewed=True,
        evidence_mode="synthetic",
        case_ratings=[{"case_id": c["id"], "acceptable": True} for c in cases],
        tasks=[
            {
                "completed_without_rescue": True,
                "authoring_minutes": 2,
                "correction_minutes": 3,
            }
        ],
    )
    report = summarize(record)
    assert report["decision"] == "awaiting_human_evidence"
    assert report["median_authoring_including_correction_minutes"] == 5
    record["evidence_mode"] = "observed_human_pilot"
    assert summarize(record)["decision"] == "eligible_for_teacher_decision"
    record["incidents"]["false_save"] = 1
    assert summarize(record)["decision"] == "stop_and_repair"


def test_duplicate_or_unknown_cases_rejected():
    with pytest.raises(ValueError):
        summarize({"case_ratings": [{"case_id": "invented", "acceptable": True}]})
    with pytest.raises(ValueError):
        summarize(
            {"case_ratings": [{"case_id": "grounded_en", "acceptable": True}] * 2}
        )


def test_pilot_seed_is_new_only_and_has_exact_synthetic_scope(tmp_path):
    database = tmp_path / "pilot.db"
    env = dict(
        os.environ,
        SLM_DB_PATH=str(database),
        SLM_LOG_DIR=str(tmp_path / "logs"),
        JWT_SECRET="synthetic-only-pilot-token-signing-key-123456",
        SLM_INITIAL_ADMIN_PASSWORD="SyntheticPilotBootstrap123!",
    )
    command = [
        sys.executable,
        str(ROOT / "scripts/seed_pilot.py"),
        "--synthetic",
        "--database",
        str(database),
    ]
    first = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30
    )
    assert first.returncode == 0, first.stderr
    with sqlite3.connect(database) as db:
        assert (
            db.execute("SELECT count(*) FROM users WHERE role='TEACHER'").fetchone()[0]
            == 2
        )
        assert (
            db.execute("SELECT count(*) FROM users WHERE role='STUDENT'").fetchone()[0]
            == 2
        )
        assert db.execute("SELECT count(*) FROM contents").fetchone()[0] == 3
        assert db.execute("SELECT count(*) FROM student_study_plans").fetchone()[0] == 0
        assert db.execute("SELECT is_published FROM assessments").fetchone()[0] == 0
    before = database.read_bytes()
    again = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=10
    )
    assert again.returncode == 1
    assert database.read_bytes() == before
