"""Disposable loopback-only application for explicit browser acceptance.

Only synthetic fixtures and a deterministic provider stub are used. This is not
an application launcher or evidence of real-model quality.
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
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / "synthetic.db"
    if database.exists():
        raise SystemExit("Browser acceptance requires a new synthetic database")

    from cryptography.fernet import Fernet

    admin_password = secrets.token_urlsafe(24) + "A1!"
    os.environ.update(
        SLM_TEST_MODE="1",
        SLM_DB_PATH=str(database),
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

    from src.core.models import User, Content, StudyPlanContent
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
    from src.core.services.ai_service import AIService, AIResponse, AIProvider
    from src.core.services.temporal_service import utc_now
    from unittest.mock import MagicMock

    def setup_client(service):
        service._client = MagicMock()
        service._client.post.side_effect = RuntimeError(
            "Real provider transport disabled in browser acceptance"
        )
        service._client.get.side_effect = RuntimeError(
            "Real model discovery disabled in browser acceptance"
        )

    def synthetic_response(service, prompt, **kwargs):
        return AIResponse(
            content=json.dumps(
                {
                    "explanation": "Synthetic browser-test hint: compare equal parts. This is not a real model answer."
                }
            ),
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
    from fastapi.responses import Response
    from src.api.main import app

    sw_requests = 0

    @app.get("/acceptance-sw.js")
    def acceptance_worker():
        """Serve the actual previous worker once, then the candidate for update."""
        nonlocal sw_requests
        sw_requests += 1
        source = (ROOT / "tests/fixtures/service_worker_v14.js" if sw_requests == 1
                  else ROOT / "src/web/sw.js")
        return Response(source.read_text(encoding="utf-8-sig"), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-store"})

    uvicorn.run("src.api.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
