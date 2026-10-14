"""Real authentication and endpoints; only final AI transport is synthetic."""
from datetime import datetime
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from scripts.seed_admin import seed_admin_user
from src.core.models import User, UserRole, AIModelConfiguration, HelpRequest, TeacherMessage
from src.core.models.models import TutorQuestion, TutorReply, SharedAIConfiguration
from src.core.services.ai_service import AIService, AIResponse, AIProvider

PASSWORD = "SyntheticPass123!"


@pytest.fixture
def test_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def world(db_service, monkeypatch):
    from src.api.main import app
    from src.core.services import ai_request_lifecycle as lifecycle
    lifecycle._RECORDS.clear()
    lifecycle._ACTIVE.clear()
    assert not app.dependency_overrides
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("SLM_INITIAL_ADMIN_EMAIL", "admin.demo@example.com")
    assert seed_admin_user() == 0
    client = TestClient(app)
    def login(name):
        response = client.post('/api/auth/login', data={'username':name,'password':PASSWORD})
        assert response.status_code == 200, response.text
        return {'Authorization':'Bearer '+response.json()['access_token']}
    headers = {'admin':login('admin')}
    ids = {}
    for name, role in [('teacher_a','teacher'),('teacher_b','teacher'),('learner_a','student'),('learner_b','student')]:
        response = client.post('/api/auth/register',headers=headers['admin'],json={
            'username':name,'email':name+'@example.com','password':PASSWORD,
            'first_name':'Synthetic','last_name':name,'role':role,
            'teacher_id':ids.get('teacher_a') if name=='learner_a' else None})
        assert response.status_code == 200, response.text
        ids[name]=response.json()['id']
        headers[name]=login(name)
    calls=[]
    def final_transport(self, prompt, *args, **kwargs):
        calls.append((self.config.provider,self.config.model,prompt))
        return AIResponse(content='{"explanation":"Synthetic answer"}',tokens_used=3,
                          model=self.config.model,provider=AIProvider.OLLAMA,response_time=0,timestamp=datetime.now())
    monkeypatch.setattr(AIService,'_call_ai',final_transport)
    yield client,headers,ids,db_service,calls
    client.close()


def configure(world):
    client,headers,*_=world
    response=client.post('/api/settings/ai',headers=headers['admin'],json={'provider':'ollama','model':'installation-synthetic','endpoint':'http://127.0.0.1:11434'})
    assert response.status_code==200,response.text
    assert response.json()['api_key'] is None


def ask(world, name='learner_b', **extra):
    client,headers,*_=world
    return client.post('/api/questions/ask',headers=headers[name],json={
        'client_request_id':str(uuid4()),'question':'Synthetic geography question','assistance':'explanation',**extra})


def test_admin_global_and_real_unassigned_student(world):
    client,headers,ids,service,calls=world
    assert ask(world).status_code==409
    assert client.get('/api/questions',headers=headers['learner_b']).json()[0]['question']
    configure(world)
    for name in ['learner_b','learner_a','teacher_a']:
        response=ask(world,name)
        assert response.status_code==200,response.text
        assert response.json()['response']=='Synthetic answer'
        assert response.json()['receipt']['model']=='installation-synthetic'
    assert len(calls)==3
    for name in ['teacher_a','learner_a','learner_b']:
        for method,path in [('get','/api/settings/ai'),('post','/api/settings/ai'),('get','/api/settings/ai/models'),('post','/api/settings/ai/test'),('get','/api/settings/ai/test')]:
            kwargs={'headers':headers[name]}
            if method=='post':kwargs['json']={'provider':'ollama','model':'forbidden'}
            assert getattr(client,method)(path,**kwargs).status_code==403
    assert len(calls)==3
    thread=client.get('/api/questions',headers=headers['learner_b']).json()[0]
    assert not thread['can_request_teacher']
    assert client.post(f"/api/questions/{thread['id']}/teacher",headers=headers['learner_b'],json={'teacher_id':ids['teacher_a'],'client_request_id':'share-once'}).status_code==409
    assert client.post('/api/classroom/help',headers=headers['learner_b'],json={'subject':'x','description':'x'}).status_code==410


