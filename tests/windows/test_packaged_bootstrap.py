"""Opt-in first login/password rotation/restart for a new synthetic prod package."""

from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time

import pytest
import requests

pytestmark = pytest.mark.skipif(
    os.name != "nt" or not os.environ.get("SLM_PACKAGED_INITIAL_PASSWORD"),
    reason="Requires an explicit newly built synthetic Windows package",
)


@contextmanager
def packaged_application(executable, directory, environment):
    """Start only the supplied package; clean up only its child process tree."""
    port = 8000
    while True:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                break
            except OSError:
                port += 1
                assert port <= 8100, "No isolated launcher port available"
    process = subprocess.Popen([str(executable), "--no-browser"], cwd=directory, env=environment)
    client = requests.Session()
    client.trust_env = False
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            assert process.poll() is None, "New package exited during startup"
            try:
                if client.get(url + "/api/status", timeout=0.5).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("New package failed to become ready")
        yield client, url
    finally:
        client.close()
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            process.wait(timeout=10)


def test_new_package_admin_login_rotation_and_restart(tmp_path):
    """Use the bundled database from another CWD with no source/venv on PATH."""
    executable = Path(os.environ["SLM_PACKAGED_EXE"]).resolve(strict=True)
    environment = {name: value for name, value in os.environ.items()
                   if name not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "SLM_DB_PATH",
                                   "SLM_TEST_MODE", "SLM_CONFIG_FILE", "SLM_INITIAL_ADMIN_PASSWORD",
                                   "SLM_PACKAGED_INITIAL_PASSWORD"}}
    environment["PATH"] = os.environ["SYSTEMROOT"] + "/System32"
    environment["SLM_LOG_DIR"] = str(tmp_path / "logs")
    initial = os.environ["SLM_PACKAGED_INITIAL_PASSWORD"]
    rotated = secrets.token_urlsafe(24) + "A1!"
    with packaged_application(executable, tmp_path, environment) as (client, url):
        response = client.post(url + "/api/auth/login", data={"username": "admin", "password": initial}, timeout=10)
        assert response.status_code == 200, "Bundled initial admin login failed"
        token = response.json()["access_token"]
        changed = client.post(url + "/api/auth/change-password",
                              headers={"Authorization": "Bearer " + token},
                              json={"current_password": initial, "new_password": rotated}, timeout=10)
        assert changed.status_code == 200, "Package password rotation failed"
    with packaged_application(executable, tmp_path, environment) as (client, url):
        old = client.post(url + "/api/auth/login", data={"username": "admin", "password": initial}, timeout=10)
        assert old.status_code == 401, "Restart restored the initial password"
        current = client.post(url + "/api/auth/login", data={"username": "admin", "password": rotated}, timeout=10)
        assert current.status_code == 200, "Restart lost the changed password"
        revoked = client.get(url + "/api/auth/me", headers={"Authorization": "Bearer " + token}, timeout=10)
        assert revoked.status_code == 401, "Password rotation failed to revoke the old token"
