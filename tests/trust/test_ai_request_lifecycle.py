"""Provider work is bounded, replay-safe and never confused with known cost."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

from src.api.routes import ai
from src.core.services import ai_request_lifecycle as lifecycle
from src.core.services.assistance_policy import set_assessment_policy
from src.core.services.temporal_service import utc_now
from tests.trust.test_assistance_policy import assessment_fixture
from tests.trust.test_resource_contracts import scenario, synthetic_credentials


def identity():
    return str(uuid4())


def test_same_request_replays_without_new_provider_work_or_usage(scenario):
    client, db, users, selected, plan, lessons, prompts = scenario
    selected[0] = users["learner_a"]
    selected[0].settings = {"timezone": "Europe/Madrid", "auth_version": 3}
    db.commit()
    payload = {
        "message": "Explain fractions",
        "content_id": lessons[0].id,
        "client_request_id": identity(),
    }
    first = client.post("/api/ai/chat", json=payload)
    second = client.post("/api/ai/chat", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() and len(prompts) == 1
    receipt = first.json()["receipt"]
    assert receipt["status"] == "completed" and not receipt["cost_known"]
    assert receipt["tokens_used"] is None and receipt["requests_used_today"] == 1
    assert client.get("/api/ai/usage").json()["requests_used_today"] == 1
    assert (
        selected[0].settings["timezone"] == "Europe/Madrid"
        and selected[0].settings["auth_version"] == 3
    )
    assert (
        client.post(
            "/api/ai/chat", json={**payload, "message": "Different request"}
        ).status_code
        == 409
    )
    assert len(prompts) == 1


def test_daily_claim_survives_receipt_loss_without_automatic_reinference(scenario):
    client, db, users, selected, _, _, prompts = scenario
    selected[0] = users["teacher_a"]
    request_id = identity()
    payload = {"question": "A question", "client_request_id": request_id}
    assert client.post("/api/ai/answer-question", json=payload).status_code == 200
    lifecycle._RECORDS.pop((selected[0].id, request_id))
    response = client.post("/api/ai/answer-question", json=payload)
    assert response.status_code == 409 and "unknown" in response.text
    assert len(prompts) == 1


def test_daily_limit_is_checked_before_provider_work(scenario):
    client, db, users, selected, _, _, prompts = scenario
    selected[0] = users["teacher_a"]
    selected[0].settings = {
        "ai_request_usage": {
            "day_utc": utc_now().date().isoformat(),
            "started": 100,
            "request_ids": [],
        }
    }
    db.commit()
    response = client.post(
        "/api/ai/chat", json={"message": "Explain", "client_request_id": identity()}
    )
    assert response.status_code == 429 and prompts == []
    assert client.get("/api/ai/usage").json()["active_request_id"] is None


def test_cached_response_cannot_cross_a_stricter_teacher_policy(scenario):
    client, db, users, selected, plan, _, prompts = scenario
    assessment = assessment_fixture(db, users, plan)
    set_assessment_policy(db, assessment, "explanations")
    db.commit()
    selected[0] = users["learner_a"]
    assert client.post(f"/api/assessments/{assessment.id}/start").status_code == 200
    payload = {"question": "Explain", "client_request_id": identity()}
    assert (
        client.post("/api/ai/answer-question", json=payload).json()[
            "effective_assistance"
        ]
        == "explanation"
    )
    set_assessment_policy(db, assessment, "hints_only")
    db.commit()
    assert client.post("/api/ai/answer-question", json=payload).status_code == 409
    assert len(prompts) == 1


def slow_service(monkeypatch):
    entered, release = Event(), Event()
    service = SimpleNamespace(
        config=SimpleNamespace(provider="ollama", model="synthetic", max_tokens=321),
        close=MagicMock(),
    )

    def provide(**kwargs):
        assert isinstance(
            kwargs["user"], dict
        )  # no DB-bound user reaches provider thread
        entered.set()
        if not release.wait(3):
            raise RuntimeError("Synthetic bounded provider release timed out")
        return {"explanation": "MUST_NOT_DELIVER_AFTER_CANCEL"}

    service.provide_tutoring = provide
    monkeypatch.setattr(ai, "get_ai_service_dependency", lambda *args: service)
    return service, entered, release


def wait_for_release(client):
    deadline = time.monotonic() + 1
    while (
        client.get("/api/ai/usage").json()["active_request_id"]
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert client.get("/api/ai/usage").json()["active_request_id"] is None


def test_cancel_is_private_suppresses_delivery_and_keeps_busy_provider_slot(
    scenario, monkeypatch
):
    client, db, users, selected, _, _, _ = scenario
    selected[0] = users["teacher_a"]
    service, entered, release = slow_service(monkeypatch)
    request_id = identity()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                client.post,
                "/api/ai/chat",
                json={"message": "Slow", "client_request_id": request_id},
            )
            assert entered.wait(2)
            assert (
                client.post(
                    "/api/ai/answer-question", json={"question": "Second"}
                ).status_code
                == 409
            )
            selected[0] = users["teacher_b"]
            assert (
                client.post(f"/api/ai/requests/{request_id}/cancel").status_code == 404
            )
            selected[0] = users["teacher_a"]
            cancelled = client.post(f"/api/ai/requests/{request_id}/cancel")
            assert cancelled.status_code == 200
            assert (
                cancelled.json()["status"] == "cancelled"
                and cancelled.json()["provider_may_continue"]
            )
            result = pending.result(timeout=2)
            assert (
                result.status_code == 200
                and result.json()["receipt"]["status"] == "cancelled"
            )
            assert "MUST_NOT_DELIVER_AFTER_CANCEL" not in result.text
            assert client.get("/api/ai/usage").json()["active_request_id"] == request_id
            assert (
                client.post("/api/ai/chat", json={"message": "Third"}).status_code
                == 409
            )
    finally:
        release.set()
    wait_for_release(client)
    service.close.assert_called_once()


def test_timeout_has_honest_receipt_and_no_unbounded_retry(scenario, monkeypatch):
    client, db, users, selected, _, _, _ = scenario
    selected[0] = users["teacher_a"]
    service, entered, release = slow_service(monkeypatch)
    monkeypatch.setattr(lifecycle, "REQUEST_TIMEOUT_SECONDS", 0.03)
    try:
        result = client.post(
            "/api/ai/chat", json={"message": "Slow", "client_request_id": identity()}
        )
        assert result.status_code == 200 and entered.is_set()
        assert result.json()["receipt"]["status"] == "timed_out"
        assert result.json()["receipt"]["provider_may_continue"]
        assert "MUST_NOT_DELIVER_AFTER_CANCEL" not in result.text
        assert client.post("/api/ai/chat", json={"message": "Retry"}).status_code == 409
    finally:
        release.set()
    wait_for_release(client)
