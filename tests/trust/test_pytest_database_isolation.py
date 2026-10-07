"""Real nested pytest lifecycle uses synthetic paths, including during collection."""

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("collect_only", [True, False])
def test_collection_and_teardown_never_select_default_database(tmp_path, collect_only):
    """Protect collection, per-test isolation, between-test fallback and restoration."""
    probe = tmp_path / "test_isolated_probe.py"
    probe.write_text(textwrap.dedent("""
        import os
        from pathlib import Path
        from src.core.services.database import DatabaseService

        collection_path = Path(os.environ['SLM_DB_PATH'])
        assert collection_path.is_absolute()
        assert collection_path.name == 'collection.sqlite3'
        assert collection_path.parent.name.startswith('slm-pytest-collection-')
        database = DatabaseService()
        try:
            assert database.db_path == collection_path
        finally:
            database.close()

        test_paths = []

        def test_first(test_db_path, monkeypatch):
            assert Path(os.environ['SLM_DB_PATH']) == test_db_path
            assert test_db_path != collection_path
            test_paths.append(test_db_path)
            monkeypatch.setenv('SLM_DB_PATH', str(test_db_path.parent / 'changed-by-test.sqlite3'))
            monkeypatch.setenv('SLM_LOG_DIR', str(test_db_path.parent / 'changed-logs'))

        def test_second(test_db_path):
            assert Path(os.environ['SLM_DB_PATH']) == test_db_path
            assert test_db_path != collection_path
            assert test_db_path not in test_paths
            test_paths.append(test_db_path)
    """), encoding="utf-8")
    config = tmp_path / "synthetic.properties"
    config.write_text("[ai]\ndefault_provider = ollama\ndefault_model = synthetic\n", encoding="utf-8")
    sentinel = tmp_path / "caller-database-do-not-open.sqlite3"
    sentinel.write_bytes(b"Synthetic caller-owned sentinel; not a database")
    environment = {
        **os.environ, "PYTHONPATH": str(ROOT), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "SLM_OFFLINE_TESTS": "1", "USE_REAL_AI": "0", "SLM_CONFIG_FILE": str(config),
    }
    if collect_only:
        environment["SLM_DB_PATH"] = str(sentinel)
        environment["SLM_LOG_DIR"] = str(tmp_path / "caller-logs")
    else:
        environment.pop("SLM_DB_PATH", None)
        environment.pop("SLM_LOG_DIR", None)
    runner = textwrap.dedent("""
        import os
        from pathlib import Path
        import sys
        import pytest
        from tests import conftest as fixture_plugin

        work = Path(sys.argv[1])
        collect_only = sys.argv[2] == '1'
        before = {key: os.environ.get(key) for key in ('SLM_DB_PATH', 'SLM_LOG_DIR')}

        class Observer:
            module = None
            after_tests = []

            def pytest_collection_modifyitems(self, items):
                self.module = items[0].module

            @pytest.hookimpl(hookwrapper=True, tryfirst=True)
            def pytest_runtest_teardown(self):
                yield
                self.after_tests.append(Path(os.environ['SLM_DB_PATH']))

        observer = Observer()
        args = ['-q', '-p', 'no:cacheprovider', '--confcutdir', str(work),
                '--basetemp', str(work / 'basetemp'), str(work / 'test_isolated_probe.py')]
        if collect_only:
            args.append('--collect-only')
        result = pytest.main(args, plugins=[fixture_plugin, observer])
        assert result == 0, result
        assert {key: os.environ.get(key) for key in before} == before
        assert observer.module is not None
        collection = observer.module.collection_path
        assert not collection.parent.exists()
        assert not (work / 'slm_educator.db').exists()
        assert (work / 'caller-database-do-not-open.sqlite3').read_bytes() == b'Synthetic caller-owned sentinel; not a database'
        if not collect_only:
            assert len(observer.module.test_paths) == 2
            assert observer.after_tests == [collection, collection]
        print('COLLECTION_ISOLATION_VERIFIED')
    """)
    result = subprocess.run(
        [sys.executable, "-c", runner, str(tmp_path), "1" if collect_only else "0"],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "COLLECTION_ISOLATION_VERIFIED" in result.stdout
