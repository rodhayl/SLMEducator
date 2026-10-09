"""Real file handlers retain Unicode under a simulated Windows ANSI default."""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import textwrap

from cryptography.fernet import Fernet
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("entrypoint", ["service", "launcher"])
@pytest.mark.parametrize("default_codec", ["utf-8", "cp1252"])
def test_file_logging_preserves_unicode_with_explicit_utf8(
    tmp_path: Path, entrypoint: str, default_codec: str
) -> None:
    """Exercise both startup paths without creating a native window or server."""
    config = tmp_path / "synthetic.properties"
    config.write_text("[ai]\ndefault_provider=ollama\n", encoding="utf-8")
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "SLM_TEST_MODE": "1",
        "SLM_OFFLINE_TESTS": "1",
        "USE_REAL_AI": "0",
        "SLM_CONFIG_FILE": str(config),
        "SLM_DB_PATH": str(tmp_path / "synthetic.sqlite3"),
        "SLM_LOG_DIR": str(tmp_path / "logs"),
        "SLM_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "JWT_SECRET": secrets.token_urlsafe(48),
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
    }
    runner = textwrap.dedent("""
        import logging
        from pathlib import Path
        import sys

        entrypoint, default_codec = sys.argv[1:]
        original_init = logging.FileHandler.__init__
        original_basic_config = logging.basicConfig

        def init_with_host_default(handler, filename, mode='a', encoding=None,
                                   delay=False, errors=None):
            if encoding in (None, 'locale'):
                encoding = default_codec
            original_init(handler, filename, mode=mode, encoding=encoding,
                          delay=delay, errors=errors)

        logging.FileHandler.__init__ = init_with_host_default

        # basicConfig resolves its own omitted encoding before FileHandler does.
        # Intercept both public boundaries so Python UTF-8 mode cannot mask a bug.
        def basic_config_with_host_default(**kwargs):
            if 'filename' in kwargs and kwargs.get('encoding') in (None, 'locale'):
                kwargs['encoding'] = default_codec
            original_basic_config(**kwargs)

        logging.basicConfig = basic_config_with_host_default
        messages = ['Synthetic Recuperación', 'Synthetic 中文']

        def emit_messages(*args, **kwargs):
            for message in messages:
                logging.warning(message)

        if entrypoint == 'service':
            from src.core.services.logging import LoggingService
            LoggingService()
            emit_messages()
            paths = [Path('logs/slm_educator.log'), Path('logs/errors.log')]
        else:
            from src import starter
            starter.setup_frozen_working_directory = lambda: None
            starter.setup_frozen_logging = lambda: None
            starter.setup_frozen_modules = lambda: None
            starter.uvicorn.run = emit_messages
            starter.run_server(65534)
            paths = [Path('api.log')]

        logging.shutdown()
        for path in paths:
            content = path.read_text(encoding='utf-8')
            for message in messages:
                assert message in content, (path.name, message, content)
        print('UNICODE_LOGGING_VERIFIED')
    """)
    result = subprocess.run(
        [sys.executable, "-c", runner, entrypoint, default_codec],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert "UNICODE_LOGGING_VERIFIED" in result.stdout
