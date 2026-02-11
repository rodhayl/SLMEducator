# SLMEducator

AI-assisted learning platform with teacher and student workflows.

## Requirements

- Windows 10/11
- Python 3.10+ (64-bit)
- Git

## Quick Start (Recommended)

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
- Seeds/updates the `admin` account with deterministic defaults
- Starts FastAPI with Uvicorn on port `8080`

## Manual Run (Alternative)

```powershell
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
```

## Configuration

- Copy `.env.example` to `.env` for local secret/env overrides.
- Copy `env.properties.example` to `env.properties` for app runtime defaults.
- Keep local-only runtime files out of published artifacts:
  - `.env`
  - `env.properties`
  - `settings.properties`

## Initial Admin Account

Default credentials used by `start.bat` and `build_package.bat --prod`:
- Username: `admin`
- Password: `Admin12345678`
- Email: `admin@example.invalid`

Optional overrides:
- `SLM_INITIAL_ADMIN_PASSWORD`
- `SLM_INITIAL_ADMIN_EMAIL`

Admin seeding logic lives in `scripts/seed_admin.py`.

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
- `--prod`: Creates a clean production package and recreates `slm_educator.db` with seeded admin credentials.
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
.\venv\Scripts\activate.bat
pip install -r requirements.txt
```

- Login issues after local DB changes: reseed admin explicitly.

```powershell
set SLM_INITIAL_ADMIN_PASSWORD=Admin12345678
set SLM_INITIAL_ADMIN_EMAIL=admin@example.invalid
.\venv\Scripts\python.exe scripts\seed_admin.py
```

## Security Notes

- Do not commit real API keys, local logs, or runtime databases.
- Keep `.env`, `env.properties`, `settings.properties`, `logs/`, and `*.db` out of publishable exports.

## License

MIT. See `LICENSE`.
