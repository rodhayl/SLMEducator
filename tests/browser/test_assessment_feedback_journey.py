"""Synthetic manual assessment, retry, zero-grade and role-isolation acceptance."""

import json
import os
import re
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from test_live_journeys import login, screenshot

pytestmark = pytest.mark.skipif(
    os.environ.get("SLM_BROWSER_ACCEPTANCE") != "1",
    reason="Explicit isolated browser acceptance only",
)

ANSWER = "Synthetic first answer: three eighths."
EDITED_ANSWER = "Synthetic revised answer: I need help comparing equal parts."
FEEDBACK = "Synthetic teacher feedback: compare the numerators of equal eighths."
OUTAGE = "Synthetic grade save unavailable. Retry your saved inputs."
PENDING = re.compile("Pending teacher review|Pendiente de revisión", re.I)


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
    """Use the learner's real navigation, review, edit and submit controls."""
    login(page, world, "learner_a")
    assessment_id = world.manifest["assessment_id"]
    page.locator('[data-view="assessments"]').click()
    with page.expect_response(
        lambda response: response.url
        == f"{world.base_url}/api/assessments/{assessment_id}/start"
        and response.request.method == "POST"
    ) as started:
        page.locator(f'a[href="assessment_taker.html?id={assessment_id}"]').click()
    assert started.value.ok
    submission_id = started.value.json()["submission_id"]
    answer = page.locator("#questions-container textarea")
    answer.fill(ANSWER)
    page.locator("#review-btn").click()
    expect(answer).to_be_disabled()
    expect(answer).to_have_value(ANSWER)
    page.locator('#review-buttons [onclick="exitReviewMode()"]').click()
    expect(answer).to_be_enabled()
    expect(page.locator("#review-btn")).to_be_focused()
    answer.fill(EDITED_ANSWER)
    page.locator("#review-btn").click()
    with page.expect_response(
        lambda response: response.url
        == f"{world.base_url}/api/assessments/{assessment_id}/submit"
        and response.request.method == "POST"
    ) as submitted:
        page.locator('#review-buttons [onclick="submitAssessment()"]').click()
    result = submitted.value.json()
    assert submitted.value.ok and result["submission_id"] == submission_id
    assert result["status"] == "submitted" and result["score"] is None
    expect(page.locator("#results")).to_contain_text(PENDING)
    expect(page.locator("#results")).not_to_contain_text(re.compile(r"0\s*/\s*10"))
    expect(answer).to_be_disabled()
    page.locator(
        f'#results a[href="/assessment_history.html?submission_id={submission_id}"]'
    ).click()
    expect(page.locator("#learner-submission-detail")).to_contain_text(PENDING)
    expect(page.locator("#learner-submission-detail")).to_contain_text(EDITED_ANSWER)
    expect(page.locator("#learner-submission-detail")).not_to_contain_text(
        re.compile(r"0\s*/\s*10")
    )
    screenshot(page, "assessment-pending-review.png")
    return submission_id


def grade_zero_with_one_explicit_retry(
    page: Page, world: Any, submission_id: int
) -> None:
    """Fail only the first exact grade POST and inspect real persisted state."""
    detail_path = f"/api/assessments/submissions/{submission_id}"
    before = world.api("GET", detail_path).json()
    assert before["status"] == "submitted" and before["score"] is None
    assert before["answers"][0]["given_answer"] == EDITED_ANSWER
    assert before["answers"][0]["correct_answer"]
    login(page, world, "teacher_a")
    page.goto(f"{world.base_url}/grading.html?submission_id={submission_id}")
    expect(page.locator("#grade-score")).to_be_enabled()
    expect(page.locator("#grading-placeholder")).to_be_hidden()
    expect(page.locator("#submission-title")).to_be_focused()
    page.locator("#grade-score").fill("0")
    page.locator("#grade-feedback").fill(FEEDBACK)
    grade_url = world.base_url + detail_path + "/grade"
    posts = []

    def fail_first_grade(route: Any) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        posts.append(route.request.post_data_json)
        if len(posts) == 1:
            route.fulfill(status=503, json={"detail": OUTAGE})
        else:
            route.continue_()

    page.route(grade_url, fail_first_grade)
    save = page.locator('#grading-form [onclick="submitGrade()"]')
    save.click()
    expect(page.locator('#toast-container [role="alert"]')).to_contain_text(OUTAGE)
    expect(page.locator('#toast-container [role="alert"]')).to_be_visible()
    expect(page.locator('#toast-container [role="alert"]')).to_have_css("opacity", "1")
    expect(page.locator("#grade-score")).to_have_value("0")
    expect(page.locator("#grade-feedback")).to_have_value(FEEDBACK)
    expect(save).to_be_enabled()
    assert world.api("GET", detail_path).json() == before
    assert posts == [{"score": 0, "feedback": FEEDBACK}]
    screenshot(page, "assessment-grade-save-retry.png")
    with page.expect_response(
        lambda response: response.url == grade_url and response.request.method == "POST"
    ) as saved:
        save.click()
    assert saved.value.ok and saved.value.json()["status"] == "ok"
    expect(save).to_be_enabled()
    expect(page.locator("#grade-score")).to_have_value("0")
    assert posts == [{"score": 0, "feedback": FEEDBACK}] * 2
    page.unroute(grade_url, fail_first_grade)
    after = world.api("GET", detail_path).json()
    assert (after["status"], after["score"], after["total_points"]) == ("graded", 0, 10)
    assert after["feedback"] == FEEDBACK and after["graded_at"]


