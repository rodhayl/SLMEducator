"""Opt-in lifecycle test for a real, newly built Windows Setup.

The payload uses a fresh temporary directory, but shortcuts and uninstall
registration use the current Windows profile. Existing registrations or actual
shell shortcut collisions cause a skip. Use a disposable, non-elevated account
and do not run concurrent installations. No native PASS is implied by a skip.

Set SLM_INSTALLER_SETUP to the maintained Setup executable. Optionally pin the
installed executable with SLM_INSTALLER_PAYLOAD_SHA256. An uncertain process
wait or cleanup failure retains the target and logs for manual inspection;
never delete them while an installer descendant could still be running.
"""

from __future__ import annotations

import base64
import configparser
from contextlib import closing
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.name != "nt" or not os.environ.get("SLM_INSTALLER_SETUP"),
    reason="Requires SLM_INSTALLER_SETUP pointing at a newly built Windows installer",
)

SILENT_SWITCHES = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LANG=english")
PROGRAM_FILES = ("SLMEducator.exe",)
USER_DATA = ("slm_educator.db", "env.properties")
INSTALL_TIMEOUT = 300
APP_ID = "{40301115-8D29-4D37-A067-F025278BCDC0}"


class UnsafeCleanup(RuntimeError):
    """The owned process tree or remaining installation cannot be verified."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registrations() -> list[dict[str, str]]:
    """Read exact current/legacy app keys in both registry views; never delete."""
    import winreg

    entries = []
    parent = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        for name in (APP_ID + "_is1", APP_ID):
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    parent + "\\" + name,
                    0,
                    winreg.KEY_READ | view,
                )
            except FileNotFoundError:
                continue
            with key:
                values = {"key": name}
                for field in ("InstallLocation", "UninstallString"):
                    try:
                        values[field] = str(winreg.QueryValueEx(key, field)[0])
                    except FileNotFoundError:
                        values[field] = ""
                entries.append(values)
    return entries


def _shell_directory(csidl: int) -> Path:
    """Resolve actual per-user shell folders, including redirected locations."""
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    if result != 0 or not buffer.value:
        raise UnsafeCleanup(f"Cannot resolve Windows shell folder {csidl}")
    return Path(buffer.value)


def _shortcut_paths() -> tuple[Path, Path]:
    return (
        _shell_directory(0x0002) / "SLMEducator" / "SLMEducator.lnk",
        _shell_directory(0x0010) / "SLMEducator.lnk",
    )


def _ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_owned(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Wait for this invocation and descendants using Windows PowerShell.

    Start-Process -Wait waits for the entire process tree (unlike Wait-Process).
    The fresh marker is written only after that wait. A timeout kills the shell
    via subprocess.run, but does NOT prove descendants stopped: fail closed.
    https://learn.microsoft.com/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1
    """
    marker = "SLM_TREE_DONE_" + uuid.uuid4().hex
    arguments = _ps_literal(subprocess.list2cmdline(command[1:]))
    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$p = Start-Process -FilePath {_ps_literal(command[0])} "
        f"-ArgumentList {arguments} -Wait -PassThru; "
        f"[Console]::Out.WriteLine('{marker}:' + $p.ExitCode); exit $p.ExitCode"
    )
    powershell = (
        Path(os.environ["SystemRoot"])
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        result = subprocess.run(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT,
        )
    except BaseException as error:
        raise UnsafeCleanup(
            "Installer process-tree completion is unverified; retain the target "
            "and logs. Check owned processes before any manual cleanup."
        ) from error
    expected = f"{marker}:{result.returncode}"
    if result.stdout.splitlines().count(expected) != 1:
        raise UnsafeCleanup(
            "Missing matching process-tree completion marker; retain the target "
            "and logs. PowerShell or its descendant may not have finished."
        )
    return subprocess.CompletedProcess(
        command,
        result.returncode,
        result.stdout.replace(expected, ""),
        result.stderr,
    )


def _run_setup(
    setup: Path, target: Path, log: Path
) -> subprocess.CompletedProcess[str]:
    return _run_owned(
        [
            str(setup),
            *SILENT_SWITCHES,
            f"/DIR={target}",
            f"/LOG={log}",
            "/MERGETASKS=desktopicon",
        ]
    )


def _uninstaller(target: Path) -> Path | None:
    candidates = sorted(target.glob("unins*.exe"))
    if len(candidates) > 1:
        raise UnsafeCleanup("Multiple uninstallers found; retain target for inspection")
    return candidates[0] if candidates else None


def _assert_owned_registration(target: Path) -> None:
    """Never execute an uninstall command read from the registry."""
    uninstaller = _uninstaller(target)
    for entry in _registrations():
        location = entry["InstallLocation"]
        command = entry["UninstallString"]
        if (
            not location
            or Path(location).resolve() != target.resolve()
            or uninstaller is None
            or command not in (str(uninstaller), f'"{uninstaller}"')
        ):
            raise UnsafeCleanup("Uninstall registration is not owned by this target")


def _assert_program_state_removed(target: Path) -> None:
    remaining = [
        path
        for path in (
            target / "SLMEducator.exe",
            target / "_internal",
            *_shortcut_paths(),
            *target.glob("unins*"),
        )
        if path.exists() or path.is_symlink()
    ]
    if remaining or _registrations():
        raise UnsafeCleanup("Program/profile state remains; retain target and logs")


def _uninstall(target: Path) -> None:
    _assert_owned_registration(target)
    uninstaller = _uninstaller(target)
    if uninstaller is None:
        raise UnsafeCleanup("The owned uninstaller is missing; retain target and logs")
    completed = _run_owned(
        [
            str(uninstaller),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
        ]
    )
    if completed.returncode != 0:
        raise UnsafeCleanup(f"Owned uninstall failed with {completed.returncode}")
    _assert_program_state_removed(target)


def _write_distinct_user_data(target: Path) -> dict[str, str]:
    """Write valid disposable user content so same-seed replacement is detected."""
    original = {name: _sha256(target / name) for name in USER_DATA}
    with closing(sqlite3.connect(target / USER_DATA[0])) as connection:
        with connection:
            connection.execute("CREATE TABLE installer_smoke_note (note TEXT NOT NULL)")
            connection.execute(
                "INSERT INTO installer_smoke_note VALUES (?)",
                (uuid.uuid4().hex,),
            )
        assert connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
    config = configparser.ConfigParser(interpolation=None)
    with (target / USER_DATA[1]).open(encoding="utf-8") as source:
        config.read_file(source)
    if not config.has_section("ui"):
        config.add_section("ui")
    config.set(
        "ui",
        "language",
        "es" if config.get("ui", "language", fallback="en") == "en" else "en",
    )
    with (target / USER_DATA[1]).open("w", encoding="utf-8") as output:
        config.write(output)
    changed = {name: _sha256(target / name) for name in USER_DATA}
    assert all(changed[name] != original[name] for name in USER_DATA)
    return changed


def _cleanup(target: Path) -> None:
    """Rollback partial installs only after a verified process-tree wait."""
    _assert_owned_registration(target)
    if _uninstaller(target) is not None:
        _uninstall(target)
    _assert_program_state_removed(target)
    if target.exists():
        shutil.rmtree(target)  # Never hide a cleanup failure or remove evidence first.


def test_installer_lifecycle_preserves_user_data(tmp_path: Path) -> None:
    setup = Path(os.environ["SLM_INSTALLER_SETUP"]).resolve()
    if not setup.is_file():
        pytest.fail(f"SLM_INSTALLER_SETUP does not name an existing installer: {setup}")
    if _registrations():
        pytest.skip(
            "An existing SLMEducator registration is present; refusing to touch it"
        )
    start_menu, desktop = _shortcut_paths()
    for path in (start_menu, desktop):
        if path.exists() or path.is_symlink():
            pytest.skip(f"An existing shortcut occupies {path}; refusing to touch it")

    target = tmp_path / "SLMEducator"
    assert not target.exists() and not target.is_symlink(), "A fresh target is required"
    cleanup_safe = True
    try:
        result = _run_setup(setup, target, tmp_path / "install.log")
        assert result.returncode == 0, f"Silent install failed with {result.returncode}"
        for name in (*PROGRAM_FILES, *USER_DATA):
            assert (target / name).is_file(), name
        assert (target / "_internal").is_dir()
        assert _uninstaller(target) is not None
        assert _registrations(), "The expected app registration is missing"
        _assert_owned_registration(target)
        assert start_menu.is_file(), start_menu
        assert desktop.is_file(), desktop
        pinned = os.environ.get("SLM_INSTALLER_PAYLOAD_SHA256")
        if pinned:
            assert _sha256(target / "SLMEducator.exe") == pinned

        before = _write_distinct_user_data(target)
        refused = _run_setup(setup, target, tmp_path / "reinstall.log")
        assert refused.returncode != 0, "An in-place reinstall must be refused"
        assert (target / "SLMEducator.exe").is_file()
        assert {name: _sha256(target / name) for name in USER_DATA} == before

        _uninstall(target)
        assert {name: _sha256(target / name) for name in USER_DATA} == before
        result = _run_setup(setup, target, tmp_path / "reinstall-after-uninstall.log")
        assert result.returncode == 0, f"Reinstall failed with {result.returncode}"
        assert (target / "SLMEducator.exe").is_file()
        assert {name: _sha256(target / name) for name in USER_DATA} == before
    except UnsafeCleanup:
        cleanup_safe = False
        raise
    finally:
        if cleanup_safe:
            _cleanup(target)