def test_persisted_replay_and_teacher_revocation(world):
    client,headers,ids,service,calls=world
    configure(world)
    request_id=str(uuid4())
    first=ask(world,'learner_a',client_request_id=request_id)
    assert first.status_code==200,first.text
    qid=first.json()['question_id']
    assert ask(world,'learner_a',client_request_id=request_id).json()==first.json()
    assert len(calls)==1
    from src.core.services import ai_request_lifecycle as lifecycle
    lifecycle._RECORDS.clear()
    assert ask(world,'learner_a',client_request_id=request_id).json()==first.json()
    assert len(calls)==1
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_a']).status_code==404
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json={'teacher_id':ids['teacher_a'],'client_request_id':'share-once'}).status_code==200
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_a']).status_code==200
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_b']).status_code==404
    assert client.get(f'/api/questions/{qid}',headers=headers['learner_b']).status_code==404
    reply={'client_request_id':str(uuid4()),'body':'Teacher explanation'}
    for _ in range(2):
        result=client.post(f'/api/questions/{qid}/reply',headers=headers['teacher_a'],json=reply)
        assert result.status_code==200,result.text
        assert len(result.json()['replies'])==2
    with service.get_session() as db:
        db.get(User,ids['learner_a']).teacher_id=None
        db.commit()
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json={'teacher_id':ids['teacher_a'],'client_request_id':'share-once'}).status_code==409
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_a']).status_code==404
    assert client.post(f'/api/questions/{qid}/reply',headers=headers['teacher_a'],json=reply).status_code==404
    assert len(client.get(f'/api/questions/{qid}',headers=headers['learner_a']).json()['replies'])==2


def test_ambiguous_admin_configs_require_explicit_choice(world):
    client,headers,ids,service,calls=world
    with service.get_session() as db:
        admin=db.query(User).filter_by(role=UserRole.ADMIN).one()
        for name in ['old-one','old-two']:
            db.add(AIModelConfiguration(user_id=admin.id,provider='ollama',model=name))
        db.commit()
    assert client.get('/api/settings/ai',headers=headers['admin']).status_code==409
    assert ask(world).status_code==409
    assert not calls
    configure(world)
    assert ask(world).status_code==200
    with service.get_session() as db:
        assert db.query(AIModelConfiguration).count()==3
        assert db.get(SharedAIConfiguration,1)


def test_pending_legacy_migration_preserves_orphan_and_messages(world):
    client,headers,ids,service,calls=world
    with service.get_session() as db:
        assigned=HelpRequest(student_id=ids['learner_a'],request_text='Legacy assigned question',status='open')
        orphan=HelpRequest(student_id=ids['learner_b'],request_text='Legacy orphan question',status='open')
        db.add_all([assigned,orphan,TeacherMessage(from_id=ids['teacher_a'],to_id=ids['learner_a'],subject='Unlinked',content='Not a verified thread reply')])
        db.commit()
    from src.core.services.schema_migrations import reconcile_connection
    with service.engine.begin() as connection:
        reconcile_connection(connection)
        reconcile_connection(connection)
    with service.get_session() as db:
        assert db.query(HelpRequest).count()==2
        assert db.query(TeacherMessage).count()==1
        assert db.query(TutorQuestion).count()==1
        assert db.query(TutorReply).count()==0
    queue=client.get('/api/questions',headers=headers['teacher_a']).json()
    assert len(queue)==1 and queue[0]['question']=='Legacy assigned question'
    assert client.get('/api/questions',headers=headers['learner_b']).json()==[]


def test_teacher_target_and_retries_cannot_reroute_or_reopen(world):
    client,headers,ids,service,calls=world
    configure(world)
    response=ask(world,'learner_a')
    qid=response.json()['question_id']
    target={'teacher_id':ids['teacher_a'],'client_request_id':'share-a'}
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json=target).status_code==200
    reply={'client_request_id':'reply-a','body':'Teacher answer'}
    assert client.post(f'/api/questions/{qid}/reply',headers=headers['teacher_a'],json=reply).status_code==200
    assert client.post(f'/api/questions/{qid}/resolve',headers=headers['learner_a']).status_code==200
    assert client.post(f'/api/questions/{qid}/reply',headers=headers['teacher_a'],json=reply).json()['teacher_status']=='resolved'
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json=target).json()['teacher_status']=='resolved'
    with service.get_session() as db:
        db.get(User,ids['learner_a']).teacher_id=ids['teacher_b']
        db.commit()
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json={**target,'client_request_id':'new-confirmation'}).status_code==409
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_b']).status_code==404
    new_target={'teacher_id':ids['teacher_b'],'client_request_id':'share-b'}
    assert client.post(f'/api/questions/{qid}/teacher',headers=headers['learner_a'],json=new_target).status_code==200
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_b']).status_code==200
    assert client.get(f'/api/questions/{qid}',headers=headers['teacher_a']).status_code==404


