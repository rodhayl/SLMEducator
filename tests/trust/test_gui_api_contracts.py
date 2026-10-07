"""Offline API regressions for the React replacement's minimal read/write contracts."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from src.api.routes import classroom, dashboard, study_plans
from src.core.models import (
    Assessment, Badge, Content, ContentType, HelpRequest, QuestionResponse,
    StudentStudyPlan, StudyPlan, Submission, SubmissionStatus,
    TeacherMessage, User, UserBadge, UserRole,
)
from tests.integration.test_trustworthy_scoring_sessions import attempt, create_quiz, world  # noqa: F401


@pytest.fixture
def gui_world(world):  # noqa: F811 - imported pytest fixture
    """Extend the existing real-router fixture with the affected GUI APIs."""
    for router in (classroom.router, dashboard.router, study_plans.router):
        world.client.app.include_router(router)
    admin = User(username="admin", email="admin@example.invalid", first_name="Admin",
                 last_name="Synthetic", role=UserRole.ADMIN, password_hash="unused-test-hash")
    world.db.add(admin)
    world.db.commit()
    world.admin = admin
    return world


def grade_paths(state):
    """Return both authorized grade-summary resources."""
    plan_id = state.content.study_plan_id
    return [f"/api/study-plans/{plan_id}/grades",
            f"/api/study-plans/{plan_id}/topics/{state.content.id}/grades"]


@pytest.mark.parametrize("score", [None, 0, 5, 10])
def test_grade_summaries_distinguish_absent_zero_and_positive(gui_world, score):
    state = gui_world
    quiz_id, questions = create_quiz(state, study_plan_id=state.content.study_plan_id,
                                    topic_id=state.content.id)
    if score is not None:
        state.db.add(Submission(assessment_id=quiz_id, student_id=state.learner.id,
                                status=SubmissionStatus.GRADED, score=score, total_points=10))
        state.db.commit()
    state.user = state.owner
    for path in grade_paths(state):
        response = state.client.get(path)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["average_score"] == (None if score is None else score * 10)
        assert result["passing_rate"] == (None if score is None else 100 if score >= 7 else 0)
    result = state.client.get("/api/dashboard/stats").json()
    assert result["average_score"] == (None if score is None else score * 10)


def test_topic_grades_reject_foreign_topic_and_exclude_other_plan(gui_world):
    state = gui_world
    local_plan_id = state.content.study_plan_id
    foreign_plan = StudyPlan(title="Private other course", creator_id=state.other.id)
    state.db.add(foreign_plan)
    state.db.flush()
    foreign_topic = Content(title="Private other topic", creator_id=state.other.id,
                            content_type=ContentType.LESSON, study_plan_id=foreign_plan.id)
    state.db.add(foreign_topic)
    state.db.flush()
    foreign_assessment = Assessment(title="Private grade", created_by_id=state.other.id,
                                    study_plan_id=foreign_plan.id, topic_id=foreign_topic.id,
                                    passing_score=70)
    state.db.add(foreign_assessment)
    state.db.flush()
    state.db.add(Submission(assessment_id=foreign_assessment.id, student_id=state.outsider.id,
                            status=SubmissionStatus.GRADED, score=9, total_points=10))
    state.db.commit()
    state.user = state.owner
    denied = state.client.get(f"/api/study-plans/{local_plan_id}/topics/{foreign_topic.id}/grades")
    assert denied.status_code == 403, denied.text
    # Even a legitimate shared topic must not pull another course's assessments.
    foreign_assessment.topic_id = state.content.id
    state.db.commit()
    local = state.client.get(grade_paths(state)[1])
    assert local.status_code == 200, local.text
    assert local.json()["total_assessments"] == 0
    assert local.json()["average_score"] is None


def test_topic_grades_accept_explicit_course_content_link(gui_world):
    state = gui_world
    quiz_id, _ = create_quiz(state, study_plan_id=state.content.study_plan_id, topic_id=state.content.id)
    path = grade_paths(state)[1]
    state.content.study_plan_id = None
    state.db.commit()
    state.user = state.owner
    result = state.client.get(path)
    assert result.status_code == 200, result.text
    assert result.json()["total_assessments"] == 1


@pytest.mark.parametrize("payload", [{"notes": "Resolved privately through the lesson discussion."}, {"notes": ""}])
def test_resolution_json_notes_persist_without_sending_message(gui_world, payload):
    state = gui_world
    request = HelpRequest(student_id=state.learner.id, request_text="Help: Explain", status="open",
                          resolution_notes="Old notes")
    state.db.add(request)
    state.db.commit()
    result = state.client.post(f"/api/classroom/help/{request.id}/resolve", json=payload)
    assert result.status_code == 200, result.text
    state.db.expire_all()
    persisted = state.db.get(HelpRequest, request.id)
    assert persisted.status == "resolved"
    assert persisted.resolution_notes == payload["notes"]
    assert persisted.resolved_by_id == state.owner.id
    assert persisted.resolved_at is not None
    assert state.db.query(TeacherMessage).count() == 0


def test_resolution_retains_legacy_query_and_omitted_notes_contract(gui_world):
    state = gui_world
    request = HelpRequest(student_id=state.learner.id, request_text="Help: Explain", status="open")
    state.db.add(request)
    state.db.commit()
    path = f"/api/classroom/help/{request.id}/resolve"
    assert state.client.post(path, params={"notes": "Legacy synthetic note"}).status_code == 200
    assert state.client.post(path).status_code == 200
    state.db.refresh(request)
    assert request.resolution_notes == "Legacy synthetic note"
    assert state.client.post(path, json={"notes": "Body takes precedence"},
                             params={"notes": "Ignored legacy value"}).status_code == 200
    state.db.refresh(request)
    assert request.resolution_notes == "Body takes precedence"


@pytest.mark.parametrize("actor", ["other", "learner", "outsider"])
def test_resolution_authorization_still_blocks_other_actors(gui_world, actor):
    state = gui_world
    request = HelpRequest(student_id=state.learner.id, request_text="Private help", status="open")
    state.db.add(request)
    state.db.commit()
    state.user = getattr(state, actor)
    result = state.client.post(f"/api/classroom/help/{request.id}/resolve", json={"notes": "Must not persist"})
    assert result.status_code == 403, result.text
    state.db.refresh(request)
    assert request.status == "open" and request.resolution_notes is None
    assert request.resolved_by_id is None and request.resolved_at is None


def test_contacts_scope_precedes_search_and_limit(gui_world):
    state = gui_world
    # These alphabetical matches used to consume the result window before policy filtering.
    for index in range(55):
        state.db.add(User(username=f"outsider_{index}", email=f"o{index}@example.invalid",
                          first_name="AAA Searchmatch", last_name=str(index), role=UserRole.STUDENT,
                          teacher_id=state.other.id, password_hash="unused-test-hash"))
    state.learner.first_name = "ZZZ Searchmatch"
    inactive = User(username="inactive", email="inactive@example.invalid", first_name="AAA Searchmatch",
                    last_name="Inactive", role=UserRole.STUDENT, teacher_id=state.owner.id,
                    active=False, password_hash="unused-test-hash")
    state.db.add(inactive)
    state.db.commit()
    result = state.client.get("/api/classroom/users", params={"role": "student", "limit": 1,
                                                            "search": "searchmatch"})
    assert result.status_code == 200, result.text
    assert [row["id"] for row in result.json()] == [state.learner.id]
    assert len(state.client.get("/api/classroom/users", params={"role": "student"}).json()) == 1
    assert state.client.get("/api/classroom/users", params={"search": "outsider_"}).json() == []
    assert state.client.get("/api/classroom/users", params={"role": "invalid"}).status_code == 400


def test_contacts_preserve_legacy_and_explicit_enrollment_boundaries(gui_world):
    state = gui_world
    state.learner.teacher_id = None
    state.learner.settings = {}
    state.db.add(StudentStudyPlan(student_id=state.learner.id, study_plan_id=state.content.study_plan_id))
    state.db.commit()
    assert state.learner.id in [item["id"] for item in state.client.get("/api/classroom/users").json()]
    state.user = state.learner
    ids = [item["id"] for item in state.client.get("/api/classroom/users").json()]
    assert set(ids) == {state.owner.id, state.admin.id}
    state.learner.settings = {"enrollment_explicit": True}
    state.db.commit()
    assert [item["id"] for item in state.client.get("/api/classroom/users").json()] == [state.admin.id]
    state.user = state.admin
    ids = [item["id"] for item in state.client.get("/api/classroom/users").json()]
    assert set(ids) == {state.owner.id, state.other.id, state.learner.id, state.outsider.id}


def test_badges_remain_current_actor_only(gui_world):
    state = gui_world
    badge = Badge(name="Synthetic learner badge", description="Synthetic participation only", criteria_type="xp_threshold",
                  criteria_value={"xp": 1}, xp_value=0)
    state.db.add(badge)
    state.db.flush()
    state.db.add(UserBadge(user_id=state.learner.id, badge_id=badge.id))
    state.db.commit()
    for actor, earned in [(state.owner, False), (state.learner, True), (state.admin, False)]:
        state.user = actor
        result = state.client.get("/api/gamification/badges", params={"student_id": state.learner.id})
        assert result.status_code == 200, result.text
        actual = next(item for item in result.json() if item["id"] == badge.id)
        assert actual["earned"] is earned
        assert (actual["earned_at"] is not None) is earned


@pytest.mark.parametrize("actor,allowed", [("owner", True), ("admin", True), ("learner", False)])
def test_assessment_read_capability_matches_authorization(gui_world, actor, allowed):
    state = gui_world
    quiz_id, _ = create_quiz(state)
    state.user = getattr(state, actor)
    details = state.client.get(f"/api/assessments/{quiz_id}")
    assert details.status_code == 200, details.text
    assert details.json()["can_manage"] is allowed
    listing = state.client.get("/api/assessments/")
    assert next(item for item in listing.json() if item["id"] == quiz_id)["can_manage"] is allowed
    assert (details.json()["questions"][0]["correct_answer"] is not None) is allowed
    assert state.db.query(Submission).count() == 0


@pytest.mark.parametrize("minutes", [None, 15])
def test_submission_get_repeats_persisted_timer_without_start_side_effect(gui_world, minutes):
    state = gui_world
    quiz_id, _ = create_quiz(state, time_limit_minutes=minutes, max_attempts=2)
    started = state.client.post(f"/api/assessments/{quiz_id}/start").json()
    path = f"/api/assessments/submissions/{started['id']}"
    before = state.db.query(Submission).one().started_at
    for _ in range(2):
        response = state.client.get(path)
        assert response.status_code == 200, response.text
        for key in ("started_at", "expires_at", "timing_provenance", "time_limit_minutes"):
            actual, original = response.json()[key], started[key]
            if key in {"started_at", "expires_at"} and original is not None:
                assert datetime.fromisoformat(actual.replace("Z", "+00:00")) == datetime.fromisoformat(original.replace("Z", "+00:00"))
            else:
                assert actual == original
        if minutes is not None:
            assert datetime.fromisoformat(response.json()["expires_at"].replace("Z", "+00:00")) == before + timedelta(minutes=minutes)
    state.db.expire_all()
    assert state.db.query(Submission).one().started_at == before
    state.user = state.outsider
    assert state.client.get(path).status_code == 403
    assert state.db.query(Submission).count() == 1


def test_submission_get_preserves_legacy_unknown_timing(gui_world):
    state = gui_world
    quiz_id, _ = create_quiz(state, time_limit_minutes=15)
    started = state.client.post(f"/api/assessments/{quiz_id}/start").json()
    state.db.execute(text("UPDATE assessment_submissions SET started_at = '2020-01-02 03:04:05' WHERE id = :id"),
                     {"id": started["id"]})
    state.db.commit()
    state.db.expire_all()
    response = state.client.get(f"/api/assessments/submissions/{started['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["started_at"] == "2020-01-02T03:04:05"
    assert response.json()["timing_provenance"] == "legacy_unknown"
    assert response.json()["expires_at"] is None
    assert state.db.query(Submission).one().status == SubmissionStatus.DRAFT


def test_ai_draft_total_keeps_teacher_zero_over_stale_suggestion(gui_world, monkeypatch):
    state = gui_world
    from src.api.routes import assessment
    quiz_id, questions = create_quiz(state, questions=[
        {"question_text": "First reason", "question_type": "short_answer", "points": 10},
        {"question_text": "Second reason", "question_type": "short_answer", "points": 10},
    ], grading_mode="ai_assisted")

    class SyntheticProvider:
        """Simulate an overlapping teacher grade while the provider is detached."""

        def grade_answer(self, **kwargs):
            response = state.db.query(QuestionResponse).filter_by(question_id=questions[0]["id"]).one()
            response.score = 0
            response.ai_suggested_score = 9
            state.db.commit()
            return {"points_earned": 4, "feedback": "Synthetic provisional review"}

        def close(self):
            return None

    monkeypatch.setattr(assessment, "get_ai_service_dependency", lambda user, db: SyntheticProvider())
    result, _ = attempt(state, quiz_id, [{"question_id": q["id"], "response_text": "Synthetic reason"} for q in questions])
    saved = state.db.get(Submission, result["id"])
    assert saved.ai_draft_score == 4
    assert saved.score is None and saved.teacher_approved is False
    assert result["status"] == "ai_graded"
    state.user = state.owner
    detail = state.client.get(f"/api/assessments/submissions/{saved.id}").json()
    assert detail["answers"][0]["points"] == 0


def test_capability_and_submission_reads_preserve_assessment_authorship(gui_world):
    state = gui_world
    quiz_id, questions = create_quiz(state)
    result, _ = attempt(state, quiz_id, [{"question_id": questions[0]["id"], "response_text": "B"}])
    state.learner.teacher_id = state.other.id
    state.learner.settings = {"enrollment_explicit": True}
    state.db.commit()
    state.user = state.other
    assert state.client.get(f"/api/assessments/{quiz_id}").status_code == 403
    assert state.client.get(f"/api/assessments/submissions/{result['id']}").status_code == 403
    assert state.client.get("/api/assessments/submissions").json() == []
    state.user = state.owner
    assert state.client.get(f"/api/assessments/{quiz_id}").json()["can_manage"] is True
    assert state.client.get(f"/api/assessments/submissions/{result['id']}").status_code == 200
    for actor in [state.learner, state.other]:
        state.user = actor
        for path in grade_paths(state):
            assert state.client.get(path).status_code == 403
    state.user = state.learner
    feedback = state.client.get(f"/api/assessments/submissions/{result['id']}")
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["answers"][0]["correct_answer"] is None


@pytest.mark.parametrize("payload", [{"notes": 12}, ["notes"], "private note"])
def test_invalid_resolution_body_does_not_mutate_request(gui_world, payload):
    state = gui_world
    request = HelpRequest(student_id=state.learner.id, request_text="Synthetic request", status="open")
    state.db.add(request)
    state.db.commit()
    result = state.client.post(f"/api/classroom/help/{request.id}/resolve", json=payload)
    assert result.status_code == 422, result.text
    state.db.refresh(request)
    assert request.status == "open" and request.resolution_notes is None
