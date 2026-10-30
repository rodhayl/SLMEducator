"""
E2E test fixtures - uses existing running server.

This conftest overrides autouse fixtures from root conftest to prevent
database initialization for E2E tests since they use the running server.
"""

import pytest
import requests


def is_server_running(port: int) -> bool:
    """Check if a server is already running on the given port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/api/status", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@pytest.fixture(scope="session")
def api_server_url():
    """Return URL of existing running server.

    E2E tests require a server already running on port 8080.
    """
    port = 8080
    if not is_server_running(port):
        pytest.skip(f"No server running on port {port}. Start with ./start.bat first.")

    return f"http://127.0.0.1:{port}"


@pytest.fixture
def index_page(page, api_server_url):
    """Go to the index page."""
    page.goto(api_server_url, wait_until="networkidle")
    return page


# Override autouse fixtures from root conftest to do nothing for E2E tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Null fixture - E2E tests use the running server's database."""
    yield


@pytest.fixture
def test_data_dir():
    """Null fixture - E2E tests don't need temp directories."""
    yield None


@pytest.fixture
def test_db_path():
    """Null fixture - E2E tests don't need their own DB."""
    yield None


@pytest.fixture
def test_log_dir():
    """Null fixture - E2E tests don't need log dir."""
    yield None