def test_definite_failures_preserve_question_and_do_not_fabricate_reply(world,monkeypatch):
    client,headers,ids,service,calls=world
    configure(world)
    def unavailable(*args,**kwargs):
        raise RuntimeError('Synthetic provider failure')
    monkeypatch.setattr(AIService,'_call_ai',unavailable)
    response=ask(world)
    assert response.status_code==200,response.text
    assert response.json()['receipt']['status']!='completed'
    qid=response.json()['question_id']
    saved=client.get(f'/api/questions/{qid}',headers=headers['learner_b']).json()
    assert saved['question']=='Synthetic geography question' and saved['replies']==[]
    with service.get_session() as db:
        db.get(TutorQuestion,qid).question='Legacy '+('x'*5000)
        db.commit()
    response=client.post(f'/api/questions/{qid}/ai',headers=headers['learner_b'],json={'client_request_id':'long-legacy','assistance':'explanation'})
    assert response.status_code==422
    assert len(client.get(f'/api/questions/{qid}',headers=headers['learner_b']).json()['question'])>4000


def test_capabilities_are_redacted_and_respect_active_assignment(world):
    client,headers,ids,service,calls=world
    assert client.get('/api/questions/capabilities',headers=headers['learner_b']).json()=={
        'ai_configured':False,'teacher_available':False,'teacher_name':None,'assigned_teacher_id':None}
    configure(world)
    caps=client.get('/api/questions/capabilities',headers=headers['learner_a']).json()
    assert caps['ai_configured'] and caps['assigned_teacher_id']==ids['teacher_a']
    assert set(caps)=={'ai_configured','teacher_available','teacher_name','assigned_teacher_id'}
    with service.get_session() as db:
        db.get(User,ids['teacher_a']).active=False
        db.commit()
    assert not client.get('/api/questions/capabilities',headers=headers['learner_a']).json()['teacher_available']


def test_copy_first_upgrade_preserves_source_bytes_and_encrypted_backup(world,tmp_path):
    import os
    import sqlite3
    import hashlib
    from src.core.services.recovery_service import upgrade_database, restore_backup
    client,headers,ids,service,calls=world
    with service.get_session() as db:
        db.add(HelpRequest(student_id=ids['learner_a'],request_text='Pending preserved',status='pending'))
        db.add(HelpRequest(student_id=ids['learner_b'],request_text='Orphan preserved',status='pending'))
        db.commit()
    source=tmp_path/'old-installation.db'
    with sqlite3.connect(service.engine.url.database) as live,sqlite3.connect(source) as copy:
        live.backup(copy)
        copy.executescript('DROP TABLE tutor_replies; DROP TABLE tutor_questions; DROP TABLE shared_ai_configuration;')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    output=tmp_path/'upgraded.db';archive=tmp_path/'encrypted-backup.json'
    key=os.environ['SLM_ENCRYPTION_KEY'].encode()
    upgrade_database(source,output,archive,key)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    with sqlite3.connect(output) as db:
        assert db.execute('SELECT COUNT(*) FROM help_requests').fetchone()[0]==2
        assert db.execute('SELECT question FROM tutor_questions').fetchall()==[('Pending preserved',)]
    restored=tmp_path/'restored-source.db'
    restore_backup(archive.read_bytes(),restored,key)
    with sqlite3.connect(restored) as db:
        assert db.execute('SELECT COUNT(*) FROM help_requests').fetchone()[0]==2
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='tutor_questions'").fetchall()


def test_unified_question_revision_is_resolvable_by_alembic():
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from src.core.services.schema_migrations import REVISION
    root = Path(__file__).resolve().parents[2]
    configuration = Config(str(root / "alembic.ini"))
    configuration.set_main_option("script_location", str(root / "alembic"))
    assert ScriptDirectory.from_config(configuration).get_current_head() == REVISION


