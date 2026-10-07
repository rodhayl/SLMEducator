"""Host-independent failure controls for the opt-in Windows installer smoke.

No Windows executable, real registry or real user profile is accessed here.
"""

import base64
import configparser
from contextlib import closing
import importlib.util
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def smoke():  # type: ignore[no-untyped-def]
    path = Path(__file__).parent / "windows" / "test_installer_lifecycle.py"
    spec = importlib.util.spec_from_file_location("installer_smoke_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, smoke):  # type: ignore[no-untyped-def]
    setup = tmp_path / "setup.exe"
    setup.write_bytes(b"synthetic, never executable")
    root = tmp_path / "test-run"
    root.mkdir()
    target = root / "SLMEducator"
    shortcuts = (tmp_path / "redirected-menu.lnk", tmp_path / "redirected-desktop.lnk")
    seed = tmp_path / "seed.db"
    with closing(sqlite3.connect(seed)) as connection:
        with connection:
            connection.execute("CREATE TABLE example_user_data (note TEXT)")
            connection.execute("INSERT INTO example_user_data VALUES ('seed')")
    state = SimpleNamespace(
        setup_calls=0,
        uninstall_calls=0,
        entries=[],
        failure_at=None,
        failure=None,
        reseed_at=None,
        uninstall_failure=False,
        target=target,
        root=root,
        shortcuts=shortcuts,
    )

    def run_owned(command: list[str]) -> subprocess.CompletedProcess[str]:
        if Path(command[0]) != setup:
            assert Path(command[0]) == target / "unins000.exe"
            state.uninstall_calls += 1
            if state.uninstall_failure:
                return subprocess.CompletedProcess(command, 1, "", "")
            for name in ("SLMEducator.exe", "unins000.exe", "unins000.dat"):
                (target / name).unlink(missing_ok=True)
            shutil.rmtree(target / "_internal")
            for shortcut in shortcuts:
                shortcut.unlink(missing_ok=True)
            state.entries.clear()
            return subprocess.CompletedProcess(command, 0, "", "")
        state.setup_calls += 1
        registered = bool(state.entries)
        target.mkdir(exist_ok=True)
        for name in ("SLMEducator.exe", "unins000.exe", "unins000.dat"):
            (target / name).write_bytes(b"synthetic program")
        (target / "_internal").mkdir(exist_ok=True)
        for name, data in (
            ("slm_educator.db", seed.read_bytes()),
            ("env.properties", b"[ui]\nlanguage = en\n"),
        ):
            if not (target / name).exists() or state.reseed_at == state.setup_calls:
                (target / name).write_bytes(data)
        for shortcut in shortcuts:
            shortcut.write_bytes(b"owned synthetic shortcut")
        state.entries[:] = [
            {
                "key": smoke.APP_ID + "_is1",
                "InstallLocation": str(target),
                "UninstallString": f'"{target / "unins000.exe"}"',
            }
        ]
        if state.failure_at == state.setup_calls:
            if state.failure == "timeout":
                raise smoke.UnsafeCleanup("Synthetic unverified process-tree timeout")
            return subprocess.CompletedProcess(command, 1, "", "synthetic error")
        return subprocess.CompletedProcess(command, 1 if registered else 0, "", "")

    monkeypatch.setenv("SLM_INSTALLER_SETUP", str(setup))
    monkeypatch.delenv("SLM_INSTALLER_PAYLOAD_SHA256", raising=False)
    monkeypatch.setattr(smoke, "_registrations", lambda: state.entries)
    monkeypatch.setattr(smoke, "_shortcut_paths", lambda: shortcuts)
    monkeypatch.setattr(smoke, "_run_owned", run_owned)
    return state


@pytest.mark.parametrize("index", [0, 1])
def test_preexisting_actual_shortcut_is_untouched(smoke, installation, index):  # type: ignore[no-untyped-def]
    shortcut = installation.shortcuts[index]
    shortcut.write_bytes(b"preexisting personal shortcut")
    with pytest.raises(pytest.skip.Exception, match="existing shortcut"):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert shortcut.read_bytes() == b"preexisting personal shortcut"
    assert installation.setup_calls == installation.uninstall_calls == 0
    assert not installation.target.exists()


def test_preexisting_exact_app_registration_skips(smoke, installation):  # type: ignore[no-untyped-def]
    installation.entries.append({"key": smoke.APP_ID})
    with pytest.raises(pytest.skip.Exception, match="existing SLMEducator"):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.setup_calls == installation.uninstall_calls == 0


@pytest.mark.parametrize("stage", [1, 3])
def test_failed_partial_install_is_rolled_back_after_verified_wait(
    smoke, installation, stage
):  # type: ignore[no-untyped-def]
    installation.failure_at = stage
    installation.failure = "nonzero"
    with pytest.raises(AssertionError, match="failed"):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.uninstall_calls == (1 if stage == 1 else 2)
    assert not installation.entries
    assert not any(path.exists() for path in installation.shortcuts)
    assert not installation.target.exists()


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_unverified_timeout_preserves_everything_for_manual_cleanup(
    smoke, installation, stage
):  # type: ignore[no-untyped-def]
    installation.failure_at = stage
    installation.failure = "timeout"
    with pytest.raises(smoke.UnsafeCleanup, match="unverified"):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.uninstall_calls == (1 if stage == 3 else 0)
    assert (installation.target / "unins000.exe").is_file()
    assert installation.entries
    assert all(path.is_file() for path in installation.shortcuts)


def test_distinct_valid_user_content_and_normal_lifecycle(smoke, installation):  # type: ignore[no-untyped-def]
    smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.setup_calls == 3
    assert installation.uninstall_calls == 2
    assert not installation.target.exists()


@pytest.mark.parametrize("stage", [2, 3])
def test_defective_same_seed_overwrite_is_detected(smoke, installation, stage):  # type: ignore[no-untyped-def]
    installation.reseed_at = stage
    with pytest.raises(AssertionError):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.setup_calls == stage
    assert not installation.target.exists()


def test_failed_uninstall_is_not_retried_or_deleted(smoke, installation):  # type: ignore[no-untyped-def]
    installation.uninstall_failure = True
    with pytest.raises(smoke.UnsafeCleanup, match="uninstall failed"):
        smoke.test_installer_lifecycle_preserves_user_data(installation.root)
    assert installation.uninstall_calls == 1
    assert (installation.target / "unins000.exe").is_file()
    assert installation.entries


def test_foreign_registration_blocks_cleanup(smoke, installation):  # type: ignore[no-untyped-def]
    installation.target.mkdir()
    (installation.target / "unins000.exe").write_bytes(b"owned")
    installation.entries.append(
        {
            "InstallLocation": str(installation.root / "foreign"),
            "UninstallString": '"foreign/unins000.exe"',
        }
    )
    with pytest.raises(smoke.UnsafeCleanup, match="not owned"):
        smoke._cleanup(installation.target)
    assert installation.uninstall_calls == 0
    assert (installation.target / "unins000.exe").is_file()


def test_partial_state_without_uninstaller_is_retained(smoke, installation):  # type: ignore[no-untyped-def]
    installation.target.mkdir()
    (installation.target / "SLMEducator.exe").write_bytes(b"partial")
    installation.shortcuts[0].write_bytes(b"partial")
    with pytest.raises(smoke.UnsafeCleanup, match="state remains"):
        smoke._cleanup(installation.target)
    assert (installation.target / "SLMEducator.exe").is_file()
    assert installation.shortcuts[0].is_file()


def test_mutated_database_and_config_are_valid(smoke, installation):  # type: ignore[no-untyped-def]
    smoke._run_setup(
        Path(os.environ["SLM_INSTALLER_SETUP"]),
        installation.target,
        installation.root / "install.log",
    )
    hashes = smoke._write_distinct_user_data(installation.target)
    # sqlite3's context manager commits but never closes; on Windows an open
    # connection blocks the disposable cleanup rmtree below (WinError 32).
    with closing(sqlite3.connect(installation.target / "slm_educator.db")) as connection:
        with connection:
            assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
            assert connection.execute(
                "SELECT note FROM installer_smoke_note"
            ).fetchone()[0]
            assert connection.execute(
                "SELECT note FROM example_user_data"
            ).fetchone() == (
                "seed",
            )
    config = configparser.ConfigParser()
    config.read(installation.target / "env.properties")
    assert config["ui"]["language"] == "es"
    assert len(hashes) == 2
    smoke._cleanup(installation.target)


@pytest.mark.parametrize(
    "output,code",
    [
        ("", 0),
        ("SLM_TREE_DONE_stale:0", 0),
        ("shell failed", 1),
        ("SLM_TREE_DONE_fresh:0", 1),
    ],
)
def test_missing_stale_or_mismatched_marker_fails_closed(
    smoke, monkeypatch, output, code
):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SystemRoot", "C:/Windows")
    monkeypatch.setattr(smoke.uuid, "uuid4", lambda: SimpleNamespace(hex="fresh"))
    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], code, output, ""),
    )
    with pytest.raises(smoke.UnsafeCleanup, match="completion marker"):
        smoke._run_owned(["setup.exe", "/VERYSILENT"])


