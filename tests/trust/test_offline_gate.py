"""The synthetic gate never discovers providers or uses a real HTTP transport."""

import os
from pathlib import Path

import httpx
import pytest
import requests

from tests.conftest import is_configured_ai_available, is_lm_studio_available


def test_offline_provider_discovery_never_connects(monkeypatch):
    monkeypatch.setenv("SLM_OFFLINE_TESTS", "1")

    def unexpected(*args, **kwargs):
        pytest.fail("Offline discovery tried an HTTP call")

    monkeypatch.setattr(httpx, "get", unexpected)
    assert not is_lm_studio_available()
    assert not is_configured_ai_available()


@pytest.mark.skipif(os.environ.get("SLM_OFFLINE_TESTS") != "1", reason="Offline gate only")
def test_offline_transports_fail_before_network():
    with httpx.Client(trust_env=False) as client:
        with pytest.raises(RuntimeError, match="SLM_OFFLINE_TESTS"):
            client.get("https://example.invalid/")
    with pytest.raises(RuntimeError, match="SLM_OFFLINE_TESTS"):
        requests.get("https://example.invalid/", timeout=1)


@pytest.mark.skipif(os.environ.get("SLM_OFFLINE_TESTS") != "1", reason="Offline gate only")
@pytest.mark.asyncio
async def test_offline_async_transport_fails_before_network():
    async with httpx.AsyncClient(trust_env=False) as client:
        with pytest.raises(RuntimeError, match="SLM_OFFLINE_TESTS"):
            await client.get("https://example.invalid/")


def test_ci_gate_keeps_external_acceptance_separate():
    root = Path(__file__).parents[2]
    workflow = (root / ".github/workflows/offline-tests.yml").read_text()
    for contract in (
        'SLM_OFFLINE_TESTS: "1"',
        'USE_REAL_AI: "0"',
        "contents: read",
        "persist-credentials: false",
        "npm ci --ignore-scripts",
        "--ignore=tests/manual --ignore=tests/real_ai",
        '-m "not real_ai"',
        "--basetemp=",
        "npm run check --prefix src/frontend",
        "cache-dependency-path: src/frontend/package-lock.json",
    ):
        assert contract in workflow
    assert "pull_request_target" not in workflow
