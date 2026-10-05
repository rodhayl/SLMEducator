"""Fresh-process, synthetic CLI recovery and real application reopen acceptance.

The application runs in Uvicorn with real loopback HTTP and authentication/
database services, without dependency overrides. This is not a browser, frozen
executable or Windows acceptance test. Every process has an isolated home,
configuration and working directory; no existing installation is selected.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
from typing import Iterator

from cryptography.fernet import Fernet
import pytest


ROOT = Path(__file__).resolve().parents[2]
RECOVERY = ROOT / "scripts" / "recover_database.py"
NOTE = "Synthetic recovery note: equal eighths describe the same whole."


class IsolatedEnvironment(dict[str, str]):
    """Keep generated keys out of pytest's argument diagnostics."""

    def __repr__(self) -> str:
        return "<isolated synthetic process environment>"


@dataclass
class SyntheticInstallation:
    """Describe disposable fixtures without printing generated credentials."""

    root: Path
    source: Path
    backup: Path
    key: bytes = field(repr=False)
    env: dict[str, str] = field(repr=False)
    payload: dict = field(repr=False)


# Run the real API in a *new interpreter*, so no pytest fixtures, service
# singletons, authentication overrides or encryption state cross installations.
APPLICATION_DRIVER = r'''
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import httpx

request = json.load(sys.stdin)
state = request["state"]

@contextmanager
def application():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [
            sys.executable, "-m", "uvicorn", "src.api.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ]
    server_environment = None
    if request.get("executable"):
        # The frozen launcher chooses its own first free loopback port.
        port = 8000
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.bind(("127.0.0.1", port))
                    break
                except OSError:
                    port += 1
        command = [request["executable"], "--no-browser"]
        import os
        server_environment = {name: value for name, value in os.environ.items()
                              if name not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}}
        server_environment["PATH"] = os.environ["SYSTEMROOT"] + "/System32"
    with Path("application.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(command, env=server_environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",
                              trust_env=False, timeout=10) as client:
                deadline = time.monotonic() + 40
                while time.monotonic() < deadline:
                    assert server.poll() is None, "Application process exited at startup"
                    try:
                        if client.get("/api/status").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                else:
                    raise AssertionError("Application did not start within 20 seconds")
                yield client
        finally:
            if server.poll() is None:
                if request.get("executable"):
                    subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    server.wait(timeout=10)
                else:
                    server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)

with application() as client:
    headers = {}
    identities = {}
    for account in request["credentials"]:
        login = client.post("/api/auth/login", data={
            "username": account["username"], "password": account["password"]})
        assert login.status_code == 200, "Original account login failed"
        headers[account["username"]] = {
            "Authorization": "Bearer " + login.json()["access_token"]}
        identities[account["username"]] = login.json()["user"]

    def api(method, path, user, expected=200, **kwargs):
        response = client.request(method, path, headers=headers[user], **kwargs)
        assert response.status_code == expected, (
            method, path, response.status_code, response.text)
        return response.json()

    for name in headers:
        assert api("GET", "/api/auth/me", name)["username"] == name

    plan = state["plan_id"]
    if request["mode"] == "prepare":
        state["source"] = api("PUT", f"/api/study-plans/{plan}/source", "teacher_a",
                              json={"filename": "synthetic.md", "extracted_text": "Equal eighths of the same whole can be compared by their numerators."})["source"]
        package = api("GET", f"/api/portability/plans/{plan}/export?audience=teacher", "teacher_a")
        imported = api("POST", "/api/portability/import", "teacher_b",
                       json={"package": package, "confirm": True})
        state["imported_plan"] = imported["study_plan_id"]
        assert imported["status"] == "draft"
        state["content_id"] = min(item["id"] for item in
            api("GET", "/api/content/", "teacher_a"))
        state["imported_content_id"] = min(item["id"] for item in
            api("GET", "/api/content/", "teacher_b"))
        for action, expected in (("review", "reviewed"), ("publish", "published")):
            result = api("POST", f"/api/study-plans/{plan}/workflow", "teacher_a",
                         json={"action": action})
            assert result["status"] == expected
        learner = identities["learner_a"]["id"]
        assignment = api("POST", f"/api/study-plans/{plan}/assign", "teacher_a",
                         json={"student_ids": [learner]})
        assert assignment["assigned_student_ids"] == [learner]
        session = api("POST", "/api/learning/start", "learner_a",
                      json={"content_id": state["content_id"], "study_plan_id": plan})
        state["session_id"] = session["id"]
        state["snapshot"] = session["content_snapshot"]
        state["revision"] = session["context_revision"]
        assert state["revision"]["provenance"] == "captured_at_start"
        assert state["snapshot"]["content_data"]["content"]
        ended = api("POST", f"/api/learning/{session['id']}/end", "learner_a",
                    json={"notes": request["note"], "difficulty_rating": 3})
        assert ended["status"] == "completed"
        assessment = api("GET", "/api/assessments/", "teacher_a")[0]
        assessment_id = assessment["id"]
        question = api("GET", f"/api/assessments/{assessment_id}", "teacher_a")["questions"][0]
        api("POST", f"/api/assessments/{assessment_id}/publish", "teacher_a")
        attempt = api("POST", f"/api/assessments/{assessment_id}/start", "learner_a")
        state["submission_id"] = attempt["submission_id"]
        pending = api("POST", f"/api/assessments/{assessment_id}/submit", "learner_a",
                      json={"submission_id": state["submission_id"],
                            "answers": [{"question_id": question["id"], "response_text": "Synthetic answer needs teacher correction."}]})
        assert pending["score"] is None
        api("POST", f"/api/assessments/submissions/{state['submission_id']}/grade", "teacher_a",
            json={"score": 0, "feedback": "Synthetic recovery feedback: compare equal eighths."})
    else:
        history = api("GET", f"/api/learning/history/{state['content_id']}", "learner_a")
        assert len(history) == 1 and history[0]["id"] == state["session_id"]
        assert history[0]["status"] == ("active" if request["mode"] == "reopen-active" else "completed")
        assert history[0]["notes"] == request["note"]
        assert history[0]["content_snapshot"] == state["snapshot"]
        assert history[0]["context_revision"] == state["revision"]
        for _ in range(2):
            reopened = api("POST", f"/api/learning/{state['session_id']}/restore", "learner_a")
            assert reopened["id"] == state["session_id"] and reopened["status"] == "active"
            assert reopened["notes"] == request["note"]
            assert reopened["content_snapshot"] == state["snapshot"]
            assert reopened["context_revision"] == state["revision"]

    source = api("GET", f"/api/content/{state['content_id']}", "teacher_a")
    grade = api("GET", f"/api/assessments/submissions/{state['submission_id']}", "learner_a")
    assert grade["score"] == 0 and grade["feedback"] == "Synthetic recovery feedback: compare equal eighths."
    api("GET", f"/api/assessments/submissions/{state['submission_id']}", "learner_b", expected=403)
    assert api("GET", f"/api/study-plans/{plan}/source", "teacher_a")["source"] == state["source"]
    api("GET", f"/api/study-plans/{plan}/source", "learner_a", expected=403)
    imported = api("GET", f"/api/content/{state['imported_content_id']}", "teacher_b")
    assert imported["content_data"] == source["content_data"]
    learner = api("GET", f"/api/content/{state['content_id']}", "learner_a")
    assert learner["content_data"] == state["snapshot"]["content_data"]
    api("GET", f"/api/content/{state['content_id']}", "learner_b", expected=403)
    imported_plan = state["imported_plan"]
    assert api("GET", f"/api/study-plans/{imported_plan}/workflow", "teacher_b")["status"] == "draft"
    package = api("GET", f"/api/portability/plans/{imported_plan}/export?audience=teacher", "teacher_b")
    assert len(package["assessments"]) == 1
    question = package["assessments"][0]["questions"][0]
    assert question["correct_answer"] == (
        "5/8 is larger: both are equal eighths of the same whole and five exceeds three.")
    state["verified_accounts"] = sorted(headers)
    print(json.dumps(state))
'''


