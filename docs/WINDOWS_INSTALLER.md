# Windows installer recipe (Inno Setup)

Updated 2026-10-06. This is the minimal maintained recipe that wraps a freshly
built PyInstaller `onedir` payload in a real Windows installer. It reuses the
existing production builder and the create-only seeder; it does not introduce a
second packaging path, a migration framework or a shared bootstrap password.

## Requirements

- Windows 10/11 (the installer must be compiled on Windows).
- Python 3.13 with `requirements.txt`, `requirements-dev.txt` and
  `pyinstaller==6.16.0` installed in the same environment (the verified
  combination). The builder refuses a Python whose Tcl/Tk uses the `zipfs`
  layout, observed with Python 3.14.
- Inno Setup 6 (`ISCC.exe`). `scripts/build_installer.py` looks in
  `%ProgramFiles(x86)%\Inno Setup 6`, `%ProgramFiles%\Inno Setup 6` and
  `%LOCALAPPDATA%\Programs\Inno Setup 6`; use `--iscc` to point elsewhere.
  Do not bypass operating-system permissions or security prompts to install it.

## Invocation

```powershell
.\build_installer.bat --payload-dir "C:\builds\SLMEducator payload 20261006" --output-dir "C:\builds\SLMEducator setup 20261006" --version 2.0.0
```

`--payload-dir` and `--output-dir` must be **new absolute** directories; existing
paths are refused so an installed copy is never reused as a build source. The
build id defaults to the current short source commit (`--build-id` overrides it).
The output file is
`SLMEducator-Setup-<version>-<build-id>.exe`.

The initial administrator password is not printed by this script. Set
`SLM_INITIAL_ADMIN_PASSWORD` to a unique password of at least 12 characters in
the build process environment, or keep the one-time generated value printed by
the seeder, and store it privately. Build the installer separately for each
installation; a seeded package and its password hash must not be shared.

## What the recipe does

- Runs `scripts/build_package.py --prod --output-dir <payload-dir>`, so the
  payload is built from a new database and the existing create-only seeder.
  Working databases, local configuration and existing installations are not
  read or changed.
- Compiles `installer/SLMEducator.iss` with the payload path, version, build id
  and output directory supplied as compiler defines.
- Installs per user under `%LOCALAPPDATA%\Programs\SLMEducator` with
  `PrivilegesRequired=lowest`: no administrator elevation and no service.
- Installs the complete `onedir` payload, never the executable alone.
- Treats `slm_educator.db` and `env.properties` as user data: they are installed
  only when absent (`onlyifdoesntexist`) and are never removed by the
  uninstaller (`uninsneveruninstall`). There is no wildcard `[UninstallDelete]`.
- Refuses to update an existing per-user installation in place and stops with a
  clear message instead of improvising a migration. Uninstall first (data and
  configuration are preserved) or use a new destination.
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

It silently installs into a disposable pytest temporary directory, checks the
program files, shortcuts and per-user uninstall entry, confirms that an in-place
reinstall is refused without touching data, uninstalls, and reinstalls over the
preserved data. It skips when another SLMEducator installation is registered for
the current user, so it never touches an installation it does not own.

## Limits

- The setup executable is not code-signed. Windows SmartScreen may warn; this
  recipe does not instruct users to bypass security controls.
- This is an installer for a local single-process evaluation. It does not
  certify production readiness, educational efficacy, multi-user hosting or
  upgrade compatibility. An in-place upgrade path is explicitly not offered.
- A native build, an install/login/restart smoke test and a human X-button check
  remain separate evidence; mocked freezing on Linux cannot replace them.
