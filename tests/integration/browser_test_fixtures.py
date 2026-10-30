"""
Browser Integration Test Data Fixtures.

Provides test accounts and data setup utilities for browser-based testing
of the SLM Educator application.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TestAccount:
    """Test account credentials and metadata."""

    username: str
    password: str
    role: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# Standard test accounts used across browser tests
BROWSER_TEST_ACCOUNTS: Dict[str, TestAccount] = {
    "teacher": TestAccount(
        username="tester_unique_123",
        password="Password123!",
        role="teacher",
        email="tester@example.com",
        first_name="Test",
        last_name="Teacher",
    ),
    "student": TestAccount(
        username="teststudent123",
        password="TestPass123!",
        role="student",
        email="student@example.com",
        first_name="Test",
        last_name="Student",
    ),
    "admin": TestAccount(
        username="admin_test",
        password="AdminPass123!",
        role="admin",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
    ),
}


# Integration test scenarios from BROWSER_TESTS.md Section 21
INTEGRATION_SCENARIOS = {
    "21.1": {
        "name": "Content Creation to Session Flow",
        "steps": [
            "Create content",
            "Start session",
            "Complete session",
            "Verify activity logged",
        ],
        "required_elements": [
            "#create-ai-content-form",
            "#generated-items-list",
            "#session-timer",
        ],
    },
    "21.2": {
        "name": "Assessment Creation and Grading",
        "steps": [
            "Create assessment",
            "Student takes assessment",
            "Teacher grades",
            "Student views results",
        ],
        "required_elements": [
            "#quiz-title",
            "#questions-container",
            "#grading-filter-tabs",
        ],
    },
    "21.3": {
        "name": "Study Plan Assignment Flow",
        "steps": [
            "Create study plan",
            "Assign to student",
            "Student starts plan",
            "Progress tracked",
        ],
        "required_elements": [
            "#plan-title",
            "#studentDetailModal",
            "#continue-learning-card",
        ],
    },
    "21.4": {
        "name": "Help Request to Resolution",
        "steps": [
            "Student submits help",
            "Teacher views queue",
            "Teacher responds",
            "Student receives response",
        ],
        "required_elements": ["#helpModal", "#help-queue-list", "#inbox-unread-badge"],
    },
    "21.5": {
        "name": "Badge Award Flow",
        "steps": [
            "Complete qualifying action",
            "Badge awarded",
            "Notification shown",
            "Badge in profile",
        ],
        "required_elements": ["#gam-badges", "#profile-badges-list"],
    },
}


def get_test_account(role: str = "teacher") -> TestAccount:
    """
    Get test account for specified role.

    Args:
        role: Account role (teacher, student, admin)

    Returns:
        TestAccount with credentials

    Raises:
        KeyError: If role not found
    """
    return BROWSER_TEST_ACCOUNTS[role]


def get_integration_scenario(scenario_id: str) -> Dict[str, Any]:
    """
    Get integration test scenario details.

    Args:
        scenario_id: Scenario ID (e.g., "21.1")

    Returns:
        Scenario configuration dict
    """
    return INTEGRATION_SCENARIOS.get(scenario_id, {})