def read_published_feedback(page: Page, world: Any, submission_id: int) -> None:
    """Real history links, reload and Back preserve the final learner view."""
    login(page, world, "learner_a")
    assessment_id = world.manifest["assessment_id"]
    page.locator('[data-view="assessments"]').click()
    page.locator(
        f'a[href="assessment_history.html?assessment_id={assessment_id}"]'
    ).click()
    page.locator(
        f'#learner-submission-list a[href*="submission_id={submission_id}"]'
    ).click()
    detail = page.locator("#learner-submission-detail")
    expect(detail).to_contain_text(FEEDBACK)
    page.reload()
    expect(detail).to_contain_text(FEEDBACK)
    expect(detail).to_contain_text(re.compile(r"0\s*/\s*10"))
    expect(detail).to_contain_text(EDITED_ANSWER)
    selected = page.locator('#learner-submission-list a[aria-current="true"]')
    selected.hover()
    expect(selected).to_have_css("background-color", "rgb(13, 110, 253)")
    payload = world.api(
        "GET", f"/api/assessments/submissions/{submission_id}", account="learner_a"
    ).json()
    assert_private_assets_absent(payload)
    learner_assessment = world.api(
        "GET", f"/api/assessments/{assessment_id}", account="learner_a"
    ).json()
    assert_private_assets_absent(learner_assessment)
    marker = world.manifest["private_rubric_marker"]
    assert marker not in json.dumps([payload, learner_assessment])
    expect(page.locator("body")).not_to_contain_text(marker)
    private_answer = world.api(
        "GET", f"/api/assessments/submissions/{submission_id}"
    ).json()["answers"][0]["correct_answer"]
    expect(page.locator("body")).not_to_contain_text(private_answer)
    expect(
        page.locator("#grade-score, #grade-feedback, [data-grade-action]")
    ).to_have_count(0)
    screenshot(page, "assessment-learner-zero-feedback.png")
    page.go_back()
    expect(page).to_have_url(re.compile(r"assessment_history\.html\?assessment_id="))
    page.go_forward()
    expect(detail).to_contain_text(FEEDBACK)


def deny_foreign_submission(
    page: Page, world: Any, submission_id: int, account: str
) -> None:
    """Deep-link denial and a forbidden write are enforced by the real server."""
    login(page, world, account)
    detail_url = f"{world.base_url}/api/assessments/submissions/{submission_id}"
    target = "grading" if account == "teacher_b" else "assessment_history"
    with page.expect_response(lambda response: response.url == detail_url) as denied:
        page.goto(f"{world.base_url}/{target}.html?submission_id={submission_id}")
    assert denied.value.status == 403
    assert (
        EDITED_ANSWER not in denied.value.text() and FEEDBACK not in denied.value.text()
    )
    error = page.locator(
        "#answers-container" if account == "teacher_b" else "#learner-submission-detail"
    )
    expect(error).to_contain_text(re.compile("permission|permiso", re.I))
    expect(page.locator("body")).not_to_contain_text(EDITED_ANSWER)
    expect(page.locator("body")).not_to_contain_text(FEEDBACK)
    if account == "teacher_b":
        expect(page.locator("#grade-score")).to_be_disabled()
    else:
        expect(page.locator("#grade-score")).to_have_count(0)
    result = page.evaluate(
        """async (url) => {
        const response = await fetch(url + '/grade', {
            method: 'POST',
            headers: {Authorization: 'Bearer ' + AuthService.getToken(), 'Content-Type': 'application/json'},
            body: JSON.stringify({score: 9, feedback: 'Synthetic forbidden overwrite'})
        });
        return response.status;
    }""",
        detail_url,
    )
    assert result == 403
    assert (
        world.api("GET", "/api/assessments/submissions", account=account).json() == []
    )


def test_manual_assessment_feedback_zero_retry_and_isolation(
    live_page: Page, browser_world: Any
) -> None:
    """Keep the complete journey in one fresh module-scoped synthetic database."""
    page, world = live_page, browser_world
    assessment_id = world.manifest["assessment_id"]
    definition = world.api("GET", f"/api/assessments/{assessment_id}").json()
    assert definition["rubric"]["name"] == world.manifest["private_rubric_marker"]
    assert definition["rubric"]["criteria"][0]["max_points"] == 10
    attempt_posts = []
    page.on(
        "request",
        lambda request: (
            attempt_posts.append(request.url)
            if request.method == "POST"
            and request.url
            in {
                f"{world.base_url}/api/assessments/{assessment_id}/start",
                f"{world.base_url}/api/assessments/{assessment_id}/submit",
            }
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
        f"{world.base_url}/api/assessments/{assessment_id}/start",
        f"{world.base_url}/api/assessments/{assessment_id}/submit",
    ]
