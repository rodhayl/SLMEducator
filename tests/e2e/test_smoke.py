"""
Smoke tests for basic application functionality.
"""

import re
from playwright.sync_api import Page, expect


def test_homepage_loads(index_page: Page):
    """Verify the homepage loads and title is correct."""
    # Wait for page to fully load
    index_page.wait_for_load_state("networkidle")

    # Check title
    expect(index_page).to_have_title(re.compile(r"SLM Educator"), timeout=10000)

    # Check for main heading - page uses h2 not h1
    heading = index_page.locator("h2")
    expect(heading.first).to_be_visible(timeout=10000)


def test_api_status_check(index_page: Page):
    """Verify the frontend connects to the API status endpoint."""
    # Wait for page to fully load and JS to execute
    index_page.wait_for_load_state("networkidle")

    # The frontend fetches /api/status and updates the #status div
    status_div = index_page.locator("#status")

    # Wait for the async fetch to complete - check for 'online' status text
    # Increase timeout for slow API responses
    expect(status_div).to_be_visible(timeout=15000)
    expect(status_div).to_contain_text("online", timeout=15000)

    # Page uses Bootstrap bg-success class for green
    expect(status_div).to_have_class(re.compile(r"bg-success"), timeout=10000)
