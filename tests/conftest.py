"""
Test configuration and setup for SLMEducator
"""

import pytest
import os
import sys
from pathlib import Path
import tempfile
import shutil
import weakref
from unittest.mock import MagicMock

# Add this repo's `src/` to path for imports (and prevent leakage from other repos)
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

# Remove any conflicting paths and add our src path first
conflicting_paths = [p for p in sys.path if "AAC_ASSISTANT" in p]
for path in conflicting_paths:
    sys.path.remove(path)
sys.path.insert(0, str(src_path))

# Set test environment variables
os.environ["SLM_TEST_MODE"] = "1"
# Generate a valid Fernet key for testing
from cryptography.fernet import Fernet

os.environ["SLM_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

# Reset settings service to ensure it loads env-test.properties
from core.services.settings_config_service import (
    reset_settings_service,
    get_settings_service,
)

reset_settings_service()


# ============= LM Studio / AI Provider Utilities =============


def is_lm_studio_available():
    """Check if LM Studio is running and accessible at the configured endpoint."""
    import httpx

    try:
        settings = get_settings_service()
        lm_studio_url = settings.get("ai", "lm_studio.url", "http://localhost:1234")
        # LM Studio uses OpenAI-compatible API
        response = httpx.get(f"{lm_studio_url}/v1/models", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            return "data" in data and len(data.get("data", [])) > 0
        return False
    except Exception:
        return False


def get_configured_ai_model():
    """Get the AI model configured in env-test.properties."""
    settings = get_settings_service()
    return settings.get("ai", "default_model", "gpt-oss-12b-i1")


def get_configured_ai_provider():
    """Get the AI provider configured in env-test.properties."""
    settings = get_settings_service()
    return settings.get("ai", "default_provider", "lm_studio")


def is_configured_ai_available():
    """Check if the configured AI provider is available."""
    provider = get_configured_ai_provider()
    if provider == "lm_studio":
        return is_lm_studio_available()
    elif provider == "ollama":
        import httpx

        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            return response.status_code == 200 and bool(
                response.json().get("models", [])
            )
        except Exception:
            return False
    else:
        # For cloud providers, assume available (will fail with auth errors if not)
        return True


@pytest.fixture(scope="function")
def test_data_dir():
    """Create a temporary test data directory"""
    temp_dir = tempfile.mkdtemp(prefix="slmeducator_test_")
    yield Path(temp_dir)

    # Windows file handle cleanup
    # First, dispose any database connections
    try:
        from core.services.database import get_db_service

        db = get_db_service()
        if hasattr(db, "engine") and db.engine:
            db.engine.dispose()
    except Exception:
        pass

    # Use gc and retry logic for Windows file locking
    import gc

    gc.collect()
    import time

    for i in range(10):  # Increased retries
        try:
            shutil.rmtree(temp_dir)
            break
        except PermissionError:
            time.sleep(0.2)  # Slightly longer wait
            gc.collect()
        except Exception:
            break  # Non-permission errors, stop trying


@pytest.fixture
def test_db_path(test_data_dir):
    """Create a test database path"""
    return test_data_dir / "test.db"


@pytest.fixture
def test_log_dir(test_data_dir):
    """Create a test logs directory"""
    log_dir = test_data_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


@pytest.fixture(autouse=True)
def setup_test_env(test_db_path, test_log_dir):
    """Set up test environment"""
    # Set test database path
    os.environ["SLM_DB_PATH"] = str(test_db_path)
    os.environ["SLM_LOG_DIR"] = str(test_log_dir)

    # Import and initialize database service
    from core.services.database import init_db_service

    init_db_service(str(test_db_path))

    yield

    # Cleanup
    if "SLM_DB_PATH" in os.environ:
        del os.environ["SLM_DB_PATH"]
    if "SLM_LOG_DIR" in os.environ:
        del os.environ["SLM_LOG_DIR"]


# Keep a registry of AIService instances created during tests; will auto-close them
_tracked_services = weakref.WeakSet()


@pytest.fixture(autouse=True)
def _track_and_patch_ai_services(monkeypatch, request):
    """Auto fixture to:
    - Track AIService instance creation and close instances created during the test
    - Patch AIService._setup_client for non-real AI tests to prevent accidental network calls
    """
    try:
        from core.services.ai_service import AIService
    except Exception:
        yield
        return

    # Wrap __init__ to register instances
    orig_init = AIService.__init__

    def _tracked_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        try:
            _tracked_services.add(self)
        except Exception:
            pass

    monkeypatch.setattr(AIService, "__init__", _tracked_init)

    # For non-real AI tests, ensure _setup_client uses a MagicMock to avoid HTTP calls
    use_real = False
    if os.environ.get("USE_REAL_AI") == "1":
        use_real = True
    else:
        # Check markers for real AI
        marker = request.node.get_closest_marker("real_ai")
        if marker:
            use_real = True
        # Also check if test is in the real_ai directory
        test_path = str(request.fspath)
        if "real_ai" in test_path:
            use_real = True

    if not use_real:

        def _fake_setup_client(self):
            self._client = MagicMock()

        monkeypatch.setattr(AIService, "_setup_client", _fake_setup_client)

    # Snapshot before test
    before = set(_tracked_services)
    yield

    # After test, close any newly created services
    after = set(_tracked_services) - before
    for svc in after:
        try:
            svc.close()
        except Exception:
            pass

    # As a fallback, try to close anything still tracked
    for svc in list(_tracked_services):
        try:
            svc.close()
        except Exception:
            pass


@pytest.fixture
def db_service(test_db_path):
    """Provide a database service for tests"""
    from core.services.database import get_db_service, init_db_service

    init_db_service(str(test_db_path))
    service = get_db_service()

    yield service

    # Close database service (disposes engine and closes open sessions)
    try:
        service.close()
    except Exception:
        pass


@pytest.fixture
def db_session(db_service):
    """SQLAlchemy session fixture expected by API-focused tests."""
    return db_service.session


@pytest.fixture
def client(db_service, monkeypatch):
    """FastAPI TestClient wired to the same test DB session."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api.dependencies import get_db

    def _override_get_db():
        yield db_service.session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_teacher(db_service):
    """Default teacher user for API tests (auth + classroom messaging)."""
    from core.models import User, UserRole
    from core.security import hash_password

    username = "api_test_teacher"
    existing = db_service.session.query(User).filter(User.username == username).first()
    if existing:
        return existing

    user = User(
        username=username,
        email="api_teacher@test.com",
        first_name="API",
        last_name="Teacher",
        role=UserRole.TEACHER,
        password_hash=hash_password("Password123!"),
    )
    db_service.session.add(user)
    db_service.session.commit()
    db_service.session.refresh(user)
    return user


@pytest.fixture
def test_student(db_service):
    """Default student user for API tests (auth + classroom messaging)."""
    from core.models import User, UserRole
    from core.security import hash_password

    username = "api_test_student"
    existing = db_service.session.query(User).filter(User.username == username).first()
    if existing:
        return existing

    user = User(
        username=username,
        email="api_student@test.com",
        first_name="API",
        last_name="Student",
        role=UserRole.STUDENT,
        password_hash=hash_password("Password123!"),
    )
    db_service.session.add(user)
    db_service.session.commit()
    db_service.session.refresh(user)
    return user


@pytest.fixture
def teacher_token(client, test_teacher):
    """Bearer token for the default teacher user."""
    resp = client.post(
        "/api/auth/login",
        data={"username": test_teacher.username, "password": "Password123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def student_token(client, test_student):
    """Bearer token for the default student user."""
    resp = client.post(
        "/api/auth/login",
        data={"username": test_student.username, "password": "Password123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# Configure pytest for headless Tkinter


def pytest_configure(config):
    """Configure pytest for headless operation"""
    os.environ["TKINTER_HEADLESS"] = "true"
    # Register custom markers used across tests
    config.addinivalue_line(
        "markers", "real_ai: marks tests as requiring real AI/LLM (slow, costs tokens)"
    )


def pytest_unconfigure(config):
    """Cleanup after tests"""
    if "TKINTER_HEADLESS" in os.environ:
        del os.environ["TKINTER_HEADLESS"]


# Centralized AI grading fixtures to eliminate duplication


@pytest.fixture
def mock_ai_service_success():
    """Create a mock AI service that returns successful grading"""
    from unittest.mock import Mock

    mock_service = Mock()
    mock_service.grade_answer.return_value = {
        "points_earned": 8,
        "max_points": 10,
        "percentage": 80,
        "feedback": "Good answer! You correctly identified the answer.",
        "explanation": "The answer was evaluated correctly.",
        "improvements": ["Consider adding more context"],
        "misconceptions": [],
        "strengths": ["Correct identification"],
    }
    return mock_service


@pytest.fixture
def mock_ai_service_partial():
    """Create a mock AI service that returns partial credit"""
    from unittest.mock import Mock

    mock_service = Mock()
    mock_service.grade_answer.return_value = {
        "points_earned": 4,
        "max_points": 10,
        "percentage": 40,
        "feedback": "Partially correct. You mentioned related information but not the exact answer.",
        "explanation": "The answer was partially correct.",
        "improvements": ["Focus on the specific question asked"],
        "misconceptions": ["Some confusion about the topic"],
        "strengths": ["Identified related concepts"],
    }
    return mock_service


@pytest.fixture
def mock_ai_service_error():
    """Create a mock AI service that raises exceptions"""
    from unittest.mock import Mock
    from core.services.ai_service import AIServiceError

    mock_service = Mock()
    mock_service.grade_answer.side_effect = AIServiceError("AI service unavailable")
    return mock_service


@pytest.fixture
def exercise_content_factory():
    """Factory for creating exercise content to eliminate duplication"""

    def _create_exercise_content(
        question_text, answer, question_type="short_answer", max_points=10
    ):
        from types import SimpleNamespace

        return SimpleNamespace(
            title="Test Exercise",
            content_data={
                "question": question_text,
                "answer": answer,
                "question_type": question_type,
                "max_points": max_points,
            },
        )

    return _create_exercise_content


@pytest.fixture
def patch_messagebox_and_ai():
    """Context manager to patch messagebox and AI service to eliminate duplication"""
    from unittest.mock import patch

    def _patch_messagebox_and_ai(mock_ai_service):
        return (
            patch("tkinter.messagebox.showinfo"),
            patch("tkinter.messagebox.showwarning"),
            patch("tkinter.messagebox.showerror"),
            patch(
                "core.services.ai_service.get_ai_service", return_value=mock_ai_service
            ),
        )

    return _patch_messagebox_and_ai


@pytest.fixture
def mock_user_data():
    """Standard mock user data to eliminate duplication"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "role": "teacher",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def mock_student_data():
    """Standard mock student data to eliminate duplication"""
    return {
        "id": 2,
        "username": "student1",
        "email": "student@example.com",
        "role": "student",
        "first_name": "Student",
        "last_name": "One",
    }


@pytest.fixture
def format_feedback():
    """Helper function to format feedback strings consistently"""

    def _format_feedback(points_earned, max_points, percentage=None):
        if percentage is None:
            percentage = int((points_earned / max_points) * 100)
        return f"Good answer! You scored {points_earned}/{max_points} points ({percentage}%)."

    return _format_feedback


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    from unittest.mock import Mock

    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def create_ai_response():
    """Factory fixture to create AIResponse objects consistently."""

    def _create_ai_response(
        content,
        tokens_used=50,
        model="gpt-3.5-turbo",
        provider="openrouter",
        response_time=1.0,
        **kwargs,
    ):
        from src.core.services.ai_service import AIResponse, AIProvider
        from datetime import datetime

        return AIResponse(
            content=content,
            tokens_used=tokens_used,
            model=model,
            provider=AIProvider(provider),
            response_time=response_time,
            timestamp=kwargs.get("timestamp", datetime.now()),
        )

    return _create_ai_response


@pytest.fixture
def format_grading_feedback():
    """Standardized feedback formatting for AI grading results"""

    def _format_grading_feedback(result, include_percentage=True):
        """Format AI grading result into user-friendly feedback string"""
        points = result.get("points_earned", 0)
        max_points = result.get("max_points", 10)
        percentage = result.get("percentage", 0)
        feedback = result.get("feedback", "")

        score_part = f"Score: {points}/{max_points} points"
        if include_percentage:
            score_part += f" ({percentage}%)"

        if feedback:
            return f"{score_part}. {feedback}"
        return score_part

    return _format_grading_feedback


@pytest.fixture
def create_grading_result():
    """Factory fixture to create standardized grading results"""

    def _create_grading_result(
        points_earned=8,
        max_points=10,
        percentage=80,
        feedback="Good answer! You correctly identified the key concepts.",
        explanation="The answer demonstrated understanding of the topic.",
        improvements=None,
        misconceptions=None,
        strengths=None,
    ):
        """Create a standardized grading result dictionary"""
        return {
            "points_earned": points_earned,
            "max_points": max_points,
            "percentage": percentage,
            "feedback": feedback,
            "explanation": explanation,
            "improvements": improvements or ["Consider adding more examples"],
            "misconceptions": misconceptions or [],
            "strengths": strengths or ["Correct identification of key points"],
        }

    return _create_grading_result


@pytest.fixture
def format_error_message():
    """Standardized error message formatting"""

    def _format_error_message(error_type, details=None):
        """Format error messages consistently across the application"""
        base_messages = {
            "ai_service_error": "AI service error occurred during grading",
            "network_error": "Network connection failed",
            "timeout_error": "Request timed out",
            "invalid_response": "Invalid response from AI service",
            "authentication_error": "Authentication failed",
        }

        message = base_messages.get(error_type, "Unknown error occurred")
        if details:
            message += f": {details}"
        return message

    return _format_error_message


@pytest.fixture
def create_test_exercise():
    """Factory fixture to create test exercises with consistent structure"""

    def _create_test_exercise(
        question="What is the capital of France?",
        correct_answer="Paris",
        question_type="short_answer",
        max_points=10,
        difficulty="medium",
        subject="Geography",
    ):
        """Create a standardized test exercise"""
        return {
            "question": question,
            "correct_answer": correct_answer,
            "question_type": question_type,
            "max_points": max_points,
            "difficulty": difficulty,
            "subject": subject,
        }

    return _create_test_exercise


# ============= Real AI Service Fixture (uses env-test.properties config) =============


@pytest.fixture(scope="class")
def test_ai_service():
    """
    Get a real AI service configured from env-test.properties.

    This fixture reads the provider and model from env-test.properties
    (default: LM Studio with gpt-oss-12b-i1) and creates
    a properly configured AIService instance.

    Skips if the configured AI provider is not available.
    """
    import logging
    from core.services.ai_service import AIService
    from core.models import AIModelConfiguration

    if not is_configured_ai_available():
        pytest.skip(
            f"Configured AI provider ({get_configured_ai_provider()}) is not available"
        )

    settings = get_settings_service()
    provider = get_configured_ai_provider()
    model = get_configured_ai_model()

    # Get endpoint based on provider
    if provider == "lm_studio":
        endpoint = settings.get("ai", "lm_studio.endpoint", "http://localhost:1234/v1")
    elif provider == "ollama":
        endpoint = settings.get("ai", "ollama.url", "http://localhost:11434")
    else:
        endpoint = settings.get("ai", f"{provider}.url", None)

    # Create a configuration object
    config = AIModelConfiguration(
        user_id=1,  # Dummy user ID for testing
        provider=provider,
        model=model,
        endpoint=endpoint,
    )

    logger = logging.getLogger("TestAIService")
    ai_service = AIService(config, logger)

    try:
        yield ai_service
    finally:
        try:
            ai_service.close()
        except Exception:
            pass
