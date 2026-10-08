"""Offline regressions for returned assessment traceability and system notices."""
from datetime import timedelta

import pytest

from src.core.models import Assessment, Content, ContentType, StudyPlan, StudentStudyPlan, Submission
from src.core.services.temporal_service import utc_now
from tests.integration.test_trustworthy_scoring_sessions import create_quiz, world as scoring_world

world = scoring_world


def test_assessment_links_round_trip_update_clear_and_reject_foreign_resources(world):
    world.user = world.owner
    result = world.client.post('/api/assessments/', json={
        'title': 'Linked draft', 'study_plan_id': world.content.study_plan_id,
        'topic_id': world.content.id,
    })
    path = f"/api/assessments/{result.json()['id']}"
    detail = world.client.get(path).json()
    assert detail['study_plan_id'] == world.content.study_plan_id
    assert detail['topic_id'] == world.content.id
    assert world.client.put(path, json={'title': 'Same links'}).status_code == 200
    assert world.client.get(path).json()['topic_id'] == world.content.id
    assert world.client.put(path, json={'study_plan_id': None, 'topic_id': None}).status_code == 200
    detail = world.client.get(path).json()
    assert detail['study_plan_id'] is None and detail['topic_id'] is None
    foreign_plan = StudyPlan(title='Other author', creator_id=world.other.id)
    foreign_content = Content(title='Other private material', creator_id=world.other.id, content_type=ContentType.LESSON)
    world.db.add_all([foreign_plan, foreign_content])
    world.db.commit()
    for changes in ({'study_plan_id': foreign_plan.id}, {'topic_id': foreign_content.id}):
        assert world.client.put(path, json=changes).status_code == 403
        assert world.client.get(path).json() == detail
    assert world.client.put(path, json={'study_plan_id': world.content.study_plan_id, 'topic_id': world.content.id}).status_code == 200
    assert world.client.get(path).json()['topic_id'] == world.content.id


@pytest.mark.parametrize('with_attempt', [False, True])
def test_link_edits_respect_attempt_and_assigned_publication_immutability(world, with_attempt):
    quiz_id, _ = create_quiz(world, study_plan_id=world.content.study_plan_id)
    if with_attempt:
        assert world.client.post(f'/api/assessments/{quiz_id}/start').status_code == 200
    else:
        world.db.add(StudentStudyPlan(student_id=world.learner.id, study_plan_id=world.content.study_plan_id))
        world.db.commit()
    world.user = world.owner
    for changes in ({'study_plan_id': None}, {'topic_id': world.content.id}):
        assert world.client.put(f'/api/assessments/{quiz_id}', json=changes).status_code == 409
    world.db.refresh(world.db.get(Assessment, quiz_id))
    assert world.db.get(Assessment, quiz_id).study_plan_id == world.content.study_plan_id


@pytest.mark.parametrize('kind,legacy', [
    ('attempt_time_exceeded', 'Time limit exceeded. Answers preserved for teacher review.'),
    ('attempt_timezone_unknown', 'Original attempt timezone unknown. Answers preserved for teacher review.'),
    ('attempt_closed', 'Attempt explicitly closed without submission or grade. The reserved attempt remains consumed.'),
])
def test_system_notices_are_separate_and_survive_teacher_feedback(world, kind, legacy):
    quiz_id, questions = create_quiz(world, time_limit_minutes=1)
    started = world.client.post(f'/api/assessments/{quiz_id}/start').json()
    stored = world.db.get(Submission, started['id'])
    if kind == 'attempt_time_exceeded':
        stored.started_at = utc_now() - timedelta(minutes=2)
    elif kind == 'attempt_timezone_unknown':
        stored.started_at = utc_now().replace(tzinfo=None)
    world.db.commit()
    path = f"/api/assessments/submissions/{started['id']}"
    if kind == 'attempt_closed':
        assert world.client.post(path + '/close', json={'reason': 'abandoned'}).status_code == 200
    else:
        assert world.client.post(f'/api/assessments/{quiz_id}/submit', json={
            'submission_id': started['id'], 'answers': [{'question_id': questions[0]['id'], 'response_text': 'A'}],
        }).status_code == 200
    detail = world.client.get(path).json()
    assert detail['system_notices'] == [kind]
    assert detail['feedback'] is None
    world.db.refresh(stored)
    assert stored.feedback is None
    # Narrow read compatibility for pre-fix rows; no rewriting of old records.
    stored.feedback = legacy
    world.db.commit()
    assert world.client.get(path).json()['feedback'] is None
    world.db.refresh(stored)
    assert stored.feedback == legacy
    if kind != 'attempt_closed':
        world.user = world.owner
        assert world.client.post(path + '/grade', json={'score': 10, 'feedback': 'Revisado por el docente.'}).status_code == 200
        detail = world.client.get(path).json()
        assert detail['system_notices'] == [kind]
        assert detail['feedback'] == 'Revisado por el docente.'


