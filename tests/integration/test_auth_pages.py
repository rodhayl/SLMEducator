"""React delivery and authentication keep distinct, isolated contracts."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.frontend_delivery import register_frontend
from tests.fixtures.frontend_artifact import make_frontend
from tests.trust import test_resource_contracts as fixture_source

scenario = fixture_source.scenario
synthetic_credentials = fixture_source.synthetic_credentials


def test_auth_pages_use_verified_react_build_and_legacy_bridges(tmp_path):
    app = FastAPI()
    register_frontend(app, make_frontend(tmp_path))
    client = TestClient(app)
    for path in ("/", "/entrar", "/personas/nueva"):
        response = client.get(path)
        assert response.status_code == 200
        assert '<div id="root">' in response.text
        assert response.headers["cache-control"] == "no-cache"
    for old, current in (
        ("/login.html", "/entrar"),
        ("/register.html", "/personas/nueva"),
    ):
        response = client.get(old, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == current
        assert client.get(response.headers["location"]).status_code == 200
    for retired in ("/static/css/main.css", "/static/js/auth.js"):
        assert client.get(retired).status_code == 404


def test_invalid_login_still_rejected_against_synthetic_database(scenario):
    client, *_ = scenario
    response = client.post(
        "/api/auth/login",
        data={"username": "invalid_user", "password": "invalid_password"},
    )
    assert response.status_code == 401