def _installation(path: Path, key: bytes) -> dict[str, str]:
    """Build a minimum environment without inheriting private runtime overrides."""
    path.mkdir()
    home = path / "home"
    home.mkdir()
    config = path / "synthetic.properties"
    config.write_text("[ai]\ndefault_provider=ollama\n", encoding="utf-8")
    environment = IsolatedEnvironment({
        name: value for name, value in os.environ.items()
        if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    })
    environment.update(
        HOME=str(home), USERPROFILE=str(home), PYTHONPATH=str(ROOT),
        PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
        SLM_DB_PATH=str(path / "installation.db"), SLM_CONFIG_FILE=str(config),
        SLM_ENCRYPTION_KEY=key.decode(), JWT_SECRET=secrets.token_urlsafe(48),
        SLM_INITIAL_ADMIN_PASSWORD=secrets.token_urlsafe(24) + "A1!",
        SLM_OFFLINE_TESTS="1", USE_REAL_AI="0",
    )
    return environment


def _run(environment: dict[str, str], *arguments: str | Path, payload: dict | None = None,
         expected: int = 0) -> subprocess.CompletedProcess[str]:
    """Invoke a real process, keeping ephemeral credentials out of diagnostics."""
    result = subprocess.run(
        [sys.executable, *map(str, arguments)],
        cwd=Path(environment["SLM_DB_PATH"]).parent,
        env=environment, input=json.dumps(payload) if payload else None,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == expected, result.stderr
    return result


def _json_output(result: subprocess.CompletedProcess[str]) -> dict:
    """Read the final JSON object after the create-only seeder's status line."""
    return json.loads(result.stdout[result.stdout.find("{"):])


@contextmanager
def _readonly(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        yield connection
    finally:
        connection.close()


def _logical_digest(path: Path) -> str:
    """Compare schema and rows rather than SQLite-managed WAL read marks."""
    with _readonly(path) as connection:
        return sha256("\n".join(connection.iterdump()).encode()).hexdigest()


@pytest.fixture(scope="module")
def installation(tmp_path_factory):
    """Make one synthetic source, closing all application writers before backup."""
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.mktemp("operational")) as folder:
        root = Path(folder)
        key = Fernet.generate_key()
        environment = _installation(root / "source", key)
        source = Path(environment["SLM_DB_PATH"])
        seeded = _json_output(_run(
            environment, ROOT / "scripts" / "seed_pilot.py",
            "--database", source, "--synthetic",
        ))
        payload = {"mode": "prepare", "state": {"plan_id": seeded["plan_id"]},
                   "credentials": seeded["credentials"] + [
                       {"username": "admin", "password": environment["SLM_INITIAL_ADMIN_PASSWORD"]}
                   ], "note": NOTE}
        state = _json_output(_run(environment, "-c", APPLICATION_DRIVER, payload=payload))
        backup = root / "private.slmbackup"
        _run(environment, RECOVERY, "backup", "--database", source, "--output", backup)
        yield SyntheticInstallation(root=root, key=key, env=environment, source=source,
                                    backup=backup, payload={**payload, "mode": "reopen", "state": state})


def test_cli_restore_reopens_real_auth_imported_content_and_learning_session(installation):
    """A separately configured process reads and resumes the encrypted backup."""
    run = installation
    before = _logical_digest(run.source)
    environment = _installation(run.root / "second-installation", run.key)
    destination = Path(environment["SLM_DB_PATH"])
    assert environment["JWT_SECRET"] != run.env["JWT_SECRET"]
    source_summary = _json_output(_run(run.env, RECOVERY, "inspect", "--database", run.source))
    restored = _json_output(_run(environment, RECOVERY, "restore", "--backup", run.backup,
                                 "--output", destination))
    checked = _json_output(_run(environment, RECOVERY, "inspect", "--database", destination))
    assert checked == source_summary
    assert restored["summary"] == checked["summary"]
    assert _logical_digest(destination) == before
    archive = run.backup.read_bytes()
    for private in (run.key, run.env["JWT_SECRET"].encode(), NOTE.encode(),
                    run.payload["credentials"][0]["password"].encode()):
        assert private not in archive
    with _readonly(destination) as connection:
        for table, column in (("contents", "content_data"),
                              ("study_plans", "content_metadata"),
                              ("assessment_questions", "correct_answer"),
                              ("learning_sessions", "content_snapshot")):
            values = connection.execute(f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
            assert values and all(value[0].startswith("gAAAA") for value in values)
    reopened = _json_output(_run(environment, "-c", APPLICATION_DRIVER, payload=run.payload))
    assert reopened["verified_accounts"] == ["admin", "learner_a", "learner_b", "teacher_a", "teacher_b"]
    assert _logical_digest(run.source) == before
    assert not (Path(environment["HOME"]) / ".slm_educator").exists()
    assert not (Path(run.env["HOME"]) / ".slm_educator").exists()


def test_cli_wrong_key_and_existing_outputs_preserve_source_and_destination(installation):
    """Rejected keys and create-only paths cannot replace existing data."""
    run = installation
    before = _logical_digest(run.source)
    archive_bytes = run.backup.read_bytes()
    wrong = IsolatedEnvironment({**run.env, "SLM_ENCRYPTION_KEY": Fernet.generate_key().decode()})
    absent = run.root / "wrong-key.db"
    _run(wrong, RECOVERY, "restore", "--backup", run.backup, "--output", absent, expected=1)
    assert not absent.exists()
    _run(wrong, RECOVERY, "inspect", "--database", run.source, expected=1)
    _run(wrong, RECOVERY, "backup", "--database", run.source, "--output", absent, expected=1)
    assert not absent.exists()
    _run(run.env, RECOVERY, "restore", "--backup", run.backup, "--output", run.source, expected=1)
    _run(run.env, RECOVERY, "backup", "--database", run.source, "--output", run.backup, expected=1)
    assert _logical_digest(run.source) == before
    assert run.backup.read_bytes() == archive_bytes


def test_windowless_receipt_cannot_replace_backup_or_database(installation):
    run = installation
    archive = run.backup.read_bytes()
    before = _logical_digest(run.source)
    _run(run.env, RECOVERY, "--result-file", run.backup, "inspect", "--database", run.source, expected=2)
    missing = run.root / "absent.db"
    _run(run.env, RECOVERY, "--result-file", missing, "restore", "--backup", run.backup,
         "--output", missing, expected=2)
    assert not missing.exists()
    assert run.backup.read_bytes() == archive
    assert _logical_digest(run.source) == before


def test_interrupted_restore_can_retry_without_partial_destination(installation):
    """Kill a real restore process immediately before atomic final promotion."""
    import time

    run = installation
    destination = run.root / "interrupted-restore.db"
    signal = run.root / "promotion-ready"
    original = run.backup.read_bytes()
    driver = r'''
import os, sys, time
from pathlib import Path
from src.core.services.recovery_service import restore_backup
archive, destination, signal = map(Path, sys.argv[1:])
link = os.link
def pause_promotion(source, target, **kwargs):
    if Path(target) == destination:
        signal.write_text("ready")
        time.sleep(60)
    return link(source, target, **kwargs)
os.link = pause_promotion
restore_backup(archive.read_bytes(), destination, os.environ["SLM_ENCRYPTION_KEY"].encode())
'''
    process = subprocess.Popen([sys.executable, "-c", driver, str(run.backup),
                                str(destination), str(signal)], env=run.env, cwd=run.root,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 20
        while not signal.exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.05)
        assert signal.exists(), "Restore never reached final promotion"
        process.kill()
        process.wait(timeout=5)
        assert not destination.exists()
        assert run.backup.read_bytes() == original
        _run(run.env, RECOVERY, "restore", "--backup", run.backup, "--output", destination)
        _run(run.env, RECOVERY, "inspect", "--database", destination)
        assert destination.exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.parametrize("damage", ["ciphertext", "size", "digest", "manifest", "json", "root", "sqlite"])
def test_cli_corrupt_archives_fail_without_a_destination(installation, damage):
    """Even authenticated but invalid SQLite bytes are rejected before promotion."""
    run = installation
    before = _logical_digest(run.source)
    original = run.backup.read_bytes()
    archive = json.loads(original)
    if damage == "ciphertext":
        archive["database"] = "gAAAA-invalid-synthetic-ciphertext"
    elif damage == "size":
        archive["database_bytes"] += 1
    elif damage == "digest":
        archive["database_sha256"] = "0" * 64
    elif damage == "manifest":
        archive["summary"]["row_counts"]["users"] += 1
    elif damage == "sqlite":
        raw = b"Synthetic invalid database bytes"
        archive.update(database=Fernet(run.key).encrypt(raw).decode(),
                       database_bytes=len(raw), database_sha256=sha256(raw).hexdigest())
    serialized = json.dumps(archive).encode()
    if damage == "json":
        serialized = b"{invalid JSON"
    elif damage == "root":
        serialized = b"[]"
    damaged = run.root / f"damaged-{damage}.slmbackup"
    damaged.write_bytes(serialized)
    destination = run.root / f"rejected-{damage}.db"
    result = _run(run.env, RECOVERY, "restore", "--backup", damaged,
                  "--output", destination, expected=1)
    assert not destination.exists()
    assert _logical_digest(run.source) == before
    assert run.backup.read_bytes() == original
    assert damaged.read_bytes() == serialized
    assert "Recovery stopped:" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("command", ["backup", "inspect"])
def test_cli_corrupt_source_reports_failure_without_modifying_input(installation, command):
    """Unreadable SQLite fails cleanly for source-facing operational commands."""
    run = installation
    source = run.root / f"invalid-{command}.db"
    original = b"Synthetic invalid SQLite source"
    source.write_bytes(original)
    arguments = [RECOVERY, command, "--database", source]
    destination = run.root / "invalid-source.slmbackup"
    if command == "backup":
        arguments.extend(["--output", destination])
    result = _run(run.env, *arguments, expected=1)
    assert source.read_bytes() == original
    assert not destination.exists()
    assert "Recovery stopped:" in result.stderr
    assert "Traceback" not in result.stderr
