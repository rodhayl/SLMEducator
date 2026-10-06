"""New synthetic installation with actual provider transport and capture hooks.

This opt-in server never loads an existing database/configuration. Captures
contain only the fixed synthetic source prompts and model outputs, not logins.
"""

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    if directory.exists():
        raise SystemExit("Real-provider acceptance requires a NEW synthetic directory")
    directory.mkdir(parents=True)
    from cryptography.fernet import Fernet

    password = secrets.token_urlsafe(24) + "A1!"
    os.environ.update(
        SLM_TEST_MODE="1", SLM_DB_PATH=str(directory / "synthetic.db"),
        SLM_CONFIG_FILE=str(directory / "env.properties"),
        SLM_ENCRYPTION_KEY=Fernet.generate_key().decode(), JWT_SECRET=secrets.token_urlsafe(48),
        SLM_INITIAL_ADMIN_PASSWORD=password, SLM_LOG_DIR=str(directory / "logs"),
    )
    # Keep a recovery key separately from archives. Never publish this directory.
    (directory / "recovery.key").write_text(os.environ["SLM_ENCRYPTION_KEY"], encoding="utf-8")
    from src.core.services.settings_config_service import get_settings_service
    # The environment resolver accepts only existing overrides. Pass this new
    # path directly so first-run defaults cannot write a fallback configuration.
    settings = get_settings_service(str(directory / "env.properties"))
    settings.set("ai", "default_provider", "lm_studio")
    settings.set("ai", "default_model", "slm-production-evaluation")
    settings.set("ai", "lm_studio.url", "http://127.0.0.1:1234")
    from scripts.seed_pilot import seed_pilot
    with redirect_stdout(io.StringIO()):
        manifest = seed_pilot(directory / "synthetic.db")
    manifest["credentials"].append({"username": "admin", "password": password, "role": "admin"})
    (directory / "fixture.json").write_text(json.dumps(manifest), encoding="utf-8")

    from src.core.services.ai_service import AIService
    setup = AIService._setup_client

    def capture_setup(service):
        setup(service)

        def capture(response):
            response.read()
            if response.request.url.host != "127.0.0.1" or response.request.url.port != 1234:
                return
            record = {"request": json.loads(response.request.content),
                      "response": response.json(), "status": response.status_code}
            with (directory / "inference.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

        service._client.event_hooks["response"].append(capture)

    AIService._setup_client = capture_setup
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
