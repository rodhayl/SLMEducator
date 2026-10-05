# SLMEducator: AI-Assisted Teaching and Learning

**Status:** Source-run application for local development and evaluation. The repository includes test suites and Windows packaging scripts; packaged GitHub releases are not currently provided.

SLMEducator brings teacher and student workflows into a Python/FastAPI learning application. It combines study plans, lessons, exercises, tutoring and learning-session tracking with configurable local or cloud AI providers. The project explores how AI assistance can fit into structured educational workflows while keeping roles, progress and application data in a conventional web architecture.

## What this project demonstrates

- Teacher workflows for creating and improving study plans, lessons, exercises and assessment questions.
- Student tutoring, learning-session lifecycle and progress/history handling.
- Provider integration separated from application services and persistence.
- Source setup, automated tests, browser validation scenarios and Windows packaging.

Use demonstration data for evaluation. Generated learning material needs teacher review, and provider selection determines whether inputs leave the machine. This repository does not establish improved learning outcomes, suitability for children or regulatory compliance in a particular deployment.

## Requirements

- Windows 10/11
- Python 3.10+ (64-bit)
- Git

## Quick Start (Windows)

Clone this repository and open PowerShell in its root. Before launching, review [Initial Admin Account](#initial-admin-account). For a new database, supply your own initial credential or privately save the one-time generated password printed during startup.

```powershell
.\install_dependencies.bat
.\start.bat
```

Application URL: `http://127.0.0.1:8080`

`start.bat` does the following:
- Uses the environment prepared explicitly by `install_dependencies.bat`; launch never installs or upgrades packages
- Activates `venv`
- Creates runtime folders (`logs`, `data`, `exports`, `temp`)
- Sets local runtime environment variables
- Calls create-only admin seeding on each launch; existing accounts and their security state are preserved
- Starts FastAPI with Uvicorn on port `8080`

## Manual Run (Alternative)

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
```

## Configuration

- Copy `.env.example` to `.env` for local secret/env overrides.
- Copy `env.properties.example` to `env.properties` for app runtime defaults.
- Keep local-only runtime files out of published artifacts:
  - `.env`
  - `env.properties`
  - `settings.properties`

## Initial Admin Account

`start.bat` calls [scripts/seed_admin.py](scripts/seed_admin.py) on every launch. The seeder creates an account only when the username `admin` is absent. If that username already exists, it leaves the password, email, role, active status, lockout state and authentication attempts unchanged. Bootstrap environment variables are ignored for existing accounts, even if a password value is invalid. Restarting therefore preserves a password changed in the UI.

For an explicit first-run credential, set `SLM_INITIAL_ADMIN_PASSWORD` to your own unique password of at least 12 characters in the launcher's process environment. `SLM_INITIAL_ADMIN_EMAIL` optionally sets the new account's email. These variables are for initial creation only, not password recovery. Treat the password as a secret: do not place a real value in shared commands, documentation or commits.

The launcher no longer supplies a shared default password. With no nonblank password override, the seeder generates a random password for a new administrator and prints it once, whether invoked by the launcher or directly. Keep that output private and save it before closing the terminal. A later launch will not print or recover it. Sign in and rotate the initial credential. These development provisioning paths need review before use with real student information.

Packaging uses the same create-only seeder in disposable staging. It does not delete or seed the working database, copy local configuration, supply a shared password, or stop running applications. See [Build Packages](#build-packages) for credential handling and explicit test-data snapshots.

## Testing

Install development tools explicitly with `install_dependencies.bat --dev` or `python -m pip install -r requirements-dev.txt`. Runtime dependencies stay in `requirements.txt`.


Unified test runner:

```powershell
.\run_tests.bat --help
```

If `venv` is missing, `run_tests.bat` prompts:

`Dependencies are missing. Would you like to install them now? (Y/N)`

Common examples:

```powershell
.\run_tests.bat --full
.\run_tests.bat --quick
.\run_tests.bat --ai
.\run_tests.bat --phases
.\run_tests.bat --real-ai --yes
.\run_tests.bat --full --open-coverage
```

Notes:
- Running `.\run_tests.bat` with no arguments prints usage/help.
- `--real-ai` performs real network API calls and may incur provider cost.
- Test files and commands describe the available checks; record the commit, environment, provider and executed scope when reporting results. Browser scenarios and real-provider calls require their own validation.

## Deterministic offline checks

The GitHub workflow `.github/workflows/offline-tests.yml` installs pinned test
dependencies, then runs synthetic API/service/packaging tests and serial DOM
regressions. CI also checks the audited domain types and enforces the existing
80% whole-source line-coverage target. The test phase disables provider discovery
and real HTTP transports.
It excludes manual tests, existing-server browser tests and real-provider suites;
installation still requires access to package registries.

From a prepared PowerShell environment, the equivalent Python gate is:

```powershell
$env:SLM_OFFLINE_TESTS = "1"
$env:USE_REAL_AI = "0"
python -m pytest tests -q -ra --strict-markers --ignore=tests/manual --ignore=tests/e2e --ignore=tests/real_ai -m "not real_ai" --basetemp="$env:TEMP/slm-check-$([guid]::NewGuid())"
Remove-Item Env:SLM_OFFLINE_TESTS
```

For DOM checks, run `npm ci --ignore-scripts --prefix tests/ui`, then
`npm test --prefix tests/ui` with Node 20+. See [the UI test boundary](tests/ui/README.md).
These checks do not certify a Windows executable, a live browser or model quality.
See [maintained functional contracts](docs/FUNCTIONAL_REQUIREMENTS.md) for current
capabilities instead of historical desktop-module inventories.

## Browser E2E Testing (Chrome DevTools)

Manual browser validation scenarios are tracked in:
- `docs/BROWSER_TEST.md`

Recommended flow:

```powershell
.\start.bat
```

Then open `http://127.0.0.1:8080` in Chrome, open DevTools (`F12`), and execute the scenarios documented in `docs/BROWSER_TEST.md`.

## Build Packages

Build Windows packages on Windows with the project dependencies and PyInstaller
installed in the same Python environment. `build_package.bat` activates `venv`
when available and delegates to `scripts/build_package.py`. It resolves the
checkout from the script location, rather than the caller's working directory.
Relative `--database` and `--output-dir` arguments to the batch wrapper resolve
from that checkout; use absolute paths when selecting a database elsewhere.

Use Python 3.13 for the verified Windows build. The builder checks Tcl/Tk before
freezing and refuses Python installations using an unsupported zipfs layout
(observed with Python 3.14); do not bypass this preflight. See the exact build,
artifact hashes, acceptance results and remaining limits in
[Windows candidate report](docs/PRODUCTION_READINESS_WINDOWS_20261005.md).

The subsequent [source-clarification contract candidate](docs/SOURCE_CLARIFICATION_CONTRACT_20261005.md)
adds bounded lesson-output checks. Its exact-model semantic rerun and rebuilt
Windows artifact remain pending; the earlier EXE does not contain that change.

```powershell
.\build_package.bat --help
.\build_package.bat --prod
.\build_package.bat --prod --output-dir "dist\SLMEducator-next"
.\build_package.bat --test --database "C:\synthetic-fixtures\education.db"
```

Modes and data boundaries:
- `--prod`: Creates a new database in disposable staging and seeds its initial
  admin with the existing seeder. The working database, WAL/SHM files and local
  configuration are not read or changed. No running app is stopped.
- `--test --database PATH`: Requires an explicit existing SQLite database.
  SQLite's online backup API includes committed WAL data in a consistent,
  standalone snapshot. It does not copy live WAL/SHM files or run the seeder, so
  existing accounts and credentials remain unchanged. SQLite may manage source
  WAL/SHM sidecars and read marks during this explicitly requested backup; test
  mode does not promise byte-identical sidecars. Missing, invalid or
  persistently busy source databases fail the build instead of silently
  producing an empty package.
- Both modes generate configuration from the application's public defaults.
  Working `env.properties`, `.env`, `settings.properties`, test config and home
  security keys are never intentionally bundled. Configure the new package's
  `env.properties` after building; builder environment path overrides do not
  select a different database/configuration accidentally.
- Default outputs are `dist\SLMEducator` and `dist\SLMEducator_Test`. Existing
  output directories are refused, including prior packages with user data.
  Choose a new `--output-dir` for each rebuild. Staging and build caches are
  isolated and cleaned after success or failure.

For production, set `SLM_INITIAL_ADMIN_PASSWORD` to a unique password of at least
12 characters in the build process environment, or save the random password
printed once by the seeder. `SLM_INITIAL_ADMIN_EMAIL` optionally sets the new
account email. No plaintext credential file is included. Sign in as `admin` and
rotate the initial credential. Build separately for each installation: copying a
seeded package also copies its account and password hash. A bootstrap failure is
fatal; the builder will not report success for an unseeded package.

The frozen launcher uses the executable's directory for relative runtime paths,
so the packaged admin database and configuration work when launched from another
directory. Use a writable package location. Explicit runtime `SLM_DB_PATH` and
`SLM_CONFIG_FILE` overrides remain supported. Source-run launch behavior is
unchanged.

Test snapshots may contain personal information, accounts and encrypted provider
settings. Use synthetic data and do not distribute them. Encryption keys are not
exported; encrypted records require the matching key in the test runtime.

The `--prod` label is a build mode, not a production-readiness certification.
Automated packaging tests exercise real SQLite and the real seeder with a
simulated freezer. A native Windows build and packaged startup/login smoke test
are still required before distributing an executable.

## Teacher-reviewed local evaluation

New accounts require an authenticated administrator or teacher. Bootstrap remains create-only. Teachers create their own learners; resource access follows enrollment and authorship. The password-change screen uses `/api/auth/change-password` and revokes previous sessions after rotation.

New courses and assessments are drafts. Review and publish a course before assigning it. Assigned material is immutable; create a separate draft for revisions. AI-generated subjective grading remains provisional until the assessment author reviews it. Provider failure never becomes a final failing grade.

Assessment authors can configure assistance during open attempts: hints only, explanations, or disabled. See [assistance policy](docs/ASSISTANCE_POLICY.md). Timezone settings use an explicit UTC default or your chosen IANA zone; old offset-free history stays labelled unknown until a field-scoped, backed-up conversion with a known source zone. See [portability and recovery](docs/PORTABILITY_RECOVERY.md).

See [the implementation boundary](implementation_documents/LEARNING_LOOP_PLAN.md) for the two-teacher/two-learner synthetic scenario and the separate browser, native Windows and human-pilot acceptance gates.

## Repository Layout

```text
src/            application code (api, core, web)
tests/          unit/integration/e2e tests
scripts/        utility scripts
docs/           project documentation (including browser test guide)
translations/   i18n JSON files
```

## Troubleshooting

- Port conflict on `8080`: stop conflicting process or change port in `start.bat`.
- `python` not found: install Python 3.10+ and ensure it is in PATH.
- Dependency issues: recreate `venv` and reinstall requirements.

```powershell
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

- A missing initial admin can be created directly with the same first-run behavior described above:

```powershell
.\venv\Scripts\python.exe scripts\seed_admin.py
```

This command never resets an existing account or clears a lockout. For a known password, use the application's password-change flow after signing in. If access is lost or the account is disabled, stop and arrange an explicit recovery procedure with the administrator; changing bootstrap variables will not recover the account. Do not delete the database to regain access.

## Security Notes

- Do not commit real API keys, local logs, or runtime databases.
- Keep `.env`, `env.properties`, `settings.properties`, `logs/`, and `*.db` out of publishable exports.

## License

MIT. See `LICENSE`.
