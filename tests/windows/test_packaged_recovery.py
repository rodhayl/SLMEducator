"""Opt-in Windows frozen CLI and operational recovery; synthetic databases only."""

import json
import os
from pathlib import Path
import subprocess
import socket

import pytest

from tests.integration.test_operational_recovery import (
    APPLICATION_DRIVER, _installation, _json_output, _run, installation,
)

pytestmark = pytest.mark.skipif(
    os.name != "nt" or not os.environ.get("SLM_PACKAGED_EXE"),
    reason="Explicit native Windows package acceptance only",
)


def frozen(executable, environment, receipt, *arguments, expected=0):
    """Run the windowless package and read its explicit, create-only receipt."""
    clean = {name: value for name, value in environment.items()
             if name not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}}
    clean["PATH"] = os.environ["SYSTEMROOT"] + "/System32"
    result = subprocess.run([str(executable), "--recovery", "--result-file", str(receipt),
                             *map(str, arguments)], cwd=receipt.parent, env=clean, timeout=40)
    assert result.returncode == expected
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["success"] is (expected == 0)
    return data


def test_frozen_backup_restore_reopens_accounts_content_and_progress(installation):
    executable = Path(os.environ["SLM_PACKAGED_EXE"]).resolve(strict=True)
    run = installation
    backup = run.root / "frozen.slmbackup"
    frozen(executable, run.env, run.root / "backup-receipt.json",
           "backup", "--database", run.source, "--output", backup)
    environment = _installation(run.root / "Restauración limpia ñ", run.key)
    destination = Path(environment["SLM_DB_PATH"])
    restored = frozen(executable, environment, destination.parent / "restore-receipt.json",
                      "restore", "--backup", backup, "--output", destination)
    checked = frozen(executable, environment, destination.parent / "inspect-receipt.json",
                     "inspect", "--database", destination)
    assert checked["summary"] == restored["summary"]
    # Actual frozen GUI launcher/API with no Python/venv/source paths in its env.
    payload = {**run.payload, "executable": str(executable)}
    state = _json_output(_run(environment, "-c", APPLICATION_DRIVER, payload=payload))
    assert state["verified_accounts"] == ["admin", "learner_a", "learner_b", "teacher_a", "teacher_b"]
    # Repeat startup after the completed restoration; notes/history remain.
    payload["state"] = state
    payload["mode"] = "reopen-active"
    # An unrelated loopback listener must survive the launch and its cleanup.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupant:
        # Occupy the next port the launcher would select. An existing app on
        # 8000 is legitimate and must neither break this fixture nor be stopped.
        occupied_port = 8000
        while True:
            try:
                occupant.bind(("127.0.0.1", occupied_port))
                break
            except OSError:
                occupied_port += 1
                if occupied_port > 8100:
                    raise
        occupant.listen()
        restarted = _json_output(_run(environment, "-c", APPLICATION_DRIVER, payload=payload))
        assert occupant.getsockname() == ("127.0.0.1", occupied_port)
        with socket.create_connection(("127.0.0.1", occupied_port), timeout=2):
            pass
    assert restarted["session_id"] == state["session_id"]
    invalid = destination.parent / "invalid.slmbackup"
    invalid.write_text("[]", encoding="utf-8")
    rejected = destination.parent / "invalid.db"
    frozen(executable, environment, destination.parent / "invalid-receipt.json",
           "restore", "--backup", invalid, "--output", rejected, expected=1)
    assert not rejected.exists()
    frozen(executable, environment, destination.parent / "existing-receipt.json",
           "restore", "--backup", backup, "--output", destination, expected=1)
