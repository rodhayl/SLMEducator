"""Transferred profile and notes remain restricted; private notes are preserved."""

from tests.trust.test_resource_contracts import scenario, synthetic_credentials  # noqa: F401,F811


def test_transfer_preserves_own_notes_without_cross_teacher_or_profile_access(scenario):  # noqa: F811
    client, db, users, selected, *_ = scenario
    outgoing, incoming, student = users['teacher_a'], users['teacher_b'], users['learner_a']
    selected[0] = outgoing
    path = f'/api/students/{student.id}/notes'
    assert client.post(path, json={'notes': 'Outgoing teacher private observation'}).status_code == 200
    student.teacher_id = incoming.id
    db.commit()
    assert client.get(f'/api/auth/users/{student.id}').status_code == 404
    assert client.get(f'/api/students/{student.id}/progress').status_code == 403
    assert client.post(path, json={'notes': 'Must not overwrite'}).status_code == 403
    assert client.get(path).status_code == 403
    db.refresh(outgoing)
    assert outgoing.settings[f'student_notes_{student.id}'] == 'Outgoing teacher private observation'
    selected[0] = incoming
    assert client.get(path).json() == {'notes': ''}
    assert client.get(f'/api/auth/users/{student.id}').status_code == 200
    selected[0] = student
    assert client.get(path).status_code == 403
