"""The opt-in evaluator must write configuration only in its new state."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

def test_new_provider_state_does_not_change_fallback_configuration(tmp_path: Path) -> None:
    """Start real synthetic bootstrap beside an unrelated synthetic config."""
    root = Path(__file__).resolve().parents[1]
    fallback = tmp_path / "env-test.properties"
    original = b"[ai]\ndefault_provider = unrelated-synthetic-provider\n"
    fallback.write_bytes(original)
    state = tmp_path / "new-provider-state"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with (tmp_path / "server-output.txt").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, str(root / "tests/browser/local_provider_server.py"),
             "--state-dir", str(state), "--port", str(port)],
            cwd=tmp_path,
            env={**os.environ, "SLM_OFFLINE_TESTS": "1", "USE_REAL_AI": "0"},
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                assert process.poll() is None, "Synthetic server exited"
                if (state / "fixture.json").is_file():
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Synthetic bootstrap did not complete")
            assert (state / "fixture.json").is_file()
            assert (state / "env.properties").is_file()
            assert fallback.read_bytes() == original
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