@pytest.mark.parametrize(("source_kind", "revocation"), [("content", "enrollment"), ("course", "enrollment"), ("course", "removed_item")])
def test_saved_source_snapshot_respects_revoked_content_access(world, source_kind, revocation):
    from src.core.models import Content, ContentType, StudyPlan, StudyPlanContent, StudentStudyPlan
    client, headers, ids, service, calls = world
    configure(world)
    with service.get_session() as db:
        plan = StudyPlan(title='Private synthetic source', creator_id=ids['teacher_a'], phases=[], is_public=False)
        db.add(plan)
        db.flush()
        content = Content(title='Restricted source', creator_id=ids['teacher_a'], study_plan_id=plan.id, content_type=ContentType.LESSON)
        content.set_encrypted_content_data({'content': 'SOURCE_ACCESS_MARKER: equal parts.'})
        db.add(content)
        db.flush()
        db.add(StudyPlanContent(study_plan_id=plan.id, content_id=content.id, phase_index=0, order_index=0))
        db.add(StudentStudyPlan(student_id=ids['learner_a'], study_plan_id=plan.id, progress={}))
        other = Content(title='Still assigned source', creator_id=ids['teacher_a'], study_plan_id=plan.id, content_type=ContentType.LESSON)
        other.set_encrypted_content_data({'content': 'Still accessible synthetic material.'})
        db.add(other)
        db.flush()
        db.add(StudyPlanContent(study_plan_id=plan.id, content_id=other.id, phase_index=0, order_index=1))
        db.commit()
        plan_id, content_id = plan.id, content.id
    request_id = 'saved-source-access'
    context = {'content_id': content_id if source_kind == 'content' else None, 'study_plan_id': plan_id}
    result = ask(world, 'learner_a', client_request_id=request_id, **context)
    assert result.status_code == 200, result.text
    qid = result.json()['question_id']
    assert 'SOURCE_ACCESS_MARKER' in client.get(f'/api/questions/{qid}', headers=headers['learner_a']).text
    # A changed version is still readable history while source access remains.
    with service.get_session() as db:
        db.get(Content, content_id).set_encrypted_content_data({'content': 'A revised source without the original marker.'})
        db.commit()
    assert 'SOURCE_ACCESS_MARKER' in client.get(f'/api/questions/{qid}', headers=headers['learner_a']).text
    changed = ask(world, 'learner_a', client_request_id=request_id, **context)
    assert changed.status_code == 409 and 'SOURCE_ACCESS_MARKER' not in changed.text
    with service.get_session() as db:
        if revocation == 'enrollment':
            db.query(StudentStudyPlan).filter_by(student_id=ids['learner_a'], study_plan_id=plan_id).delete()
        else:
            db.query(StudyPlanContent).filter_by(content_id=content_id, study_plan_id=plan_id).delete()
            db.get(Content, content_id).study_plan_id = None
        db.commit()
    assert client.get(f'/api/content/{content_id}', headers=headers['learner_a']).status_code == 403
    replay = ask(world, 'learner_a', client_request_id=request_id, **context)
    assert replay.status_code in (403, 409) and 'SOURCE_ACCESS_MARKER' not in replay.text
    saved = client.get(f'/api/questions/{qid}', headers=headers['learner_a'])
    assert saved.status_code == 200
    assert saved.json()['replies'][0]['body'] == 'Synthetic answer'
    assert 'SOURCE_ACCESS_MARKER' not in saved.text
    assert 'SOURCE_ACCESS_MARKER' not in client.get('/api/questions', headers=headers['learner_a']).text
    with service.get_session() as db:
        receipt = db.query(TutorReply).filter_by(question_id=qid).one().receipt
        assert 'SOURCE_ACCESS_MARKER' in receipt['response']['source']['content_data']


def test_question_cancel_suppresses_late_reply_and_preserves_saved_question(world, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    client, headers, ids, service, calls = world
    configure(world)
    entered, release = Event(), Event()
    original = AIService._call_ai
    def blocked(self, *args, **kwargs):
        entered.set()
        assert release.wait(10), 'Synthetic test transport was not released'
        return original(self, *args, **kwargs)
    monkeypatch.setattr(AIService, '_call_ai', blocked)
    request_id = 'cancel-saved-question'
    with ThreadPoolExecutor(max_workers=1) as worker:
        response = worker.submit(ask, world, 'learner_b', client_request_id=request_id)
        try:
            assert entered.wait(5)
            denied = client.post(f'/api/ai/requests/{request_id}/cancel', headers=headers['learner_a'])
            assert denied.status_code == 404
            cancelled = client.post(f'/api/ai/requests/{request_id}/cancel', headers=headers['learner_b'])
            assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
        finally:
            release.set()
        result = response.result(timeout=10)
    assert result.status_code == 200, result.text
    qid = result.json()['question_id']
    assert result.json()['receipt']['status'] == 'cancelled'
    saved = client.get(f'/api/questions/{qid}', headers=headers['learner_b']).json()
    assert saved['question'] == 'Synthetic geography question' and saved['replies'] == []
    repeat = ask(world, 'learner_b', client_request_id=request_id)
    assert repeat.status_code == 200 and repeat.json()['receipt']['status'] == 'cancelled'
    assert len(calls) == 1
