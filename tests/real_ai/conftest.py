"""
Real AI Test Suite Configuration
==================================

STRICT RULES:
1. NO MOCKS allowed - all tests use REAL AI/LLM services
2. NO FAKES allowed - actual API calls only
3. Tests will be SLOW - real network calls
4. Tests will COST tokens - actual AI usage

This conftest.py enforces real AI usage and prevents mocking.
"""

import pytest
import os
import sys
from pathlib import Path
import httpx

# Add src to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Note: We set USE_REAL_AI in fixtures/hooks, not at module level,
# to avoid affecting tests outside this directory during collection.
os.environ["SLM_TEST_MODE"] = "1"

# Generate encryption key for tests
from cryptography.fernet import Fernet

if "SLM_ENCRYPTION_KEY" not in os.environ:
    os.environ["SLM_ENCRYPTION_KEY"] = Fernet.generate_key().decode()


def pytest_configure(config):
    """Configure pytest for real AI testing"""
    # Register markers properly
    config.addinivalue_line(
        "markers", "real_ai: marks tests as requiring real AI/LLM (slow, costs tokens)"
    )
    config.addinivalue_line("markers", "no_mock: marks tests that forbid mocking")
    config.addinivalue_line("markers", "slow: marks tests as slow running")

    use_real_ai = os.environ.get("USE_REAL_AI") == "1"

    # Display banner (ASCII only for Windows compatibility)
    print("\n" + "=" * 60)
    print("REAL AI TEST SUITE - STRICT MODE")
    print("=" * 60)
    print(
        f"[{'OK' if use_real_ai else '!'}] Real AI: {'ENABLED' if use_real_ai else 'DISABLED'}"
    )
    print(
        f"[{'X' if use_real_ai else 'OK'}] Mocks: {'FORBIDDEN' if use_real_ai else 'ALLOWED'}"
    )
    if use_real_ai:
        print("[!] WARNING: Tests will make actual API calls")
        print("[!] WARNING: Tests will consume AI tokens")
    else:
        print("[i] Set USE_REAL_AI=1 to enable real network AI calls")
    print("=" * 60 + "\n")


@pytest.fixture(scope="session")
def verify_real_ai_only():
    """Optional fixture to verify real AI usage"""
    import sys

    # Warn if mock modules detected (but don't fail - parent conftest may load them)
    mock_modules = [mod for mod in sys.modules.keys() if "mock" in mod.lower()]
    if mock_modules:
        print(f"\n[!] Warning: Mock modules detected: {mock_modules}")
        print("   These will not be used in real AI tests.\n")

    yield

    print("\n[OK] Real AI tests completed")


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in this directory as real_ai and no_mock"""
    use_real_ai = os.environ.get("USE_REAL_AI") == "1"
    for item in items:
        item_path = str(item.fspath).replace("\\", "/")
        if "/tests/real_ai/" not in item_path:
            continue
        item.add_marker(pytest.mark.real_ai)
        item.add_marker(pytest.mark.no_mock)
        item.add_marker(pytest.mark.slow)
        if not use_real_ai:
            item.add_marker(
                pytest.mark.skip(
                    reason="Real AI tests disabled. Set USE_REAL_AI=1 to run."
                )
            )


def _provider_reachable(provider: str, cfg: dict, api_key: str | None) -> bool:
    provider = (provider or "").lower()

    if provider == "lm_studio":
        endpoint = cfg.get("lm_studio_url") or "http://localhost:1234"
        try:
            r = httpx.get(f"{endpoint}/v1/models", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    if provider == "ollama":
        endpoint = cfg.get("ollama_url") or "http://localhost:11434"
        try:
            r = httpx.get(f"{endpoint}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    # Cloud providers need credentials at minimum.
    if provider in {"openrouter", "openai", "anthropic"}:
        return bool(api_key)

    return False


@pytest.fixture(scope="session")
def real_ai_config():
    """Get REAL AI configuration from settings"""
    if os.environ.get("USE_REAL_AI") != "1":
        pytest.skip("Real AI tests disabled. Set USE_REAL_AI=1 to run.")

    from core.services.settings_config_service import get_settings_service

    settings = get_settings_service()
    ai_config = settings.get_ai_config_defaults()

    # Validate configuration
    provider = ai_config.get("default_provider")
    model = ai_config.get("default_model")
    api_key = (
        ai_config.get("openrouter_api_key")
        if provider == "openrouter"
        else ai_config.get("api_key")
    )

    if not provider or not model:
        pytest.skip("Real AI configuration not found in env-test.properties")

    if not _provider_reachable(provider, ai_config, api_key):
        pytest.skip(f"Configured real AI provider is unavailable: {provider}")

    print(f"\n[AI] Using REAL AI: {provider}/{model}")

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "config": ai_config,
    }


@pytest.fixture
def real_ai_service(real_ai_config):
    """
    Create REAL AI service instance - NO MOCKS ALLOWED

    This fixture creates an actual AI service that will make real API calls.
    """
    from core.services.ai_service import AIService
    from core.models import AIModelConfig
    import logging

    config = AIModelConfig(
        provider=real_ai_config["provider"],
        model=real_ai_config["model"],
        api_key=real_ai_config["api_key"],
    )

    logger = logging.getLogger("RealAITest")
    logger.setLevel(logging.INFO)

    service = AIService(config, logger)

    # CRITICAL: Verify this is a real service, not a mock
    assert not hasattr(service, "_mock_name"), "[X] FORBIDDEN: AI service is a mock!"
    assert not hasattr(service, "return_value"), "[X] FORBIDDEN: AI service is a mock!"

    print(f"[OK] Real AI Service created: {config.provider}/{config.model}")

    yield service

    # Ensure HTTP clients are closed when tests complete
    try:
        service.close()
    except Exception:
        pass


@pytest.fixture
def db_service():
    """Create test database service"""
    from core.services.database import DatabaseService

    # Use in-memory database for speed
    db = DatabaseService(":memory:")
    yield db
    db.close()


@pytest.fixture
def test_user(db_service):
    """Create a real test user (not mocked)"""
    from core.models import User, UserRole
    from core.security import hash_password
    from datetime import datetime

    user = User(
        username=f"real_ai_test_user_{datetime.now().timestamp()}",
        password_hash=hash_password("testpass123"),
        email=f"realaitest_{datetime.now().timestamp()}@test.com",
        role=UserRole.STUDENT,
        first_name="RealAI",
        last_name="TestUser",
        grade_level="10",
    )

    created_user = db_service.create_user(user)
    yield created_user