@pytest.mark.parametrize(
    "error", [subprocess.TimeoutExpired("powershell", 300), KeyboardInterrupt()]
)
def test_shell_timeout_cannot_authorize_cleanup(smoke, monkeypatch, error):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SystemRoot", "C:/Windows")
    run = Mock(side_effect=error)
    monkeypatch.setattr(smoke.subprocess, "run", run)
    with pytest.raises(smoke.UnsafeCleanup, match="completion is unverified"):
        smoke._run_owned(["setup.exe", "/VERYSILENT"])
    assert run.call_count == 1


@pytest.mark.parametrize("code", [0, 1])
def test_verified_tree_marker_keeps_exit_status_and_literal_arguments(
    smoke, monkeypatch, code
):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SystemRoot", "C:/Windows")
    monkeypatch.setattr(smoke.uuid, "uuid4", lambda: SimpleNamespace(hex="fresh"))
    run = Mock(
        return_value=subprocess.CompletedProcess(
            [], code, f"SLM_TREE_DONE_fresh:{code}\n", ""
        )
    )
    monkeypatch.setattr(smoke.subprocess, "run", run)
    command = [
        "C:/build dir/O'Brien;$x/Setup.exe",
        "/DIR=C:/test dir/target",
        "/LOG=C:/test dir/log",
    ]
    result = smoke._run_owned(command)
    assert result.returncode == code
    script = base64.b64decode(run.call_args.args[0][-1]).decode("utf-16-le")
    assert "-Wait -PassThru" in script
    assert "-FilePath 'C:/build dir/O''Brien;$x/Setup.exe'" in script
    assert (
        '-ArgumentList \'"/DIR=C:/test dir/target" "/LOG=C:/test dir/log"\'' in script
    )
    assert run.call_args.kwargs["timeout"] == smoke.INSTALL_TIMEOUT
    assert "-NoProfile" in run.call_args.args[0]
