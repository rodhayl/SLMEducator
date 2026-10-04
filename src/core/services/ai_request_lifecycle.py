"""Bounded single-process tutor requests with durable daily claims and honest cancellation."""

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from hashlib import sha256
import json
from threading import Lock
import time
from uuid import uuid4

from fastapi import HTTPException
from src.core.models import User
from .temporal_service import utc_now

DAILY_REQUEST_LIMIT = 100
REQUEST_TIMEOUT_SECONDS = 90
RECEIPT_TTL_SECONDS = 600


@dataclass
class RequestRecord:
    user_id: int
    request_id: str
    fingerprint: str
    loop: asyncio.AbstractEventLoop
    started: float = field(default_factory=time.monotonic)
    cancelled: bool = False
    provider_running: bool = False
    status: str = "running"
    provider: str = "unknown"
    model: str = "unknown"
    max_output_tokens: int = 1000
    tokens_used: int | None = None
    requests_used_today: int = 0
    result: dict | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


_LOCK = Lock()
_RECORDS: dict[tuple[int, str], RequestRecord] = {}
_ACTIVE: dict[int, str] = {}
CURRENT_REQUEST: ContextVar[RequestRecord | None] = ContextVar(
    "slm_ai_request", default=None
)


def begin(user_id: int, request_id: str | None, payload: dict) -> RequestRecord:
    identity = request_id or str(uuid4())
    fingerprint = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with _LOCK:
        now = time.monotonic()
        for key, old in list(_RECORDS.items()):
            if (
                not old.provider_running
                and old.status != "running"
                and now - old.started > RECEIPT_TTL_SECONDS
            ):
                del _RECORDS[key]
        previous = _RECORDS.get((user_id, identity))
        if previous:
            if previous.fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Request ID belongs to different input; start a new request explicitly",
                )
            if previous.result is not None:
                return previous
            raise HTTPException(
                status_code=409,
                detail="This request is still running or its result is unavailable; check usage before retrying",
            )
        if user_id in _ACTIVE:
            raise HTTPException(
                status_code=409,
                detail="One AI request is already active for this account",
            )
        if len(_RECORDS) >= 2000:
            finished = sorted(
                (
                    record
                    for record in _RECORDS.values()
                    if not record.provider_running and record.status != "running"
                ),
                key=lambda record: record.started,
            )
            if not finished:
                raise HTTPException(
                    status_code=429, detail="AI request capacity is busy; retry later"
                )
            del _RECORDS[(finished[0].user_id, finished[0].request_id)]
        record = RequestRecord(
            user_id, identity, fingerprint, asyncio.get_running_loop()
        )
        _RECORDS[(user_id, identity)] = record
        _ACTIVE[user_id] = identity
        return record


def claim_daily_usage(db, user_id: int, record: RequestRecord) -> None:
    """Commit the request claim before waiting on optional provider work."""
    db.query(User).filter_by(id=user_id).update(
        {User.xp: User.xp}, synchronize_session=False
    )
    user = db.get(User, user_id)
    db.refresh(user)
    settings = dict(user.settings or {})
    day = utc_now().date().isoformat()
    usage = dict(settings.get("ai_request_usage", {}))
    if usage.get("day_utc") != day:
        usage = {"day_utc": day, "started": 0, "request_ids": []}
    if record.request_id in usage["request_ids"]:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This request was already claimed; after restart its outcome is unknown. Start a new request explicitly if needed",
        )
    if usage["started"] >= DAILY_REQUEST_LIMIT:
        db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Daily AI request limit reached; lessons and teacher help remain available",
        )
    usage["started"] += 1
    usage["request_ids"] = [*usage["request_ids"], record.request_id]
    settings["ai_request_usage"] = usage
    user.settings = settings
    db.commit()
    record.requests_used_today = usage["started"]


def _release(record: RequestRecord) -> None:
    if not record.provider_running and record.status != "running":
        with _LOCK:
            if _ACTIVE.get(record.user_id) == record.request_id:
                del _ACTIVE[record.user_id]


