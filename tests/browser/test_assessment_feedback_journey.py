"""React assessment review, explicit retry, zero grade and role isolation."""

import json
import os
import re
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.browser.support import authenticated_status, login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)
ANSWER = "Synthetic first answer: three eighths."
EDITED_ANSWER = "Synthetic revised answer: I need help comparing equal parts."
FEEDBACK = "Synthetic teacher feedback: compare the numerators of equal eighths."
PENDING = re.compile("Awaiting teacher review|No final grade yet")


def assert_private_assets_absent(data: Any) -> None:
    """Check payloads recursively, including nullable redacted answer fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"correct_answer", "rubric", "rubrics"}:
                assert not value, f"Private grading asset exposed: {key}"
            assert_private_assets_absent(value)
    elif isinstance(data, list):
        for value in data:
            assert_private_assets_absent(value)


def submit_from_learner_dashboard(page: Page, world: Any) -> int:
    """Navigate, start explicitly, review, edit and confirm submission."""
    login(page, world, "learner_a")
    assessment_id = world.manifest["assessment_id"]
    definition = world.api("GET", f"/api/assessments/{assessment_id}").json()
    page.get_by_role("navigation").get_by_role(
        "link", name="Assessments", exact=True
    ).click()
    page.get_by_role("link", name=definition["title"], exact=True).click()
    page.get_by_role("button", name="Start assessment", exact=True).click()
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/assessments/{assessment_id}/start")
            and response.request.method == "POST"
        )
    ) as started:
        page.get_by_role("dialog").get_by_role(
            "button", name="Begin attempt", exact=True
        ).click()
    assert started.value.ok
    submission_id = started.value.json()["submission_id"]
    answer = page.get_by_label("Answer to question 1", exact=True)
    answer.fill(ANSWER)
    page.get_by_role("button", name="Review answers", exact=True).click()
    expect(answer).to_have_count(0)
    expect(page.get_by_role("main")).to_contain_text(ANSWER)
    page.get_by_role("button", name="Return to answers", exact=True).click()
    expect(answer).to_be_enabled()
    expect(answer).to_have_value(ANSWER)
    answer.fill(EDITED_ANSWER)
    page.get_by_role("button", name="Review answers", exact=True).click()
    page.get_by_role("button", name="Submit answers", exact=True).click()
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/api/assessments/{assessment_id}/submit")
            and response.request.method == "POST"
        )
    ) as submitted:
        page.get_by_role("dialog").get_by_role(
            "button", name="Submit answers", exact=True
        ).click()
    result = submitted.value.json()
    assert submitted.value.ok and result["submission_id"] == submission_id
    assert result["status"] == "submitted" and result["score"] is None
    expect(page.get_by_role("main")).to_contain_text("Submission received")
    # Confirmed submission invalidates the attempt query into its read-only view.
    expect(page.get_by_role("main")).to_contain_text(PENDING)
    expect(page.get_by_role("main")).not_to_contain_text(re.compile(r"0\s*/\s*10"))
    expect(answer).to_have_count(0)
    page.get_by_role("link", name="Submissions and feedback", exact=True).click()
    page.get_by_role("link", name=definition["title"], exact=True).click()
    expect(page).to_have_url(f"{world.base_url}/envios/{submission_id}")
    expect(page.get_by_role("main")).to_contain_text(EDITED_ANSWER)
    expect(page.get_by_role("main")).to_contain_text(PENDING)
    screenshot(page, "assessment-pending-review.png")
    return submission_id


def grade_zero_with_one_explicit_retry(
    page: Page, world: Any, submission_id: int
) -> None:
    """A failed write keeps inputs and requires a server check before retry."""
    detail_path = f"/api/assessments/submissions/{submission_id}"
    before = world.api("GET", detail_path).json()
    assert before["status"] == "submitted" and before["score"] is None
    assert before["answers"][0]["given_answer"] == EDITED_ANSWER
    assert before["answers"][0]["correct_answer"]
    login(page, world, "teacher_a")
    page.goto(f"{world.base_url}/correcciones/{submission_id}")
    score, feedback = (
        page.get_by_label("Total points", exact=True),
        page.get_by_label("Feedback", exact=True),
    )
    score.fill("0")
    feedback.fill(FEEDBACK)
    grade_url = world.base_url + detail_path + "/grade"
    posts = []

    def fail_first_grade(route: Any) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        posts.append(route.request.post_data_json)
        if len(posts) == 1:
            route.fulfill(status=503, json={"detail": "Synthetic grade save outage"})
        else:
            route.continue_()

    page.route(grade_url, fail_first_grade)
    save = page.get_by_role("button", name="Finalize total grade", exact=True)
    save.click()
    page.get_by_role("dialog").get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text(
        "The result is unknown. Your input is preserved."
    )
    expect(score).to_have_value("0")
    expect(feedback).to_have_value(FEEDBACK)
    expect(save).to_be_disabled()
    assert world.api("GET", detail_path).json() == before
    assert posts == [{"score": 0, "feedback": FEEDBACK}]
    screenshot(page, "assessment-grade-save-retry.png")
    page.get_by_role("button", name="Refresh server state", exact=True).click()
    expect(save).to_be_enabled()
    expect(score).to_have_value("0")
    expect(feedback).to_have_value(FEEDBACK)
    save.click()
    with page.expect_response(
        lambda response: response.url == grade_url and response.request.method == "POST"
    ) as saved:
        page.get_by_role("dialog").get_by_role(
            "button", name="Save", exact=True
        ).click()
    assert saved.value.ok and saved.value.json()["status"] == "ok"
    expect(page.get_by_role("main")).to_contain_text(
        "Grade saved. Server state has been refreshed."
    )
    assert posts == [{"score": 0, "feedback": FEEDBACK}] * 2
    page.unroute(grade_url, fail_first_grade)
    after = world.api("GET", detail_path).json()
    assert (after["status"], after["score"], after["total_points"]) == ("graded", 0, 10)
    assert after["feedback"] == FEEDBACK and after["graded_at"]


def read_published_feedback(page: Page, world: Any, submission_id: int) -> None:
    """History, reload and Back preserve feedback without reserving an attempt."""
    login(page, world, "learner_a")
    assessment_id = world.manifest["assessment_id"]
    definition = world.api("GET", f"/api/assessments/{assessment_id}").json()
    page.get_by_role("navigation").get_by_role(
        "link", name="Assessments", exact=True
    ).click()
    page.get_by_role("link", name=definition["title"], exact=True).click()
    page.get_by_role("link", name="Submissions and feedback", exact=True).click()
    page.get_by_role("link", name=definition["title"], exact=True).click()
    detail = page.get_by_role("main")
    expect(detail).to_contain_text(FEEDBACK)
    page.reload()
    expect(detail).to_contain_text(FEEDBACK)
    expect(detail).to_contain_text(re.compile(r"0\s*/\s*10"))
    expect(detail).to_contain_text(EDITED_ANSWER)
    payload = world.api(
        "GET", f"/api/assessments/submissions/{submission_id}", account="learner_a"
    ).json()
    learner_assessment = world.api(
        "GET", f"/api/assessments/{assessment_id}", account="learner_a"
    ).json()
    assert_private_assets_absent(payload)
    assert_private_assets_absent(learner_assessment)
    marker = world.manifest["private_rubric_marker"]
    assert marker not in json.dumps([payload, learner_assessment])
    expect(detail).not_to_contain_text(marker)
    private_answer = world.api(
        "GET", f"/api/assessments/submissions/{submission_id}"
    ).json()["answers"][0]["correct_answer"]
    expect(detail).not_to_contain_text(private_answer)
    expect(page.get_by_label("Total points", exact=True)).to_have_count(0)
    expect(
        page.get_by_role("button", name="Finalize total grade", exact=True)
    ).to_have_count(0)
    screenshot(page, "assessment-learner-zero-feedback.png")
    page.go_back()
    expect(page).to_have_url(f"{world.base_url}/evaluaciones/{assessment_id}/historial")
    page.go_forward()
    expect(detail).to_contain_text(FEEDBACK)


def deny_foreign_submission(
    page: Page, world: Any, submission_id: int, account: str
) -> None:
    """A forbidden deep link and direct write cannot disclose or change work."""
    login(page, world, account)
    detail_url = f"{world.base_url}/api/assessments/submissions/{submission_id}"
    target = "correcciones" if account == "teacher_b" else "envios"
    with page.expect_response(lambda response: response.url == detail_url) as denied:
        page.goto(f"{world.base_url}/{target}/{submission_id}")
    assert denied.value.status == 403
    assert (
        EDITED_ANSWER not in denied.value.text() and FEEDBACK not in denied.value.text()
    )
    expect(page.get_by_role("alert")).to_contain_text("You do not have access")
    expect(page.get_by_role("main")).not_to_contain_text(EDITED_ANSWER)
    expect(page.get_by_role("main")).not_to_contain_text(FEEDBACK)
    expect(page.get_by_label("Total points", exact=True)).to_have_count(0)
    assert (
        authenticated_status(
            page,
            f"/api/assessments/submissions/{submission_id}/grade",
            "POST",
            {"score": 9, "feedback": "Synthetic forbidden overwrite"},
        )
        == 403
    )
    assert (
        world.api("GET", "/api/assessments/submissions", account=account).json() == []
    )


def test_manual_assessment_feedback_zero_retry_and_isolation(
    live_page: Page, browser_world: Any
) -> None:
    """Keep the full journey in one fresh module-scoped synthetic database."""
    page, world = live_page, browser_world
    assessment_id = world.manifest["assessment_id"]
    definition = world.api("GET", f"/api/assessments/{assessment_id}").json()
    assert definition["rubric"]["name"] == world.manifest["private_rubric_marker"]
    assert definition["rubric"]["criteria"][0]["max_points"] == 10
    attempt_posts = []
    paths = {
        f"{world.base_url}/api/assessments/{assessment_id}/{action}"
        for action in ("start", "submit")
    }
    page.on(
        "request",
        lambda request: (
            attempt_posts.append(request.url)
            if request.method == "POST" and request.url in paths
            else None
        ),
    )
    submission_id = submit_from_learner_dashboard(page, world)
    grade_zero_with_one_explicit_retry(page, world, submission_id)
    read_published_feedback(page, world, submission_id)
    published = world.api("GET", f"/api/assessments/submissions/{submission_id}").json()
    for account in ("teacher_b", "learner_b"):
        deny_foreign_submission(page, world, submission_id, account)
    assert (
        world.api("GET", f"/api/assessments/submissions/{submission_id}").json()
        == published
    )
    assert world.api("GET", f"/api/assessments/{assessment_id}").json() == definition
    submissions = world.api(
        "GET", "/api/assessments/submissions", account="learner_a"
    ).json()
    assert [submission["id"] for submission in submissions] == [submission_id]
    assert attempt_posts == [
        f"{world.base_url}/api/assessments/{assessment_id}/{action}"
        for action in ("start", "submit")
    ]
