"""Opt-in installer lifecycle contract for a real, newly built Windows Setup.

Requires ``SLM_INSTALLER_SETUP`` to point at the maintained Inno Setup
executable built by ``build_installer.bat``. The test:

1. installs it silently into a disposable pytest temporary directory;
2. checks the expected program files, shortcuts and the per-user uninstall
   entry;
3. confirms that an in-place reinstall is refused without touching user data;
4. uninstalls and confirms that the database and configuration survive;
5. reinstalls over the preserved data and confirms it is still untouched.

Everything happens under pytest's temporary directory. If another SLMEducator
installation already exists for this user, the test skips instead of interfering
with it, because the installer refuses in-place updates by design. Optionally set
``SLM_INSTALLER_PAYLOAD_SHA256`` to also pin the installed executable against the
pristine payload hash.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.name != "nt" or not os.environ.get("SLM_INSTALLER_SETUP"),
    reason="Requires SLM_INSTALLER_SETUP pointing at a newly built Windows installer",
)

SILENT_SWITCHES = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LANG=english")
PROGRAM_FILES = ("SLMEducator.exe",)
USER_DATA = ("slm_educator.db", "env.properties")
INSTALL_TIMEOUT = 300


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slmeducator_uninstall_entry() -> str | None:
    """Return the HKCU uninstall subkey for an existing SLMEducator install."""
    import winreg

    try:
        parent = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        )
    except OSError:
        return None
    with parent:
        index = 0
        while True:
            try:
                name = winreg.EnumKey(parent, index)
            except OSError:
                return None
            index += 1
            try:
                with winreg.OpenKey(parent, name) as entry:
                    display, _ = winreg.QueryValueEx(entry, "DisplayName")
            except OSError:
                continue
            if str(display).startswith("SLMEducator"):
                return name
    return None


def _shortcut_paths() -> tuple[Path, Path]:
    start_menu = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "SLMEducator"
        / "SLMEducator.lnk"
    )
    desktop = _desktop_directory() / "SLMEducator.lnk"
    return start_menu, desktop


def _desktop_directory() -> Path:
    """Resolve the redirection-aware desktop folder, falling back to the profile."""
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(str(value)))
    except OSError:
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def _run_setup(setup: Path, target: Path, log: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(setup), *SILENT_SWITCHES, f"/DIR={target}", f"/LOG={log}", "/MERGETASKS=desktopicon"],
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT,
    )


def _uninstaller(target: Path) -> Path | None:
    """Return the uninstaller Inno actually created (unins000, unins001, ...)."""
    candidates = sorted(target.glob("unins*.exe"))
    return candidates[0] if candidates else None


def _uninstall(target: Path) -> None:
    uninstaller = _uninstaller(target)
    assert uninstaller is not None, "The installed uninstaller is missing"
    completed = subprocess.run(
        [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    # Inno's uninstaller copies itself to %TEMP% and removes its own
    # unins*.exe/.dat last, so waiting for the executable or the registry key
    # alone is not enough: a fast reinstall could otherwise create unins001.exe
    # while the previous uninstaller is still finishing.
    start_menu, desktop = _shortcut_paths()
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if (
            _uninstaller(target) is None
            and not (target / "SLMEducator.exe").exists()
            and _slmeducator_uninstall_entry() is None
            and not start_menu.exists()
            and not desktop.exists()
        ):
            return
        time.sleep(0.25)
    pytest.fail("The uninstaller did not finish removing its program state")


def test_installer_lifecycle_preserves_user_data(tmp_path: Path) -> None:
    setup = Path(os.environ["SLM_INSTALLER_SETUP"])
    if not setup.is_file():
        pytest.fail(f"SLM_INSTALLER_SETUP does not name an existing installer: {setup}")
    existing = _slmeducator_uninstall_entry()
    if existing is not None:
        pytest.skip(
            "An existing SLMEducator installation is registered for this user "
            f"({existing}); this test refuses to touch it"
        )

    target = tmp_path / "SLMEducator"
    installed = False
    try:
        # 1. Fresh per-user installation without elevation.
        result = _run_setup(setup, target, tmp_path / "install.log")
        assert result.returncode == 0, (
            f"Silent install failed with {result.returncode}\n{result.stdout}{result.stderr}"
        )
        installed = True
        for name in (*PROGRAM_FILES, *USER_DATA):
            assert (target / name).is_file(), name
        assert (target / "_internal").is_dir()
        assert _uninstaller(target) is not None
        assert _slmeducator_uninstall_entry() is not None
        start_menu, desktop = _shortcut_paths()
        assert start_menu.is_file(), start_menu
        assert desktop.is_file(), desktop

        pinned = os.environ.get("SLM_INSTALLER_PAYLOAD_SHA256")
        if pinned:
            assert _sha256(target / "SLMEducator.exe") == pinned

        # 2. An in-place reinstall is refused and changes nothing.
        before = {name: _sha256(target / name) for name in USER_DATA}
        refused = _run_setup(setup, target, tmp_path / "reinstall.log")
        assert refused.returncode != 0, "An in-place reinstall must be refused"
        assert (target / "SLMEducator.exe").is_file()
        assert {name: _sha256(target / name) for name in USER_DATA} == before

        # 3. Uninstall removes program files and shortcuts, not user data.
        _uninstall(target)
        installed = False
        assert not (target / "SLMEducator.exe").exists()
        assert not (target / "_internal").exists()
        assert not start_menu.is_file()
        assert not desktop.is_file()
        for name in USER_DATA:
            assert (target / name).is_file(), name
        assert {name: _sha256(target / name) for name in USER_DATA} == before

        # 4. Reinstalling over the preserved data keeps it untouched.
        result = _run_setup(setup, target, tmp_path / "reinstall-after-uninstall.log")
        assert result.returncode == 0, (
            f"Reinstall failed with {result.returncode}\n{result.stdout}{result.stderr}"
        )
        installed = True
        assert (target / "SLMEducator.exe").is_file()
        assert {name: _sha256(target / name) for name in USER_DATA} == before
    finally:
        if installed and _uninstaller(target) is not None:
            _uninstall(target)
        shutil.rmtree(target, ignore_errors=True)
