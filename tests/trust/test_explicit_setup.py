"""Source installation policy, separate from native Windows execution evidence."""
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_start_never_installs_or_upgrades_dependencies():
    start = (ROOT / 'start.bat').read_text().lower()
    assert 'call install_dependencies.bat' not in start
    assert 'pip install' not in start
    assert '--reload' not in start
    assert 'python scripts\\seed_admin.py' in start
    assert '--host 127.0.0.1' in start


def test_runtime_and_dev_dependencies_are_separate():
    runtime = (ROOT / 'requirements.txt').read_text()
    dev = (ROOT / 'requirements-dev.txt').read_text()
    assert 'pytest' not in runtime and 'mypy' not in runtime and 'black' not in runtime
    assert '-r requirements.txt' in dev and 'pytest==' in dev
    assert '--upgrade pip' not in (ROOT / 'install_dependencies.bat').read_text()
