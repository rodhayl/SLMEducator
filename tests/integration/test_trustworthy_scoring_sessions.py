"""Synthetic regressions for attempt, grading and session trust boundaries."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_db
from src.api.routes import assessment, gamification, learning
from src.api.security import get_current_user
from src.core.models import (
    Assessment, Content, ContentType, DailyGoal, LearningSession, MasteryNode,
    QuestionResponse, SessionStatus, StudyPlan, StudyPlanContent, Submission,
    SubmissionStatus, User, UserRole,
)
from src.core.services.ai_service import AIService


@pytest.fixture
def world(db_session, monkeypatch):
    """Use an isolated router application and only disposable synthetic rows."""
    users = []
    for name, role in (("owner", UserRole.TEACHER), ("other", UserRole.TEACHER),
                       ("learner", UserRole.STUDENT), ("outsider", UserRole.STUDENT)):
        user = User(username=name, email=f"{name}@example.invalid", first_name=name,
                    last_name="Synthetic", role=role, password_hash="unused-test-hash")
        db_session.add(user)
        users.append(user)
    db_session.flush()
    owner, other, learner, outsider = users
    learner.teacher_id = owner.id
    outsider.teacher_id = other.id
    plan = StudyPlan(title="Published synthetic plan", creator_id=owner.id, is_public=True)
    db_session.add(plan)
    db_session.flush()
    content = Content(title="Synthetic lesson", creator_id=owner.id,
                      content_type=ContentType.LESSON, difficulty=1, study_plan_id=plan.id)
    db_session.add(content)
    db_session.flush()
    db_session.add(StudyPlanContent(study_plan_id=plan.id, content_id=content.id, order_index=0))
    db_session.commit()
    app = FastAPI()
    for router in (assessment.router, learning.router, gamification.router):
        app.include_router(router)
    state = SimpleNamespace(user=owner, owner=owner, other=other, learner=learner,
                            outsider=outsider, db=db_session, content=content)
    app.dependency_overrides[get_current_user] = lambda: state.user
    app.dependency_overrides[get_db] = lambda: db_session
    monkeypatch.setattr(assessment, "get_ai_service_dependency", Mock(side_effect=RuntimeError("No test provider")))
    with TestClient(app) as client:
        state.client = client
        yield state


def create_quiz(world, questions=None, **settings):
    """Create and publish a valid assessment under the synthetic owner."""
    world.user = world.owner
    questions = questions or [{"question_text": "Choose A", "question_type": "multiple_choice",
                               "points": 10, "correct_answer": "A", "options": {"A": "A", "B": "B"}}]
    response = world.client.post("/api/assessments/", json={"title": "Synthetic quiz", "questions": questions, **settings})
    assert response.status_code == 200, response.text
    quiz_id = response.json()["id"]
    response = world.client.post(f"/api/assessments/{quiz_id}/publish")
    assert response.status_code == 200, response.text
    details = world.client.get(f"/api/assessments/{quiz_id}").json()
    world.user = world.learner
    return quiz_id, details["questions"]


def attempt(world, quiz_id, answers):
    """Start and finalize a durable attempt."""
    start = world.client.post(f"/api/assessments/{quiz_id}/start")
    assert start.status_code == 200, start.text
    payload = {"submission_id": start.json()["id"], "answers": answers}
    result = world.client.post(f"/api/assessments/{quiz_id}/submit", json=payload)
    assert result.status_code == 200, result.text
    return result.json(), payload


def test_duplicate_and_foreign_answers_are_rejected_before_attempt(world):
    quiz_id, questions = create_quiz(world)
    other_id, other_questions = create_quiz(world)
    answer = {"question_id": questions[0]["id"], "response_text": "A"}
    for answers in ([answer, answer], [{"question_id": other_questions[0]["id"], "response_text": "A"}],
                    [{"question_id": 999999, "response_text": "A"}]):
        result = world.client.post(f"/api/assessments/{quiz_id}/submit", json={"answers": answers})
        assert result.status_code == 422, result.text
    assert world.db.query(Submission).count() == 0
    assert world.learner.xp == 0


def test_attempt_and_submission_retries_are_idempotent(world):
    quiz_id, questions = create_quiz(world)
    start = world.client.post(f"/api/assessments/{quiz_id}/start").json()
    assert world.client.post(f"/api/assessments/{quiz_id}/start").json()["id"] == start["id"]
    result, payload = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "A"}])
    assert result["score"] == 10 and result["status"] == "graded"
    assert world.client.post(f"/api/assessments/{quiz_id}/submit", json=payload).json() == result
    world.db.refresh(world.learner)
    assert world.learner.xp == 25
    assert world.db.query(Submission).count() == world.db.query(QuestionResponse).count() == 1
    assert world.client.post(f"/api/assessments/{quiz_id}/start").status_code == 409
    payload["answers"][0]["response_text"] = "B"
    assert world.client.post(f"/api/assessments/{quiz_id}/submit", json=payload).status_code == 409


def test_legacy_retry_and_omitted_answers_preserve_total(world):
    quiz_id, questions = create_quiz(world, questions=[
        {"question_text": "A?", "question_type": "true_false", "points": 10, "correct_answer": "true"},
        {"question_text": "B?", "question_type": "short_answer", "points": 5},
    ])
    payload = {"answers": [{"question_id": questions[0]["id"], "response_text": "true"}]}
    first = world.client.post(f"/api/assessments/{quiz_id}/submit", json=payload)
    replay = world.client.post(f"/api/assessments/{quiz_id}/submit", json=payload)
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["score"] == 10 and first.json()["total_points"] == 15
    assert world.db.query(QuestionResponse).count() == 2
    assert world.db.query(QuestionResponse).order_by(QuestionResponse.id.desc()).first().score == 0


def test_separate_explicit_attempts_can_have_same_answers(world):
    quiz_id, questions = create_quiz(world, max_attempts=2)
    answers = [{"question_id": questions[0]["id"], "response_text": "A"}]
    one, _ = attempt(world, quiz_id, answers)
    two, _ = attempt(world, quiz_id, answers)
    assert one["id"] != two["id"]
    assert world.client.post(f"/api/assessments/{quiz_id}/start").status_code == 409


@pytest.mark.parametrize("mode", ["ai_assisted", "ai_automatic"])
def test_ai_uses_instructor_rubric_and_remains_provisional(world, monkeypatch, mode):
    quiz_id, questions = create_quiz(world, questions=[{"question_text": "Explain reasoning", "question_type": "short_answer", "points": 10}],
                                     grading_mode=mode, rubric={"name": "Reasoning", "criteria": [{"name": "Evidence", "description": "Cite the lesson", "max_points": 10}]})
    provider = Mock()
    provider.grade_answer.return_value = {"points_earned": 8, "feedback": "Useful evidence", "percentage": 80}
    lookup = Mock(return_value=provider)
    monkeypatch.setattr(assessment, "get_ai_service_dependency", lookup)
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "My reasoning"}])
    assert result["status"] == "ai_graded" and result["score"] is None and result["needs_review"] is True
    assert lookup.call_args.args[0].id == world.owner.id
    rubric = provider.grade_answer.call_args.kwargs["rubric"]
    assert rubric["rubrics"][0]["criteria"][0]["name"] == "Evidence"
    response = world.db.query(QuestionResponse).one()
    assert response.score is None and response.ai_suggested_score == 8 and response.ai_confidence is None
    world.user = world.owner
    accepted = world.client.post(f"/api/assessments/submissions/{result['id']}/accept-ai")
    assert accepted.status_code == 200 and accepted.json()["final_score"] == 8
    replay = world.client.post(f"/api/assessments/submissions/{result['id']}/accept-ai")
    assert replay.status_code == 200 and replay.json()["final_score"] == 8


@pytest.mark.parametrize("invalid", [{}, {"points_earned": 999, "feedback": "bad"},
                                      {"points_earned": "8", "feedback": "bad"},
                                      {"points_earned": None, "status": "needs_review", "feedback": "bad"}])
def test_invalid_ai_never_becomes_final_failure(world, monkeypatch, invalid):
    quiz_id, questions = create_quiz(world, questions=[{"question_text": "Explain", "question_type": "short_answer", "points": 10}], grading_mode="ai_automatic")
    provider = Mock()
    provider.grade_answer.return_value = invalid
    monkeypatch.setattr(assessment, "get_ai_service_dependency", lambda user, db: provider)
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "Answer"}])
    assert result["status"] == "submitted" and result["score"] is None and result["needs_review"]
    response = world.db.query(QuestionResponse).one()
    assert response.score is None and response.ai_suggested_score is None


def test_unavailable_provider_leaves_manual_review(world):
    quiz_id, questions = create_quiz(world, questions=[{"question_text": "Explain", "question_type": "short_answer", "points": 10}], grading_mode="ai_automatic")
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "Answer"}])
    assert result["status"] == "submitted" and result["score"] is None


@pytest.mark.parametrize("text", ["garbage", "{}", '{"points_earned":-1,"feedback":"bad"}',
                                   '{"points_earned":11,"feedback":"bad"}', '{"points_earned":true,"feedback":"bad"}',
                                   '{"points_earned":5.5,"feedback":"bad"}'])
def test_parser_returns_typed_review_without_fake_zero(text):
    service = object.__new__(AIService)
    result = service._parse_grading_response(text, 10)
    assert result["status"] == "needs_review" and result["points_earned"] is None and result["percentage"] is None


def test_parser_derives_percentage_but_never_confidence():
    service = object.__new__(AIService)
    result = service._parse_grading_response('{"points_earned":8,"feedback":"Good","percentage":1,"confidence":0.99}', 10)
    assert result["percentage"] == 80 and result["confidence"] is None
    assert result["status"] == "suggested" and result["needs_review"]


@pytest.mark.parametrize("score", [-1, 11, 777, 2.5])
def test_grade_ranges_on_total_and_response(world, score):
    quiz_id, questions = create_quiz(world)
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "A"}])
    response_id = world.db.query(QuestionResponse).one().id
    world.user = world.owner
    base = f"/api/assessments/submissions/{result['id']}"
    assert world.client.post(base + "/grade", json={"score": score}).status_code == 422
    assert world.client.post(base + f"/responses/{response_id}/grade", json={"score": score}).status_code == 422


def test_authorization_on_assessment_and_grading_paths(world):
    quiz_id, questions = create_quiz(world)
    result, _ = attempt(world, quiz_id, [{"question_id": questions[0]["id"], "response_text": "A"}])
    response_id = world.db.query(QuestionResponse).one().id
    world.user = world.other
    assert world.client.get(f"/api/assessments/{quiz_id}").status_code == 403
    assert world.client.get(f"/api/assessments/{quiz_id}/stats").status_code == 403
    assert world.client.get("/api/assessments/submissions").json() == []
    base = f"/api/assessments/submissions/{result['id']}"
    assert world.client.get(base).status_code == 403
    assert world.client.post(base + "/grade", json={"score": 5}).status_code == 403
    assert world.client.post(base + "/accept-ai").status_code == 403
    assert world.client.post(base + f"/responses/{response_id}/grade", json={"score": 5}).status_code == 403
    world.user = world.outsider
    assert world.client.post(f"/api/assessments/{quiz_id}/start").status_code == 403
    assert world.client.post(f"/api/assessments/{quiz_id}/submit", json={"answers": []}).status_code == 403


def test_draft_publication_question_validation_and_frozen_attempts(world):
    draft = world.client.post("/api/assessments/", json={"title": "Draft"}).json()
    assert draft["is_published"] is False
    assert world.client.post(f"/api/assessments/{draft['id']}/publish").status_code == 422
    world.user = world.learner
    assert world.client.get(f"/api/assessments/{draft['id']}").status_code == 403
    quiz_id, _ = create_quiz(world)
    assert world.client.post(f"/api/assessments/{quiz_id}/start").status_code == 200
    world.user = world.owner
    assert world.client.put(f"/api/assessments/{quiz_id}", json={"questions": []}).status_code == 409
    assert world.client.delete(f"/api/assessments/{quiz_id}").status_code == 409


def test_timed_attempt_contract_and_late_work_preservation(world):
    quiz_id, questions = create_quiz(world, time_limit_minutes=45)
    detail = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert detail["time_limit_minutes"] == 45
    assert world.client.post(f"/api/assessments/{quiz_id}/submit", json={"answers": []}).status_code == 409
    start = world.client.post(f"/api/assessments/{quiz_id}/start").json()
    assert start["expires_at"] and start["time_limit_minutes"] == 45
    submission = world.db.get(Submission, start["id"])
    submission.started_at = datetime.now() - timedelta(minutes=46)
    world.db.commit()
    result = world.client.post(f"/api/assessments/{quiz_id}/submit", json={"submission_id": start["id"], "answers": [{"question_id": questions[0]["id"], "response_text": "A"}]}).json()
    assert result["status"] == "submitted" and result["score"] is None
    assert world.db.query(QuestionResponse).one().get_decrypted_response() == "A"


def test_session_start_end_restore_and_rewards_are_idempotent(world):
    world.user = world.learner
    goal = DailyGoal(user_id=world.learner.id, goal_date=date.today(), goal_type="lessons", target_value=3, current_value=0)
    world.db.add(goal)
    world.db.commit()
    start = world.client.post("/api/learning/start", json={"content_id": world.content.id}).json()
    assert world.client.post("/api/learning/start", json={"content_id": world.content.id}).json()["id"] == start["id"]
    endpoint = f"/api/learning/{start['id']}"
    assert world.client.patch(endpoint + "/notes", json={"notes": "Saved notes"}).status_code == 200
    first = world.client.post(endpoint + "/end", json={"difficulty_rating": 3}).json()
    assert first["notes"] == "Saved notes"
    world.db.refresh(world.learner)
    first_xp = world.learner.xp
    assert first_xp >= 50  # Seeded badges may add a one-time reward.
    second = world.client.post(endpoint + "/end", json={"notes": "Retry must not overwrite"}).json()
    assert second == first
    world.db.refresh(world.learner)
    assert world.learner.xp == first_xp
    assert goal.current_value == 1
    assert world.db.query(MasteryNode).count() == 0
    assert world.learner.settings["self_confidence"][str(world.content.id)]["rating"] == 3
    assert world.client.post(endpoint + "/restore").status_code == 200
    assert world.client.post(endpoint + "/restore").status_code == 200
    assert world.client.post(endpoint + "/end", json={"difficulty_rating": 5}).status_code == 200
    world.db.refresh(world.learner)
    assert world.learner.xp == first_xp
    assert world.db.query(MasteryNode).count() == 0
    assert world.learner.settings["self_confidence"][str(world.content.id)]["rating"] == 3
    assert goal.current_value == 1


def test_session_private_content_and_client_xp_are_rejected(world):
    private = Content(title="Private", creator_id=world.other.id, content_type=ContentType.LESSON)
    world.db.add(private)
    world.db.commit()
    world.user = world.learner
    for endpoint in ("/api/learning/start", f"/api/learning/restart/{private.id}"):
        assert world.client.post(endpoint, json={"content_id": private.id}).status_code == 403
    assert world.client.post("/api/gamification/award-xp?amount=999999").status_code == 403
    world.db.refresh(world.learner)
    assert world.learner.xp == 0


def test_grading_assets_roundtrip_only_for_owner(world):
    quiz_id, questions = create_quiz(world, rubric={"name": "Draft rubric", "criteria": [{"name": "Accuracy", "max_points": 10}]})
    learner_view = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert learner_view["questions"][0]["correct_answer"] is None and learner_view["rubric"] is None
    world.user = world.owner
    owner_view = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert owner_view["questions"][0]["correct_answer"] == "A"
    assert owner_view["rubric"]["criteria"][0]["name"] == "Accuracy"
    updated = world.client.put(f"/api/assessments/{quiz_id}", json={"questions": [
        {"question_text": "Choose B", "question_type": "multiple_choice", "points": 15, "correct_answer": "B"}],
        "rubric": {"name": "New rubric", "criteria": [{"name": "Reasoning", "max_points": 15}]}})
    assert updated.status_code == 200, updated.text
    owner_view = world.client.get(f"/api/assessments/{quiz_id}").json()
    assert len(owner_view["questions"]) == 1 and owner_view["questions"][0]["correct_answer"] == "B"
    assert owner_view["total_points"] == 15
    assert owner_view["rubric"]["name"] == "New rubric"


def test_partial_ai_accept_cannot_finalize_ungraded_answer(world, monkeypatch):
    quiz_id, questions = create_quiz(world, questions=[
        {"question_text": "Explain one", "question_type": "short_answer", "points": 10},
        {"question_text": "Explain two", "question_type": "short_answer", "points": 10}])
    provider = Mock()
    provider.grade_answer.side_effect = [{"points_earned": 8, "feedback": "Good"}, RuntimeError("Unavailable")]
    monkeypatch.setattr(assessment, "get_ai_service_dependency", lambda user, db: provider)
    result, _ = attempt(world, quiz_id, [{"question_id": q["id"], "response_text": "Answer"} for q in questions])
    world.user = world.owner
    base = f"/api/assessments/submissions/{result['id']}"
    assert world.client.post(base + "/accept-ai").status_code == 409
    responses = world.db.query(QuestionResponse).order_by(QuestionResponse.id).all()
    assert all(response.score is None for response in responses)
    assert world.client.post(base + f"/responses/{responses[1].id}/grade", json={"score": 7}).status_code == 200
    assert world.client.post(base + f"/responses/{responses[0].id}/grade", json={"score": 9}).status_code == 200
    details = world.client.get(base).json()
    assert details["status"] == "graded" and details["score"] == 16


def test_session_failed_reward_rolls_back_completion(world, monkeypatch):
    world.user = world.learner
    start = world.client.post("/api/learning/start", json={"content_id": world.content.id}).json()
    monkeypatch.setattr(learning, "award_activity_xp", Mock(side_effect=RuntimeError("Synthetic reward failure")))
    with pytest.raises(RuntimeError, match="Synthetic reward failure"):
        world.client.post(f"/api/learning/{start['id']}/end", json={})
    world.db.rollback()
    session = world.db.get(LearningSession, start["id"])
    assert session.status == SessionStatus.ACTIVE and session.end_time is None
    world.db.refresh(world.learner)
    assert world.learner.xp == 0


def test_concurrent_submit_replays_create_one_result_and_reward(world):
    """Independent DB sessions model two browser retries hitting the server."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker

    quiz_id, questions = create_quiz(world)
    started = world.client.post(f"/api/assessments/{quiz_id}/start").json()
    learner_id = world.learner.id
    factory = sessionmaker(bind=world.db.get_bind())
    barrier = Barrier(2)
    payload = assessment.SubmissionCreate(submission_id=started["id"], answers=[
        assessment.AnswerSubmission(question_id=questions[0]["id"], response_text="A")])

    def submit():
        with factory() as db:
            user = db.get(User, learner_id)
            barrier.wait(timeout=5)
            return assessment.submit_assessment(quiz_id, payload, user, db)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert results[0] == results[1]
    world.db.expire_all()
    assert world.db.query(Submission).count() == world.db.query(QuestionResponse).count() == 1
    assert world.db.get(User, learner_id).xp == 25


