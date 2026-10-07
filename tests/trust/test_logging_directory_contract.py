"""Exercise real logging handlers in disposable, process-isolated directories."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("selection", ["absolute", "relative", "unset", "empty"])
def test_logging_uses_selected_directory_without_checkout_writes(
    tmp_path: Path, selection: str
) -> None:
    """Honor explicit destinations and keep the absent/empty default at logs/."""
    work = tmp_path / "disposable-working-directory"
    work.mkdir()
    if selection == "absolute":
        configured = str(tmp_path / "new-parent" / "selected-logs")
    elif selection == "relative":
        configured = "new-parent/selected-logs"
    else:
        configured = ""
    expected = Path(configured) if configured else Path("logs")
    if not expected.is_absolute():
        expected = work / expected
    config = tmp_path / "synthetic.properties"
    config.write_text("[ai]\ndefault_provider = ollama\n", encoding="utf-8")
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "SLM_TEST_MODE": "1",
        "SLM_OFFLINE_TESTS": "1",
        "USE_REAL_AI": "0",
        "SLM_CONFIG_FILE": str(config),
        "SLM_DB_PATH": str(tmp_path / "synthetic.sqlite3"),
        "SLM_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "JWT_SECRET": "synthetic-logging-directory-contract-only",
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
    }
    if selection == "unset":
        environment.pop("SLM_LOG_DIR", None)
    else:
        environment["SLM_LOG_DIR"] = configured
    runner = textwrap.dedent("""
        import json
        import logging
        from pathlib import Path
        import sys

        from src.core.services.logging import LoggingService

        expected = Path(sys.argv[1])
        service = LoggingService()
        assert service.log_dir.resolve() == expected
        handlers = [handler for handler in logging.getLogger().handlers
                    if isinstance(handler, logging.FileHandler)]
        assert {Path(handler.baseFilename) for handler in handlers} == {
            expected / 'slm_educator.log', expected / 'errors.log',
        }
        service.log_event('synthetic-directory-contract', 'INFO', 'synthetic.info')
        service.log_error('synthetic-warning', 'Synthetic error for path coverage')
        logging.shutdown()
        main = [json.loads(line) for line in
                (expected / 'slm_educator.log').read_text().splitlines()]
        errors = [json.loads(line) for line in
                  (expected / 'errors.log').read_text().splitlines()]
        assert [row['event_type'] for row in main] == [
            'synthetic.info', 'error.synthetic-warning',
        ]
        assert [row['event_type'] for row in errors] == ['error.synthetic-warning']
        assert all(row['timestamp'].endswith(('Z', '+00:00')) for row in main)
        assert {path.resolve() for path in Path.cwd().rglob('*.log')} == (
            {expected / 'slm_educator.log', expected / 'errors.log'}
            if expected.is_relative_to(Path.cwd()) else set()
        )
        if expected != Path.cwd() / 'logs':
            assert not (Path.cwd() / 'logs').exists()
        assert not (Path.cwd() / 'slm_educator.db').exists()
        print('LOGGING_DIRECTORY_VERIFIED')
    """)
    result = subprocess.run(
        [sys.executable, "-c", runner, str(expected)],
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "LOGGING_DIRECTORY_VERIFIED" in result.stdout
    assert expected.is_dir()
