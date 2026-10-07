"""Static contracts plus native cmd execution with a harmless pytest module."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_tests.bat"


def test_real_provider_gate_uses_live_choice_result_and_explicit_yes():
    text = RUNNER.read_text()
    gate = text.split("\n:run_real_ai\n", 1)[1].split("\n:finish\n", 1)[0]
    assert "%CONFIRM%" not in gate and "set /p" not in gate
    assert 'if "%ASSUME_YES%"=="1" goto :run_real_ai_confirmed' in gate
    assert "choice /C YN /N /M " in gate
    reject = gate.index("if errorlevel 2 goto :real_ai_cancelled")
    approve = gate.index("if errorlevel 1 goto :run_real_ai_confirmed")
    cancel = gate.index("\n:real_ai_cancelled\n")
    invoke = gate.index("\n:run_real_ai_confirmed\n")
    assert reject < approve < cancel < invoke
    assert "exit /b 0" in gate[cancel:invoke]
    assert "python -m pytest tests/real_ai/" in gate[invoke:]


def test_non_real_modes_reset_inherited_provider_flags():
    text = RUNNER.read_text()
    dispatch = text.index('if /i "%MODE%"=="full" goto :run_full')
    for flag in (
        'set "SLM_OFFLINE_TESTS=1"',
        'set "USE_REAL_AI=0"',
        'set "NO_MOCKS_ALLOWED="',
    ):
        assert flag in text[:dispatch]
    quick = text.split("\n:run_quick\n", 1)[1].split("\n:run_ai\n", 1)[0]
    assert quick.count("%SYNTHETIC_SCOPE%") == 2
    confirmed = text.split("\n:run_real_ai_confirmed\n", 1)[1]
    assert 'set "SLM_OFFLINE_TESTS=0"' in confirmed


def test_test_runner_installs_development_tools_explicitly():
    text = RUNNER.read_text()
    assert "call install_dependencies.bat --dev" in text
    assert "echo Run install_dependencies.bat --dev and try again." in text
    setup = text.split("\n:validate_args\n", 1)[1].split(
        "\n:activate_environment\n", 1
    )[0]
    reject = setup.index("if errorlevel 2")
    approve = setup.index("if errorlevel 1 goto :install_dependencies")
    fallback = setup.index("Dependency installation was not confirmed.")
    assert reject < approve < fallback
    assert "exit /b 1" in setup[fallback:]


def test_browser_workflow_builds_real_frontend_before_headed_journeys():
    workflow = (ROOT / ".github/workflows/browser-acceptance.yml").read_text()
    assert "cache-dependency-path: src/frontend/package-lock.json" in workflow
    install = workflow.index("npm ci --ignore-scripts --prefix src/frontend")
    build = workflow.index("npm run build --prefix src/frontend")
    run = workflow.index("xvfb-run -a python -m pytest tests/browser")
    assert install < build < run
    assert "node-version: '22'" in workflow
    assert "persist-credentials: false" in workflow


@pytest.mark.skipif(os.name != "nt", reason="Requires actual Windows cmd and CHOICE")
@pytest.mark.parametrize("inherited", [None, "YES", "NO"])
@pytest.mark.parametrize(
    "answer,explicit,allowed",
    [("Y\n", False, True), ("N\n", False, False), ("", True, True)],
)
def test_native_real_ai_confirmation_never_calls_a_provider(
    tmp_path, inherited, answer, explicit, allowed
):
    shutil.copyfile(RUNNER, tmp_path / RUNNER.name)
    scripts = tmp_path / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "activate.bat").write_text("@echo off\nexit /b 0\n")
    marker = tmp_path / "pytest-invocation.json"
    (tmp_path / "pytest.py").write_text(
        "import json,os,sys\nfrom pathlib import Path\n"
        "if __name__ == '__main__':\n"
        " Path(os.environ['SYNTHETIC_PYTEST_MARKER']).write_text(json.dumps({\n"
        "  'args': sys.argv[1:], 'offline': os.getenv('SLM_OFFLINE_TESTS'),\n"
        "  'real': os.getenv('USE_REAL_AI'), 'no_mocks': os.getenv('NO_MOCKS_ALLOWED')}))\n"
    )
    env = dict(os.environ)
    env.update(
        PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""),
        PYTHONPATH=str(tmp_path),
        SYNTHETIC_PYTEST_MARKER=str(marker),
    )
    if inherited is None:
        env.pop("CONFIRM", None)
    else:
        env["CONFIRM"] = inherited
    args = [
        os.environ.get("COMSPEC", "cmd.exe"),
        "/d",
        "/c",
        "run_tests.bat",
        "--real-ai",
    ]
    if explicit:
        args.append("--yes")
    result = subprocess.run(
        args,
        cwd=tmp_path,
        env=env,
        input=answer,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists() is allowed
    if allowed:
        invocation = json.loads(marker.read_text())
        assert "tests/real_ai/" in invocation["args"]
        assert invocation["offline"] == "0"
        assert invocation["real"] == "1"
        assert invocation["no_mocks"] == "1"


@pytest.mark.skipif(os.name != "nt", reason="Requires actual Windows cmd and CHOICE")
def test_native_accepted_setup_requests_only_development_install(tmp_path):
    shutil.copyfile(RUNNER, tmp_path / RUNNER.name)
    (tmp_path / "install_dependencies.bat").write_text(
        "@echo off\necho %* > requested-install.txt\nexit /b 1\n"
    )
    result = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "run_tests.bat", "--quick"],
        cwd=tmp_path,
        input="Y\n",
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0
    assert (tmp_path / "requested-install.txt").read_text().strip() == "--dev"


@pytest.mark.skipif(os.name != "nt", reason="Requires actual Windows cmd")
@pytest.mark.parametrize("mode", ["--full", "--quick", "--ai"])
def test_native_synthetic_modes_disable_inherited_provider_flags(tmp_path, mode):
    shutil.copyfile(RUNNER, tmp_path / RUNNER.name)
    scripts = tmp_path / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "activate.bat").write_text("@echo off\nexit /b 0\n")
    marker = tmp_path / "pytest-invocation.json"
    (tmp_path / "pytest.py").write_text(
        "import json,os,sys\nfrom pathlib import Path\n"
        "if __name__ == '__main__':\n"
        " Path(os.environ['SYNTHETIC_PYTEST_MARKER']).write_text(json.dumps({\n"
        "  'args': sys.argv[1:], 'offline': os.getenv('SLM_OFFLINE_TESTS'),\n"
        "  'real': os.getenv('USE_REAL_AI'), 'no_mocks': os.getenv('NO_MOCKS_ALLOWED')}))\n"
    )
    env = dict(os.environ)
    env.update(
        PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""),
        PYTHONPATH=str(tmp_path),
        SYNTHETIC_PYTEST_MARKER=str(marker),
        SLM_OFFLINE_TESTS="0",
        USE_REAL_AI="1",
        NO_MOCKS_ALLOWED="1",
    )
    result = subprocess.run(
        [
            os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "run_tests.bat",
            mode, "--no-coverage",
        ],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    invocation = json.loads(marker.read_text())
    assert invocation["offline"] == "1"
    assert invocation["real"] == "0"
    assert invocation["no_mocks"] is None
    if mode != "--ai":
        assert "--ignore=tests/real_ai" in invocation["args"]
        assert "not real_ai" in invocation["args"]
