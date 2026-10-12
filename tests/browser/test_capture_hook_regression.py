"""Regression for SLM-AUTO-019: the inference capture hook must survive GETs.

A catalog request (GET /v1/models) carries an empty body. The hook used to
run ``json.loads`` on it unconditionally, raising inside the hook and turning
the product's 200 into a 500. The product transport was always correct.
"""

import json

import httpx

from tests.browser.local_provider_server import decode_captured_request


def test_empty_request_body_is_recorded_without_parse() -> None:
    request = httpx.Request("GET", "http://127.0.0.1:1234/v1/models")
    assert request.content == b""
    assert decode_captured_request(request) is None


def test_json_request_body_still_decodes() -> None:
    payload = {"model": "synthetic", "messages": []}
    request = httpx.Request(
        "POST",
        "http://127.0.0.1:1234/v1/chat/completions",
        json=payload,
    )
    assert decode_captured_request(request) == payload


def test_record_keeps_response_when_request_body_is_empty(tmp_path) -> None:
    from tests.browser.local_provider_server import append_captured_record

    request = httpx.Request("GET", "http://127.0.0.1:1234/v1/models")
    response = httpx.Response(
        200,
        json={"data": [{"id": "synthetic-model"}]},
        request=request,
    )
    target = tmp_path / "inference.jsonl"
    append_captured_record(target, response)
    record = json.loads(target.read_text(encoding="utf-8").strip())
    assert record["request"] is None
    assert record["status"] == 200
    assert record["response"]["data"] == [{"id": "synthetic-model"}]