def test_concurrent_session_end_awards_once(world):
    """Conditional completion claims avoid duplicate rewards under a race."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker

    world.user = world.learner
    started = world.client.post("/api/learning/start", json={"content_id": world.content.id}).json()
    learner_id = world.learner.id
    factory = sessionmaker(bind=world.db.get_bind())
    barrier = Barrier(2)

    def complete():
        with factory() as db:
            user = db.get(User, learner_id)
            barrier.wait(timeout=5)
            return asyncio.run(learning.end_session(started["id"], learning.SessionUpdate(), user, db))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: complete(), range(2)))
    assert results[0] == results[1]
    world.db.expire_all()
    assert world.db.get(User, learner_id).xp == 75  # 50 activity + one seeded badge worth 25.


def test_slow_provider_does_not_hold_writes_or_overwrite_teacher(world, monkeypatch):
    """Pause a real route's provider while another request writes and teacher grades."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from fastapi import Depends, Request
    from sqlalchemy.orm import sessionmaker

    quiz_id, questions = create_quiz(world, questions=[
        {"question_text": "Explain", "question_type": "short_answer", "points": 10}])
    start = world.client.post(f"/api/assessments/{quiz_id}/start").json()
    learner_id, other_id, teacher_id = world.learner.id, world.outsider.id, world.owner.id
    content_id = world.content.id
    factory = sessionmaker(bind=world.db.get_bind())
    entered, release = Event(), Event()
    provider = Mock()

    def slow_grade(**kwargs):
        entered.set()
        assert release.wait(timeout=10), "Test provider was not released"
        return {"points_earned": 9, "feedback": "AI suggestion"}

    provider.grade_answer.side_effect = slow_grade
    monkeypatch.setattr(assessment, "get_ai_service_dependency", lambda user, db: provider)
    app = FastAPI()
    app.include_router(assessment.router)
    app.include_router(learning.router)

    def database():
        with factory() as db:
            yield db

    def user(request: Request, db=Depends(get_db)):
        return db.get(User, int(request.headers["X-User"]))

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    payload = {"submission_id": start["id"], "answers": [
        {"question_id": questions[0]["id"], "response_text": "Submitted reasoning"}]}
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=3) as pool:
        pending = pool.submit(client.post, f"/api/assessments/{quiz_id}/submit",
                              json=payload, headers={"X-User": str(learner_id)})
        try:
            assert entered.wait(timeout=5)
            write = pool.submit(client.post, "/api/learning/start", json={"content_id": content_id},
                                headers={"X-User": str(other_id)})
            assert write.result(timeout=2).status_code == 200
            replay = client.post(f"/api/assessments/{quiz_id}/submit", json=payload, headers={"X-User": str(learner_id)})
            assert replay.status_code == 200 and replay.json()["status"] == "submitted"
            teacher = client.post(f"/api/assessments/submissions/{start['id']}/grade", json={"score": 7},
                                  headers={"X-User": str(teacher_id)})
            assert teacher.status_code == 200
        finally:
            release.set()
        result = pending.result(timeout=5)
    assert result.status_code == 200
    assert result.json()["status"] == "graded" and result.json()["score"] == 7
    world.db.expire_all()
    assert world.db.get(User, learner_id).xp == 25
    assert world.db.query(QuestionResponse).one().ai_suggested_score is None


