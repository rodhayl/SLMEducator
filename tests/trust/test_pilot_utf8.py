"""Pilot JSON keeps literal Unicode when the host's default text codec is ANSI."""

import json
from pathlib import Path
import secrets
import sqlite3

import pytest

from scripts import evaluate_pilot, seed_pilot

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("cp1252_text_locale")


def test_locale_fixture_changes_only_implicit_text_io(tmp_path):
    path = tmp_path / "utf8.txt"
    raw = "Recuperación • 中文".encode("utf-8")
    path.write_bytes(raw)
    assert path.read_bytes() == raw
    assert path.read_text(encoding="utf-8") == "Recuperación • 中文"
    assert path.read_text() != path.read_text(encoding="utf-8")


def test_pilot_seed_persists_exact_utf8_fixture_titles(tmp_path, monkeypatch, capsys):
    from src.core.services.database import get_db_service

    database = tmp_path / "synthetic-utf8.sqlite3"
    expected = json.loads(
        (ROOT / "tests/fixtures/pilot/fractions_course.json").read_text(encoding="utf-8")
    )
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", secrets.token_urlsafe(24) + "A1!")
    try:
        seed_pilot.seed_pilot(database)
        with sqlite3.connect(database) as connection:
            titles = [row[0] for row in connection.execute("SELECT title FROM contents ORDER BY id")]
        assert titles == [lesson["title"] for lesson in expected["lessons"]]
        assert "Recuperación" in titles[2]
    finally:
        get_db_service().close()
        capsys.readouterr()  # The generated bootstrap credential is never report evidence.


def test_evaluation_catalog_keeps_non_ascii_case_identity(tmp_path, monkeypatch):
    catalog = tmp_path / "docs/pilot/evaluation_cases.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps({"cases": [{"id": "comprensión"}]}, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(evaluate_pilot, "ROOT", tmp_path)
    report = evaluate_pilot.summarize(
        {"case_ratings": [{"case_id": "comprensión", "acceptable": True}]}
    )
    assert report["rated_cases"] == report["required_cases"] == 1
    assert report["decision"] == "awaiting_human_evidence"


def test_evaluation_cli_preserves_utf8_observation_values(tmp_path, monkeypatch, capsys):
    observations = tmp_path / "observación.json"
    observations.write_text(
        json.dumps({"evidence_mode": "evaluación sintética"}, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr("sys.argv", ["evaluate_pilot.py", str(observations)])
    assert evaluate_pilot.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["evidence_mode"] == "evaluación sintética"
    assert report["decision"] == "awaiting_human_evidence"
