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
- Installs/updates dependencies through `install_dependencies.bat`
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

**Unresolved packaging hazards:** `build_package.bat --prod` still replaces the root database and supplies a shared development password when its password override is absent. The create-only seeder does not prevent that deletion or change the build script's default. Do not run this build mode in a checkout containing valuable data. Packaging needs a separate safety repair before distributing packages. See [Build Packages](#build-packages).

## Testing

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

## Browser E2E Testing (Chrome DevTools)

Manual browser validation scenarios are tracked in:
- `docs/BROWSER_TEST.md`

Recommended flow:

```powershell
.\start.bat
```

Then open `http://127.0.0.1:8080` in Chrome, open DevTools (`F12`), and execute the scenarios documented in `docs/BROWSER_TEST.md`.

## Build Packages

Build script:

```powershell
.\build_package.bat --help
```

Modes:
- `--prod`: Creates a clean package and recreates `slm_educator.db` with seeded admin credentials. The flag names a build mode; it is not a production-readiness certification.
- `--test`: Packages the current working `slm_educator.db` (if present).

Examples:

```powershell
.\build_package.bat --prod
.\build_package.bat --test
```

Important:
- Packaging requires `pyinstaller` available in the active environment/PATH.
- `--prod` intentionally replaces local `slm_educator.db` in the repository root during packaging.

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