async def invoke_provider(db, user, service, **kwargs):
    """Stop local delivery at timeout/cancel while retaining a busy provider slot."""
    record = CURRENT_REQUEST.get()
    if record is None:
        raise RuntimeError("AI requests require a lifecycle record")
    if record.cancelled:
        raise RuntimeError("AI request was cancelled before provider work")
    # A detached DTO prevents a slow provider from using the route's DB session.
    kwargs["user"] = {
        "id": user.id,
        "full_name": user.full_name,
        "grade_level": user.grade_level,
    }
    config = getattr(service, "config", None)
    for name in ("provider", "model"):
        value = getattr(config, name, None)
        if isinstance(value, str):
            setattr(record, name, value)
    cap = getattr(config, "max_tokens", None)
    record.max_output_tokens = min(1000, cap) if type(cap) is int and cap > 0 else 1000
    claim_daily_usage(db, user.id, record)
    record.provider_running = True

    def execute():
        try:
            result = service.provide_tutoring(**kwargs)
            count = getattr(
                getattr(service, "last_response", None), "tokens_used", None
            )
            record.tokens_used = count if type(count) is int and count > 0 else None
            return result
        finally:
            record.provider_running = False
            _release(record)

    future = asyncio.get_running_loop().run_in_executor(None, execute)
    cancelled = asyncio.create_task(record.cancel_event.wait())
    try:
        done, _ = await asyncio.wait(
            {future, cancelled},
            timeout=REQUEST_TIMEOUT_SECONDS,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if cancelled in done or record.cancelled:
            record.status = "cancelled"
            raise RuntimeError("AI request cancelled; provider work may continue")
        if future not in done:
            record.cancelled = True
            record.status = "timed_out"
            raise RuntimeError("AI request timed out; provider work may continue")
        return future.result()
    finally:
        cancelled.cancel()
        if not future.done():
            future.add_done_callback(
                lambda result: result.exception() if not result.cancelled() else None
            )


def receipt(record: RequestRecord) -> dict:
    return {
        "request_id": record.request_id,
        "status": record.status,
        "elapsed_seconds": round(time.monotonic() - record.started, 3),
        "provider": record.provider,
        "model": record.model,
        "tokens_used": record.tokens_used,
        "max_output_tokens": record.max_output_tokens,
        "requests_used_today": record.requests_used_today,
        "requests_limit_daily": DAILY_REQUEST_LIMIT,
        "provider_may_continue": record.provider_running,
        "cost_known": False,
    }


def finish(record: RequestRecord, result: dict | None = None) -> dict:
    if record.status == "running":
        record.status = (
            "completed"
            if result
            and result.get("status", "suggestion") == "suggestion"
            and result.get("success", True)
            else "failed"
        )
    if result is not None:
        if record.cancelled:
            result = {**result, "suggestions": None}
            if "response" in result:
                result.update(
                    response="AI request ended without a delivered answer. Provider work may continue; your question is preserved.",
                    status="unavailable",
                )
            else:
                result.update(
                    answer="AI request ended without a delivered answer. Provider work may continue; your question is preserved.",
                    success=False,
                )
        result["receipt"] = receipt(record)
        record.result = result
    _release(record)
    return result or {"receipt": receipt(record)}


def cancel(user_id: int, request_id: str) -> dict:
    record = _RECORDS.get((user_id, request_id))
    if not record:
        raise HTTPException(
            status_code=404, detail="Request receipt is unavailable for this account"
        )
    if record.status == "running":
        record.cancelled = True
        record.status = "cancelled"
        record.loop.call_soon_threadsafe(record.cancel_event.set)
    return receipt(record)


def usage(db, user_id: int) -> dict:
    saved = (db.get(User, user_id).settings or {}).get("ai_request_usage", {})
    count = (
        saved.get("started", 0)
        if saved.get("day_utc") == utc_now().date().isoformat()
        else 0
    )
    return {
        "active_request_id": _ACTIVE.get(user_id),
        "requests_used_today": count,
        "requests_limit_daily": DAILY_REQUEST_LIMIT,
        "concurrent_limit": 1,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
    }