@pytest.mark.parametrize(
    "key_state",
    [
        "missing",
        "wrong_key",
        "malformed",
        "getter_unavailable",
        "blank_key",
        "legacy_plaintext",
    ],
)
@pytest.mark.parametrize("answer", ["A", ""])
def test_unusable_objective_keys_preserve_pending_review(
    world, monkeypatch, key_state, answer
):
    """Missing/corrupt keys cannot become final zeroes, including omitted work."""
    from cryptography.fernet import Fernet
    from src.core.models import Question

    quiz_id, questions = create_quiz(world)
    question = world.db.get(Question, questions[0]["id"])
    if key_state == "missing":
        question.correct_answer = None
    elif key_state == "wrong_key":
        question.correct_answer = Fernet(Fernet.generate_key()).encrypt(b"A").decode()
    elif key_state == "malformed":
        question.correct_answer = "gAAAA-invalid-ciphertext"
    elif key_state == "blank_key":
        question.set_encrypted_correct_answer("   ")
    elif key_state == "legacy_plaintext":
        question.correct_answer = "A"
    else:
        monkeypatch.setattr(Question, "get_decrypted_correct_answer", lambda self: None)
    world.db.commit()
    world.user = world.owner
    preview = world.client.get(f"/api/assessments/{quiz_id}")
    assert (
        preview.status_code == 200
        and preview.json()["questions"][0]["correct_answer"] is None
    )
    publish = world.client.post(f"/api/assessments/{quiz_id}/publish")
    assert publish.status_code == 422
    world.user = world.learner
    result, _ = attempt(
        world, quiz_id, [{"question_id": question.id, "response_text": answer}]
    )
    assert (
        result["status"] == "submitted"
        and result["score"] is None
        and result["needs_review"]
    )
    response = world.db.query(QuestionResponse).one()
    assert response.score is None and response.is_correct is None
    assert "teacher review" in response.feedback.lower()
