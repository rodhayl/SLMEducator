# Windows installer recipe (Inno Setup)

Updated 2026-10-07. This is the minimal maintained recipe that wraps a freshly
built PyInstaller `onedir` payload in a real Windows installer. It reuses the
existing production builder and local first-run setup; it does not introduce a
second packaging path, a migration framework or a shared bootstrap password.

## Requirements

- Windows 10/11 (the installer must be compiled on Windows).
- Node 22.22+ and the explicitly prepared React frontend build described below.
  Node is a build tool; it is not required on the installed application's host.
- Python 3.13 with `requirements.txt`, `requirements-dev.txt` and
  `pyinstaller==6.16.0` installed in the same environment (the verified
  combination). The builder refuses a Python whose Tcl/Tk uses the `zipfs`
  layout, observed with Python 3.14.
- Inno Setup 6 (`ISCC.exe`). `scripts/build_installer.py` looks in
  `%ProgramFiles(x86)%\Inno Setup 6`, `%ProgramFiles%\Inno Setup 6` and
  `%LOCALAPPDATA%\Programs\Inno Setup 6`; use `--iscc` to point elsewhere.
  Do not bypass operating-system permissions or security prompts to install it.

## Invocation

From the repository root, prepare and verify the frontend before packaging:

```powershell
cd src/frontend
npm ci --ignore-scripts
npm run check
cd ../..
```

`npm run check` includes TypeScript, lint, synthetic frontend tests and the
production build. To rebuild already-checked sources, explicitly run
`npm run build` from `src/frontend`. The package builder requires
the verified, source-matching `src/frontend/dist` output; it never installs
frontend dependencies or builds missing/stale assets automatically. See the
[React frontend build requirements](../README.md#react-frontend-build).

Then invoke the installer builder:

```powershell
.\build_installer.bat --payload-dir "C:\builds\SLMEducator payload 20261006" --output-dir "C:\builds\SLMEducator setup 20261006" --version 2.0.0
```

Use **new absolute** directories for `--payload-dir` and `--output-dir`; relative
arguments are normalized to absolute paths, and existing paths are refused so an installed copy is never reused as a build source. The
build id defaults to the current short source commit (`--build-id` overrides it).
The output file is
`SLMEducator-Setup-<version>-<build-id>.exe`.

Production payloads contain no account or password. The local installation owner
chooses the first administrator credentials in the native launcher before the
server opens. Build-time bootstrap password/email variables are ignored. After
first setup, never redistribute that installation database or its credentials.

## What the recipe does

- Runs `scripts/build_package.py --prod --output-dir <payload-dir>`, so the
  payload contains an account-free database eligible for local first-run setup.
  Working databases, local configuration and existing installations are not
  read or changed.
- Compiles `installer/SLMEducator.iss` with the payload path, version, build id
  and output directory supplied as compiler defines.
- Installs per user under `%LOCALAPPDATA%\Programs\SLMEducator` with
  `PrivilegesRequired=lowest`: no elevation request and no service. Launch
  non-elevated; this setting does not remove an already-elevated caller token.
- Installs the complete `onedir` payload, never the executable alone.
- Treats `slm_educator.db` and `env.properties` as user data: they are installed
  only when absent (`onlyifdoesntexist`) and are never removed by the
  uninstaller (`uninsneveruninstall`). There is no wildcard `[UninstallDelete]`.
- Refuses to update an existing per-user installation in place and stops with a
  clear message instead of improvising a migration. A different destination does
  not bypass the per-user registration guard. Uninstall first (data and
  configuration are preserved). An unregistered portable directory is not
  protected by that guard: select a genuinely fresh destination, never an
  existing portable payload or its program files.
- Asks the user to close locked applications (`CloseApplications=yes`) without
  restarting them automatically (`RestartApplications=no`) and without any
  generic process kill.
- Performs no dependency/model download and no external call during
  installation. The only post-install action is the optional, user-visible
  launcher entry point, skipped in silent installs.

## Verifying a built installer

The lifecycle of a freshly built Setup can be checked with the opt-in test:

```powershell
$env:SLM_INSTALLER_SETUP = "C:\builds\SLMEducator setup\SLMEducator-Setup-2.0.0-<build>.exe"
$env:SLM_INSTALLER_PAYLOAD_SHA256 = "<sha256 of the pristine payload SLMEducator.exe>"  # optional
python -m pytest tests/windows/test_installer_lifecycle.py -q
```

Run non-elevated in a disposable Windows account, with no concurrent installer
or uninstaller. The payload goes into a fresh pytest temporary directory, but
Start Menu/Desktop shortcuts and HKCU registration use the real current profile.
The test resolves both actual shell folders (including redirection) and skips on
an existing target shortcut or exact current/legacy application registration.

It checks the program files and owned registration, writes distinct valid
synthetic SQLite/configuration content, then verifies preservation through a
refused in-place install, uninstall and reinstall. A same-seed overwrite now
fails. PowerShell `Start-Process -Wait` plus a fresh completion marker establishes
tree completion before cleanup. An ordinary failed partial install is rolled
back only through its owned uninstaller; the test never deletes registry keys.

On timeout, missing completion marker, foreign state or cleanup failure, it
fails closed and retains the target/uninstaller and logs. Descendants may still
be running. Inspect only this invocation's processes and finish owned cleanup
before deleting anything or rerunning; do not use a global process kill. Pytest
temporary files are not permanent evidence, so preserve needed logs privately.
The synthetic contracts can run separately with
`python -m pytest tests/test_build_installer.py tests/test_installer_lifecycle_contract.py -q`.
A Linux pass or opt-in skip is not native Windows validation.

## Limits

- The setup executable is not code-signed. Windows SmartScreen may warn; this
  recipe does not instruct users to bypass security controls.
- This is an installer for a local single-process evaluation. It does not
  certify production readiness, educational efficacy, multi-user hosting or
  upgrade compatibility. An in-place upgrade path is explicitly not offered.
- A native build, an install/login/restart smoke test and a human X-button check
  remain separate evidence; mocked freezing on Linux cannot replace them.


## First administrator (current source)

New production payloads contain an account-free database. The native launcher
asks the local installation owner to choose and confirm the first administrator
password before opening the HTTP server. No build-time credential is shipped.
Canceling setup stops startup; configured installations retain their accounts.
An existing or previously configured empty database does not reopen setup and
requires authorized recovery. These paths have synthetic SQLite/launcher tests;
a new native Windows build, install and first-start acceptance remain required.
