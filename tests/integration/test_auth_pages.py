from fastapi.testclient import TestClient
from src.api.main import app
import sys
import os

# Ensure src module is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

client = TestClient(app)


def test_auth_pages_served():
    # 1. Landing
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<title>SLM Educator</title>" in resp.text

    # 2. Login
    resp = client.get("/login.html")
    assert resp.status_code == 200
    assert 'id="login-form"' in resp.text

    # 3. Register
    resp = client.get("/register.html")
    assert resp.status_code == 200
    assert 'id="register-form"' in resp.text


def test_static_css_served():
    resp = client.get("/static/css/main.css")
    assert resp.status_code == 200
    assert ":root" in resp.text


def test_auth_api_endpoints():
    # 4. Invalid Login (should return 401)
    resp = client.post(
        "/api/auth/login",
        data={"username": "invalid_user", "password": "invalid_password"},
    )
    assert resp.status_code == 401


if __name__ == "__main__":
    try:
        print("Running Auth Page Tests...")
        test_auth_pages_served()
        print("✅ Pages Served")

        test_static_css_served()
        print("✅ CSS Served")

        test_auth_api_endpoints()
        print("✅ Auth API Handled")

    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback

        traceback.print_exc()
