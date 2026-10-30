"""
E2E test for dashboard flow: login and navigation.
"""

import re
import uuid

import requests
from playwright.sync_api import expect, Page


def _register_user(base_url: str, username: str, role: str = "teacher"):
    """Register a new user for testing."""
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "User",
        "role": role,
    }
    resp = requests.post(f"{base_url}/api/auth/register", json=payload, timeout=10)
    # Allow 200 (created) or 400 (already exists)
    assert resp.status_code in [200, 400], f"Registration failed: {resp.text}"


def test_login_create_content_and_start_session(page: Page, api_server_url: str):
    """Test user login and navigation flow.

    Tests:
    1. Register/login a test user
    2. Verify dashboard loads
    3. Navigate to Library
    4. Navigate to Settings
    """
    username = f"e2e_{uuid.uuid4().hex[:8]}"
    _register_user(api_server_url, username)

    # Login
    page.goto(f"{api_server_url}/login.html", wait_until="networkidle")
    page.fill("#username", username)
    page.fill("#password", "Password123!")
    page.click("button[type='submit']")

    # Wait for dashboard to load
    page.wait_for_url(re.compile(r".*/dashboard.html"), timeout=15000)
    expect(page).to_have_url(re.compile(r".*/dashboard.html"))

    # Verify user is logged in - user display should show the name
    user_display = page.locator("#user-name-display")
    expect(user_display).to_be_visible(timeout=10000)

    # Navigate to Library
    library_nav = page.locator("[data-view='library']")
    expect(library_nav).to_be_visible(timeout=5000)
    library_nav.click()

    # Wait for library view to show
    library_section = page.locator("#library-section, #view-library")
    expect(library_section.first).to_be_visible(timeout=10000)

    # Navigate to Settings
    settings_nav = page.locator("[data-view='settings']")
    expect(settings_nav).to_be_visible(timeout=5000)
    settings_nav.click()

    # Wait for settings view to show
    settings_section = page.locator("#view-settings, #settings-section")
    expect(settings_section.first).to_be_visible(timeout=10000)

    # Navigate back to Overview
    overview_nav = page.locator("[data-view='overview']")
    expect(overview_nav).to_be_visible(timeout=5000)
    overview_nav.click()

    # Verify overview is back
    overview_section = page.locator("#view-overview")
    expect(overview_section).to_be_visible(timeout=10000)


def test_admin_sees_teacher_nav_items(page: Page, api_server_url: str):
    username = f"e2e_admin_{uuid.uuid4().hex[:8]}"
    _register_user(api_server_url, username, role="admin")

    page.goto(f"{api_server_url}/login.html", wait_until="networkidle")
    page.fill("#username", username)
    page.fill("#password", "Password123!")
    page.click("button[type='submit']")

    page.wait_for_url(re.compile(r".*/dashboard.html"), timeout=15000)
    expect(page).to_have_url(re.compile(r".*/dashboard.html"))

    expect(page.locator("#user-name-display")).to_be_visible(timeout=10000)

    expect(page.locator("#nav-students")).to_be_visible(timeout=5000)
    expect(page.locator("#nav-grading")).to_be_visible(timeout=5000)
    expect(page.locator("#nav-create")).to_be_visible(timeout=5000)

    page.locator("#nav-students").click()
    expect(page.locator("#view-students")).to_be_visible(timeout=10000)
