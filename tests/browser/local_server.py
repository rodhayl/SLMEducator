"""Disposable loopback-only application for explicit browser acceptance.

Only synthetic fixtures and a deterministic provider stub are used. This is not
an application launcher or evidence of real-model quality.
"""

import argparse
import io
import json
import os
import re
import secrets
import sys
from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


LEGACY_WORKER_SHA256 = (
    "bde3cdc01eb53a6ff7c2060b98812c9fea0a932f48b44151255d0ca5ea487809"
)


def install_worker_fixture(app, directory: Path) -> None:
    """Stage the frozen real v22 script at /sw.js, then retire via production code.

    Only the opt-in worker suite uses this middleware. Old precache dependencies
    are inert synthetic resources, not a legacy GUI fallback. The test changes a
    private file in its own synthetic directory to simulate installing new bytes.
    """
    from fastapi.responses import Response

    from src.frontend_delivery import RETIREMENT_WORKER

    worker = (ROOT / "tests/browser/fixtures/service_worker_v22.js").read_bytes()
    if sha256(worker).hexdigest() != LEGACY_WORKER_SHA256:
        raise RuntimeError("Archived v22 worker bytes changed")
    text = worker.decode("utf-8-sig")
    assets = set(
        re.findall(
            r"'([^']+)'", text.split("const STATIC_ASSETS = [", 1)[1].split("];", 1)[0]
        )
    )
    assets -= {"/", "/login.html", "/dashboard.html"}
    marker = directory / "serve-retirement-worker"

    @app.middleware("http")
    async def worker_transition(request, call_next):
        legacy = not marker.exists()
        if request.url.path == "/sw.js":
            return Response(
                worker if legacy else RETIREMENT_WORKER,
                media_type="application/javascript",
                headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-store"},
            )
        if legacy and request.url.path in assets:
            return Response(
                "/* Inert synthetic previous-installation resource. */",
                media_type="text/plain",
                headers={"Cache-Control": "no-store"},
            )
        return await call_next(request)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--legacy-worker-fixture", action="store_true")
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / "synthetic.db"
    if database.exists():
        raise SystemExit("Browser acceptance requires a new synthetic database")

    from cryptography.fernet import Fernet

    # Never inherit private configuration or another frontend/database override.
    config = directory / "synthetic.properties"
    config.write_text(
        (ROOT / "env-test.properties").read_text(encoding="utf-8"), encoding="utf-8"
    )

    admin_password = secrets.token_urlsafe(24) + "A1!"
    os.environ.update(
        SLM_TEST_MODE="1",
        SLM_DB_PATH=str(database),
        SLM_CONFIG_FILE=str(config),
        SLM_FRONTEND_DIR=str(ROOT / "src/frontend/dist"),
        SLM_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        JWT_SECRET=secrets.token_urlsafe(48),
        SLM_INITIAL_ADMIN_PASSWORD=admin_password,
        SLM_LOG_DIR=str(directory / "logs"),
    )
    from scripts.seed_pilot import seed_pilot

    with redirect_stdout(io.StringIO()):
        manifest = seed_pilot(database)
    manifest["credentials"].append(
        {"username": "admin", "password": admin_password, "role": "admin"}
    )

    from src.core.models import Content, StudyPlanContent, User
    from src.core.services.database import get_db_service

    with get_db_service().get_session() as db:
        manifest["users"] = {user.username: user.id for user in db.query(User)}
        manifest["content_ids"] = [
            row.content_id
            for row in db.query(StudyPlanContent)
            .filter_by(study_plan_id=manifest["plan_id"])
            .order_by(StudyPlanContent.order_index)
        ]
        manifest["lesson_titles"] = [
            db.get(Content, ident).title for ident in manifest["content_ids"]
        ]

    # Prevent every outgoing provider transport, even if settings are edited.
    from unittest.mock import MagicMock

    from src.core.services.ai_service import AIProvider, AIResponse, AIService
    from src.core.services.temporal_service import utc_now

    def setup_client(service):
        service._client = MagicMock()
        service._client.post.side_effect = RuntimeError(
            "Real provider transport disabled in browser acceptance"
        )
        service._client.get.side_effect = RuntimeError(
            "Real model discovery disabled in browser acceptance"
        )

    def synthetic_response(service, prompt, **kwargs):
        # Explicit acceptance cases exercise the real parser/API/UI boundary.
        # Match only the final question, never previous conversation history.
        question = prompt.split("Student Question:", 1)[-1].splitlines()[0]
        content = json.dumps(
            {
                "explanation": "Synthetic browser-test hint: compare equal parts. This is not a real model answer."
            }
        )
        if "[acceptance:prose]" in question:
            content = "Synthetic prose: compare **equal parts**. <img src=x onerror=window.acceptanceUnsafe=1>"
        elif "[acceptance:structured]" in question:
            content = json.dumps(
                {
                    "answer": "Synthetic structured: compare **equal parts**. <script>window.acceptanceUnsafe=1</script>"
                }
            )
        elif "[acceptance:format]" in question:
            content = '{"answer": "unfinished'
        elif "[acceptance:provider]" in question:
            from src.core.exceptions import AIServiceError

            raise AIServiceError("Synthetic provider unavailable")
        return AIResponse(
            content=content,
            tokens_used=7,
            model="synthetic-browser-stub",
            provider=AIProvider.OLLAMA,
            response_time=0.01,
            timestamp=utc_now(),
        )

    AIService._setup_client = setup_client
    AIService._call_ai = synthetic_response
    path = directory / "fixture.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    path.chmod(0o600)
    import uvicorn

    from src.api.main import app

    if args.legacy_worker_fixture:
        install_worker_fixture(app, directory)

    uvicorn.run(
        "src.api.main:app", host="127.0.0.1", port=args.port, log_level="warning"
    )


if __name__ == "__main__":
    main()
