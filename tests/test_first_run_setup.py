"""Local first-admin admission uses synthetic isolated databases, never HTTP."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

from scripts import seed_admin
from src import first_run_setup, starter, starter_headless
from src.core.models import AuditLog, User, UserRole
from src.core.services.database import DatabaseService
from src.core.security import verify_password

PASSWORD = 'SyntheticBootstrap123!'


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'first-run.sqlite3'
    monkeypatch.setenv('SLM_DB_PATH', str(path))
    return path


def test_fresh_setup_then_second_attempt_and_removed_admin_stay_closed(isolated):
    assert seed_admin.prepare_first_run() == 'needed'
    seed_admin.create_first_admin('local.owner', PASSWORD, PASSWORD)
    assert seed_admin.prepare_first_run() == 'configured'
    with DatabaseService().get_session() as session:
        owner = session.query(User).one()
        assert owner.username == 'local.owner'
        assert verify_password(PASSWORD, owner.password_hash)
        assert owner.role == UserRole.ADMIN
        session.delete(owner)
        session.commit()
    assert seed_admin.prepare_first_run() == 'recovery'
    with pytest.raises(ValueError, match='closed'):
        seed_admin.create_first_admin('other.owner', PASSWORD, PASSWORD)


def test_two_local_setup_submits_create_exactly_one_admin(isolated):
    assert seed_admin.prepare_first_run() == 'needed'
    def submit(index):
        try:
            seed_admin.create_first_admin(f'owner.{index}', PASSWORD, PASSWORD)
            return 'created'
        except ValueError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, range(2)))
    assert sorted(results) == ['closed', 'created']
    database = DatabaseService()
    try:
        with database.get_session() as session:
            assert session.query(User).count() == 1
            assert session.query(AuditLog).one().details['state'] == 'complete'
    finally:
        database.close()


@pytest.mark.parametrize(('username', 'password', 'repeat', 'error'), [
    ('x', PASSWORD, PASSWORD, 'username'), ('valid.owner', 'short', 'short', 'password'),
    ('valid.owner', 'a' * 13, 'a' * 13, 'password'),
    ('valid.owner', PASSWORD, PASSWORD + 'x', 'repeat'),
    ('valid.owner', 'É' * 40 + 'Aa1!', 'É' * 40 + 'Aa1!', 'password'),
])
def test_invalid_input_preserves_pending_database(isolated, username, password, repeat, error):
    assert seed_admin.prepare_first_run() == 'needed'
    with pytest.raises(ValueError, match=error):
        seed_admin.create_first_admin(username, password, repeat)
    assert seed_admin.prepare_first_run() == 'needed'


@pytest.mark.parametrize('role', [UserRole.ADMIN, UserRole.TEACHER])
def test_existing_accounts_are_unchanged_without_new_bootstrap_marker(isolated, role):
    database = DatabaseService()
    try:
        with database.get_session() as session:
            session.add(User(username='existing', email='existing@example.invalid', password_hash='unchanged',
                             role=role, first_name='Existing', last_name='Account', active=False, failed_login_count=4, settings={'preserve': 'private fixture'}))
            session.commit()
        assert seed_admin.prepare_first_run() == ('configured' if role == UserRole.ADMIN else 'recovery')
        with pytest.raises(ValueError, match='closed'):
            seed_admin.create_first_admin('other.owner', PASSWORD, PASSWORD)
        with database.get_session() as session:
            existing = session.query(User).one()
            assert existing.password_hash == 'unchanged' and existing.failed_login_count == 4
            assert existing.settings == {'preserve': 'private fixture'} and existing.active is False
            assert session.query(AuditLog).count() == 0
    finally:
        database.close()


def test_existing_empty_database_is_not_mistaken_for_new_install(isolated):
    database = DatabaseService()
    database.close()
    assert seed_admin.prepare_first_run() == 'recovery'


def test_cancelled_setup_starts_no_native_or_headless_server(monkeypatch):
    for module in (starter, starter_headless):
        monkeypatch.setattr(module, 'setup_frozen_working_directory', lambda: None)
        monkeypatch.setattr(module, 'setup_frozen_logging', lambda: None)
        monkeypatch.setattr(module, 'ensure_initial_admin', lambda **kwargs: False)
    monkeypatch.setattr(starter.sys, 'argv', ['starter'])
    monkeypatch.setattr(starter, 'log_message', lambda message: None)
    def forbidden(*args, **kwargs):
        raise AssertionError('No process or UI launch before setup completes')
    monkeypatch.setattr(starter, 'ServerControlWindow', forbidden)
    monkeypatch.setattr(starter, 'run_console', forbidden)
    monkeypatch.setattr(starter_headless, 'run_console', forbidden)
    assert starter.main() == 1
    assert starter_headless.main() == 1


def test_noninteractive_setup_never_reads_passwords(isolated, monkeypatch, capsys):
    monkeypatch.setattr(first_run_setup.sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(first_run_setup.getpass, 'getpass', lambda *a: pytest.fail('No redirected secret entry'))
    assert first_run_setup.ensure_initial_admin(gui=False, language='en') is False
    assert 'Redirected password input is not supported' in capsys.readouterr().out
    assert seed_admin.prepare_first_run() == 'needed'


def test_native_errors_are_allowlisted_and_password_fields_are_masked():
    assert first_run_setup._error_key(RuntimeError('sensitive payload')) == 'failed'
    assert first_run_setup._error_key(ValueError('repeat')) == 'invalid_repeat'
    source = Path(first_run_setup.__file__).read_text()
    assert "show='' if key == 'username' else '•'" in source
    assert 'create_first_admin' in source and 'HTTPServer' not in source


def test_concurrent_preparation_publishes_one_complete_database(isolated, monkeypatch):
    from threading import Barrier
    import sqlite3
    barrier = Barrier(2)
    original = seed_admin._prepare_candidate
    def prepared(path):
        original(path)
        assert not Path(str(path) + '-wal').exists()
        assert not Path(str(path) + '-shm').exists()
        with sqlite3.connect(path) as connection:
            assert connection.execute('PRAGMA journal_mode').fetchone()[0] == 'delete'
        connection.close()
        barrier.wait(timeout=10)
    monkeypatch.setattr(seed_admin, '_prepare_candidate', prepared)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: seed_admin.prepare_first_run(), range(2)))
    assert results == ['needed', 'needed']
    assert isolated.exists()
    assert not list(isolated.parent.glob('.slm-first-run-*'))
    database = DatabaseService()
    try:
        with database.get_session() as session:
            assert session.query(User).count() == 0
            assert session.query(AuditLog).count() == 1
    finally:
        database.close()


def test_interruption_before_marker_commit_leaves_no_final_database(isolated, monkeypatch):
    from sqlalchemy.orm import Session
    with monkeypatch.context() as patch:
        def interrupted(self):
            raise RuntimeError('Synthetic interruption before marker')
        patch.setattr(Session, 'commit', interrupted)
        with pytest.raises(RuntimeError, match='Synthetic interruption'):
            seed_admin.prepare_first_run()
    assert not isolated.exists()
    assert not list(isolated.parent.glob('.slm-first-run-*'))
    assert seed_admin.prepare_first_run() == 'needed'


def test_interruption_before_publication_leaves_no_final_database(isolated, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(seed_admin.os, 'link', lambda *a: (_ for _ in ()).throw(OSError('Synthetic no publication')))
        with pytest.raises(OSError, match='Synthetic no publication'):
            seed_admin.prepare_first_run()
    assert not isolated.exists()
    assert not list(isolated.parent.glob('.slm-first-run-*'))
    assert seed_admin.prepare_first_run() == 'needed'


def test_existing_empty_file_and_race_winner_are_never_initialized(isolated, monkeypatch):
    link = seed_admin.os.link
    def winner(source, destination):
        Path(destination).write_bytes(b'')
        return link(source, destination)
    with monkeypatch.context() as patch:
        patch.setattr(seed_admin.os, 'link', winner)
        assert seed_admin.prepare_first_run() == 'recovery'
    assert isolated.read_bytes() == b''
    assert seed_admin.prepare_first_run() == 'recovery'
    assert isolated.read_bytes() == b''
    assert not list(isolated.parent.glob('.slm-first-run-*'))


def test_direct_creation_never_initializes_an_unprepared_database(isolated):
    with pytest.raises(ValueError, match='closed'):
        seed_admin.create_first_admin('owner', PASSWORD, PASSWORD)
    assert not isolated.exists()
