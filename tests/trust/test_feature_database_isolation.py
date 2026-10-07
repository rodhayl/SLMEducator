"""Standalone feature runners use create-only disposable database paths."""

from pathlib import Path
import os
import subprocess
import sys

import pytest

from tests.features.test_comprehensive import ComprehensiveTestSuite
from tests.features.test_workflows import WorkflowTester
from tests.features.test_phases_1_2 import Phase1And2Tester
from tests.features.test_phase3_4 import Phase3And4Tester
from tests.fixtures.synthetic_database import new_synthetic_database


RUNNERS = [ComprehensiveTestSuite, WorkflowTester, Phase1And2Tester, Phase3And4Tester]
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("runner_class", RUNNERS)
def test_feature_runner_uses_supplied_disposable_database(tmp_path, runner_class):
    """Run existing behavioral assertions without a root-relative database."""
    destination = tmp_path / "synthetic.sqlite3"
    runner = runner_class(destination)
    assert runner.db.db_path == destination
    try:
        if isinstance(runner, WorkflowTester):
            teacher, plan, contents = runner.test_teacher_workflow()
            student, assignment = runner.test_student_workflow(teacher, plan, contents)
            assert student.id != teacher.id
            assert assignment.study_plan_id == plan.id
        else:
            assert runner.run_all_tests() is True
    finally:
        runner.cleanup()
    assert destination.is_file(), "The fixture owns cleanup; the runner must not delete its path"


@pytest.mark.parametrize("runner_class", RUNNERS)
@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_feature_runner_refuses_existing_database_or_sidecar(tmp_path, runner_class, suffix):
    """A synthetic preexisting sentinel is never opened, reset or removed."""
    destination = tmp_path / "existing.sqlite3"
    sentinel = destination.with_name(destination.name + suffix)
    sentinel.write_bytes(b"Synthetic existing file; preserve unchanged")
    with pytest.raises(FileExistsError, match="destination must be new"):
        runner_class(destination)
    assert sentinel.read_bytes() == b"Synthetic existing file; preserve unchanged"
    if suffix:
        assert not destination.exists()


def test_synthetic_database_rejects_implicit_working_directory():
    with pytest.raises(ValueError, match="must be absolute"):
        new_synthetic_database(Path("synthetic.sqlite3"))


@pytest.mark.parametrize("script", [
    "core/test_content_ordering.py", "features/test_comprehensive.py",
    "features/test_workflows.py", "features/test_phases_1_2.py", "features/test_phase3_4.py",
])
def test_standalone_entrypoint_preserves_existing_filenames(tmp_path, script):
    """Direct runners clean only their temporary directories and fail honestly."""
    names = ["test_ordering.db", "test_comprehensive.db", "test_workflow.db",
             "test_phases_1_2.db", "test_phase3_4.db", "slm_educator.db"]
    for name in names:
        (tmp_path / name).write_bytes(b"Synthetic caller-owned sentinel")
    config = tmp_path / "synthetic.properties"
    config.write_text("[ai]\ndefault_provider = ollama\ndefault_model = synthetic\n", encoding="utf-8")
    environment = {
        **os.environ, "SLM_TEST_MODE": "1", "SLM_CONFIG_FILE": str(config),
        "SLM_OFFLINE_TESTS": "1", "USE_REAL_AI": "0", "PYTHONIOENCODING": "utf-8",
        "TMPDIR": str(tmp_path), "TMP": str(tmp_path), "TEMP": str(tmp_path),
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / script)], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in names:
        assert (tmp_path / name).read_bytes() == b"Synthetic caller-owned sentinel"
    assert not list(tmp_path.glob("slm-*")), "The owned temporary directory must be cleaned"