def test_teacher_rubric_breakdown_survives_saved_grade_and_learner_read(world):
    quiz_id, questions = create_quiz(world, grading_mode='manual', questions=[{
        'question_text': 'Read two fifths', 'question_type': 'short_answer', 'points': 5,
    }], rubric={'name': 'Lectura de 2/5', 'criteria': [
        {'name': 'Numerador', 'max_points': 2}, {'name': 'Denominador', 'max_points': 2},
        {'name': 'Partes iguales', 'max_points': 1},
    ]})
    started = world.client.post(f'/api/assessments/{quiz_id}/start').json()
    assert world.client.post(f'/api/assessments/{quiz_id}/submit', json={
        'submission_id': started['id'], 'answers': [{'question_id': questions[0]['id'], 'response_text': 'Mi respuesta'}],
    }).status_code == 200
    path = f"/api/assessments/submissions/{started['id']}"
    response_id = world.client.get(path).json()['answers'][0]['response_id']
    feedback = 'Comentario docente.\n\nDesglose de rúbrica: Lectura de 2/5\n- Numerador: 2 / 2\n- Denominador: 1 / 2\n- Partes iguales: 0 / 1'
    world.user = world.owner
    assert world.client.post(f'{path}/responses/{response_id}/grade', json={'score': 3, 'feedback': feedback}).status_code == 200
    for user in (world.owner, world.learner):
        world.user = user
        detail = world.client.get(path).json()
        assert detail['score'] == 3 and detail['status'] == 'graded'
        assert detail['answers'][0]['feedback'] == feedback
        assert detail['system_notices'] == []


def test_legacy_notice_matching_never_strips_unrelated_or_extended_teacher_text(world):
    quiz_id, questions = create_quiz(world, time_limit_minutes=1)
    started = world.client.post(f'/api/assessments/{quiz_id}/start').json()
    assert world.client.post(f'/api/assessments/{quiz_id}/submit', json={
        'submission_id': started['id'], 'answers': [{'question_id': questions[0]['id'], 'response_text': 'A'}],
    }).status_code == 200
    stored = world.db.get(Submission, started['id'])
    stored.feedback = 'Time limit exceeded. Answers preserved for teacher review.'
    world.db.commit()
    path = f"/api/assessments/submissions/{stored.id}"
    detail = world.client.get(path).json()
    assert detail['system_notices'] == []
    assert detail['feedback'] == stored.feedback
    stored.started_at = utc_now() - timedelta(minutes=2)
    stored.feedback += '\nTeacher-specific clarification.'
    world.db.commit()
    detail = world.client.get(path).json()
    assert detail['system_notices'] == ['attempt_time_exceeded']
    assert detail['feedback'] == stored.feedback


@pytest.mark.parametrize('source,notice', [
    ('Unanswered question: zero points.', 'question_unanswered'),
    ('Answer key unavailable; teacher review required.', 'answer_key_unavailable'),
    ('Automatic grading was unavailable or invalid. Teacher review is required.', 'automatic_grading_unavailable'),
])
def test_fixed_question_messages_have_typed_provenance_not_teacher_feedback(world, source, notice):
    quiz_id, questions = create_quiz(world, grading_mode='manual')
    started = world.client.post(f'/api/assessments/{quiz_id}/start').json()
    assert world.client.post(f'/api/assessments/{quiz_id}/submit', json={
        'submission_id': started['id'], 'answers': [],
    }).status_code == 200
    stored = world.db.get(Submission, started['id']).responses[0]
    if notice == 'automatic_grading_unavailable':
        stored.feedback = None
        stored.score = None
        stored.ai_suggested_feedback = source
    else:
        stored.feedback = source
        stored.score = 0 if notice == 'question_unanswered' else None
    world.db.commit()
    path = f"/api/assessments/submissions/{started['id']}"
    detail = world.client.get(path).json()['answers'][0]
    assert detail['system_notices'] == [notice]
    assert detail['feedback'] is None
    assert detail['ai_suggested_feedback'] is None
    # A teacher's explicitly saved text, even when identical, stays verbatim.
    world.user = world.owner
    assert world.client.post(f"{path}/responses/{stored.id}/grade", json={'score': 0, 'feedback': source}).status_code == 200
    reviewed = world.client.get(path).json()['answers'][0]
    assert reviewed['feedback'] == source
    assert reviewed['system_notices'] == []


def test_teacher_saved_exact_legacy_wording_is_retained_with_an_authorship_notice(world):
    quiz_id, questions = create_quiz(world, time_limit_minutes=1)
    started = world.client.post(f'/api/assessments/{quiz_id}/start').json()
    stored = world.db.get(Submission, started['id'])
    stored.started_at = utc_now() - timedelta(minutes=2)
    world.db.commit()
    world.client.post(f'/api/assessments/{quiz_id}/submit', json={
        'submission_id': started['id'], 'answers': [{'question_id': questions[0]['id'], 'response_text': 'A'}],
    })
    path = f"/api/assessments/submissions/{stored.id}"
    feedback = 'Time limit exceeded. Answers preserved for teacher review.'
    world.user = world.owner
    assert world.client.post(path + '/grade', json={'score': 10, 'feedback': feedback}).status_code == 200
    detail = world.client.get(path).json()
    assert detail['feedback'] == feedback
    assert detail['system_notices'] == ['attempt_time_exceeded', 'legacy_feedback_unattributed']


def test_author_link_identifiers_are_not_exposed_to_learners(world):
    quiz_id, _ = create_quiz(world, study_plan_id=world.content.study_plan_id, topic_id=world.content.id)
    path = f'/api/assessments/{quiz_id}'
    assert world.user == world.learner
    learner = world.client.get(path)
    assert learner.status_code == 200
    assert learner.json()['study_plan_id'] is None
    assert learner.json()['topic_id'] is None
    world.user = world.owner
    author = world.client.get(path).json()
    assert author['study_plan_id'] == world.content.study_plan_id
    assert author['topic_id'] == world.content.id
