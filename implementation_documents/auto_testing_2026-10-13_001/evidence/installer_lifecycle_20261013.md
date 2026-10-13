# Installer lifecycle exercise (authorized)

- Date: 2026-10-13. Windows 11 (build 26200), PowerShell 5.1, Python 3.14.7 venv.
- Authorization: the owner authorized repeated install/uninstall testing of
  this specific app with user-data preservation. Every step below was scoped
  to that authorization.

## Pre-state snapshot (owner's per-user install)

- Install location: `%LOCALAPPDATA%\Programs\SLMEducator\` (per-user).
- Registration: `HKCU\...\Uninstall\{40301115-8D29-4D37-A067-F025278BCDC0}_is1`
  in both registry views; `InstallLocation` matched the directory above and
  `UninstallString` matched the owned `unins000.exe` (same ownership guard as
  `tests/windows/test_installer_lifecycle.py`).
- Shortcuts present: Start Menu `Programs\SLMEducator\SLMEducator.lnk` and
  Desktop `SLMEducator.lnk`. No `SLMEducator` process was running.
- Installed build: `cc0c41db8193`; `SLMEducator.exe` SHA-256
  `3698A0E0BDB91142658AF72261BBFC9D5853243405CD755F9FDC4745A6FA9251`.
- User-data SHA-256 before any operation:
  - `slm_educator.db` `200031E540566D49C209232451DA45F0435D2180EAEEB02FB3F55A0300217B88`
  - `slm_educator.db-shm` `58CA5E47FAE547CEE78DBC88ACB3A1D7119933F87D5317321582DAFBF704B87D`
  - `slm_educator.db-wal` `C053FD6F47462C6CDDB2BFAC67ACCABD3D8E253A7649743950F0FE487CD6F4DA`
  - `env.properties` `C17516564BE99482DDAF07272927BDCCD4F064CA8651FAE2F43D00825F36194F`
- Full-directory backup (2,449 files, 83,626,904 bytes):
  `%LOCALAPPDATA%\SLMEducator-campaign-backup-20261013\`.

## Step 1 - owner install uninstalled with its owned uninstaller

- Ownership guard verified before execution; uninstaller run silently
  (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`), waited on the process tree;
  exit code 0.
- Verified afterwards: registration keys removed (both views), both shortcuts
  removed, `SLMEducator.exe`, `_internal\`, and `unins*.*` removed.
- All four user-data files retained with byte-identical SHA-256 hashes.

## Step 2 - real lifecycle test executed

- Command: `SLM_INSTALLER_SETUP=C:\builds\slm-setup-29df5ed\SLMEducator-Setup-2.0.0-29df5ed.exe`
  `python -m pytest tests\windows\test_installer_lifecycle.py -v`.
- Result: **1 passed in 37.86s** (`evidence\pytest_installer_lifecycle_gemma4_run.log`).
- The test exercised, against a real Inno Setup package and the current
  Windows profile: silent install into a fresh temporary target; presence of
  program files, `_internal\`, user data, owned uninstaller registration, and
  both shortcuts; writing distinct user data and hashing it; refusal of an
  in-place reinstall with data unchanged; uninstall preserving user data;
  reinstall-after-uninstall succeeding with data preserved; and verified
  cleanup of its own target.

## Step 3 - owner install restored

- Reinstalled silently to the original `%DIR%` with the same Setup artifact;
  exit code 0.
- Verified: `SLMEducator.exe`, `_internal\`, `unins000.exe` present;
  registration re-created; both shortcuts restored; registry display name
  `SLMEducator 2.0.0 (build 29df5ed)`.
- All four user-data files byte-identical to the pre-step snapshot (hashes
  above). The app was not launched afterwards; first launch is left to the
  owner.

## Honest deltas and limits

- **Build delta:** the original installed build `cc0c41db8193` Setup is no
  longer on disk (`C:\builds` holds only `19909e6` and `29df5ed` trees). The
  restore used the newest available artifact, so the installed build changed
  from `cc0c41db8193` to `29df5ed`. User data was preserved byte-identically
  through the whole sequence.
- The full-restore backup remains at
  `%LOCALAPPDATA%\SLMEducator-campaign-backup-20261013\` until the owner
  confirms the restored install.
- This exercise validates installer lifecycle behavior and user-data
  preservation. It does not validate the `cc0c41db8193` package manifest, the
  Setup-to-payload chain for that historical build, or native GUI acceptance.
