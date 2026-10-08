# SLMEducator: AI-Assisted Teaching and Learning

**Status:** Source-run application for local development and evaluation. The repository includes test suites and Windows packaging scripts; packaged GitHub releases are not currently provided.

SLMEducator brings teacher and student workflows into a Python/FastAPI learning application. It combines study plans, lessons, exercises, tutoring and learning-session tracking with configurable local or cloud AI providers. Its goal is best-effort educational help, including when students cannot reach a teacher at the moment they need assistance. AI suggestions can be useful and still contain errors; the application does not promise perfect answers.

## What this project demonstrates

- Teacher workflows for creating and improving study plans, lessons, exercises and assessment questions.
- Student tutoring, learning-session lifecycle and progress/history handling.
- Provider integration separated from application services and persistence.
- Source setup, automated tests, browser validation scenarios and Windows packaging.

Use demonstration data for evaluation. Students can ask the tutor or Q&A without a teacher being online, with or without selected course material. Previously assigned lessons and practice remain available independently of teacher presence. Creating structured courses, lessons and exercises remains a teacher/administrator workflow; shared publication and assignment require review, and subjective AI grades remain provisional. Provider selection determines whether inputs leave the machine. This repository does not establish improved learning outcomes, suitability for children or regulatory compliance in a particular deployment.

## Requirements

- Windows 10/11
- Python 3.10+ (64-bit)
- Git

## Quick Start (Windows)

Clone this repository and open PowerShell in its root. Before launching, prepare the [React frontend build](#react-frontend-build) and review [Initial Admin Account](#initial-admin-account). For a new installation, a local first-run dialog lets you choose the administrator username and password before the server starts.

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
- Opens local first-administrator setup only for a verified fresh installation; existing accounts and their security state are preserved
- Starts FastAPI with Uvicorn on port `8080`

## Manual Run (Alternative)

Prepare the [React frontend build](#react-frontend-build) and review
[Initial Admin Account](#initial-admin-account) before starting. The local setup below lets the installation owner choose the first account and preserves existing accounts. Canceling setup stops startup. Use --console instead of --interactive on a machine with an interactive terminal but no native window.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe scripts\seed_admin.py --interactive
.\venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
```

## React frontend build

The active server serves only the React build from `src/frontend/dist`. Prepare
it explicitly before source startup or packaging (Node 22.22+ is a build tool):

```powershell
cd src/frontend
npm ci --ignore-scripts
npm run check
cd ../..
```

`npm run check` includes typecheck, lint, synthetic frontend tests and the
production build. A subsequent explicit `npm run build` is sufficient to rebuild
already-checked sources. Missing or invalid output produces a clear HTTP 503 for
the UI; the API remains reachable. There is no fallback to the legacy GUI.
Node, npm, source maps, frontend sources and build tools are not runtime needs.

The package builder validates the build manifest, asset sizes/SHA-256 hashes,
Vite references, local HTML assets and matching npm lockfile/source-input digest
before any seeding or freezing. The canonical build fingerprints source, styles,
public assets and build configuration/tooling before compilation and refuses to
seal output if those inputs change. A source edit, addition or removal requires
an explicit rebuild, even when the lockfile did not change. Only verified dist
files join the allowlisted Python/runtime resources. Frontend tooling, dependencies, tests and `src/web` are excluded.
Build output must be complete, contain no unlisted files or symlinks, and match
the lockfile and source inputs; the builder never installs dependencies or starts
a frontend build. Frozen runtime validates the embedded identity and shipped
bytes without requiring the source checkout or Node.
A manifest is an integrity inventory, not a signature or native acceptance result.

Known old `.html` links redirect to allowlisted React routes with validated IDs.
Unknown routes and assets return real 404 responses; `/api/` errors never become
HTML. The frozen app uses only its own bundled dist. `SLM_FRONTEND_DIR` explicitly
selects another verified dist; the older `SLM_WEB_DIR` name accepts only that same
new format. Invalid overrides fail clearly rather than selecting another tree.
Restart the server after replacing source-build output.

Fresh installs register no service worker. `/sw.js` remains temporarily available
only to retire the two recognized old SLM caches through the normal worker
lifecycle. Save your work and close old application tabs before reopening to
finish that transition. No tab is force-reloaded, no browser drafts or other
apps' caches are erased, and offline API/inference is not provided by a cache.
Real-browser update/dirty-tab coverage and native Windows package validation are
separate acceptance gates, not implied by synthetic tests.

## Configuration

- Copy `.env.example` to `.env` for local secret/env overrides.
- Copy `env.properties.example` to `env.properties` for app runtime defaults.
- Keep local-only runtime files out of published artifacts:
  - `.env`
  - `env.properties`
  - `settings.properties`

AI settings accept a model name and endpoint through the Ollama, LM Studio,
OpenAI and OpenRouter adapters. Choose a model compatible with the selected
adapter's API and response requirements; this is not a guarantee that every
model or API works. No second model is required. Tutor/Q&A accepts a JSON object
containing a nonempty `answer`, `explanation` or `response`, or a nonempty plain
prose reply. The prose fallback excludes structural delimiters and code fences;
it does not rescue broken JSON or mark answers verified. Provider/protocol errors
remain failures. Structured authoring and grading keep their validation contracts.

Once the local application, dependencies, data and a local model are prepared,
Internet access is not required for the local-provider path. Cloud providers need
connectivity. The browser still needs the running application server; bundled static
assets do not provide offline API data or inference. Exported learner handouts
can be read separately. Hardware suitability and installation preparation remain
deployment considerations.

## Initial Admin Account

Fresh production packages contain no administrator account or password. Before
starting the HTTP server, the native launcher opens a local setup dialog for the
installation owner to choose a username and password and confirm it. Passwords
are masked and never printed, logged, placed in a URL, or sent to an HTTP setup
endpoint. Cancel closes setup without starting the server. The console fallback
requires an interactive local terminal and uses hidden password entry.

`start.bat` uses `scripts/seed_admin.py --interactive` for the same setup. The
headless launcher uses the terminal flow. For manual source startup, finish this
step before running Uvicorn. Once an administrator exists, launch leaves all
accounts, passwords, roles, lockout and authentication history unchanged.

Setup eligibility is marked only when this local bootstrap creates a brand-new
database (or when a production package prepares an account-free database). The
first account and completed marker are committed under one SQLite write lock.
Concurrent submissions cannot create two initial administrators. An existing
empty/unrecognized database, or a configured installation with its administrators
removed, requires authorized recovery; setup does not reopen.

The older explicit `python scripts/seed_admin.py` command remains a development
provisioning tool. It preserves any existing `admin` username; for a missing one
it accepts `SLM_INITIAL_ADMIN_PASSWORD` or generates a one-time credential. Normal
launch and production packaging no longer use that automatic-account path. Never
put credentials in shared commands, reports or commits. Production packages ignore
build-time bootstrap password/email variables and let each local owner choose.

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
python -m pytest tests -q -ra --strict-markers --ignore=tests/manual --ignore=tests/real_ai -m "not real_ai" --basetemp="$env:TEMP/slm-check-$([guid]::NewGuid())"
Remove-Item Env:SLM_OFFLINE_TESTS
```

For React checks, run `npm ci --ignore-scripts --prefix src/frontend`, then
`npm run check --prefix src/frontend` with Node 22.22+. This includes TypeScript,
ESLint, serial DOM tests and the production build. See [the frontend boundary](src/frontend/README.md).
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
adds bounded lesson-output checks. The
[Windows v9 semantic/GUI report](docs/reports/windows-v9-semantic-gui-20261006/REPORT.md)
records 37/44 cases accepted strictly, with local GUI repairs. The later
[single-pass report](implementation_documents/lesson_claim_consistency_20261006_final_pass_report.md)
preserves 30/44 historical and 10/12 development results, with 61/61 inference
traces. These scores are diagnostics under their recorded strict rubric, not a
requirement for perfect model output before building a best-effort candidate.
Historical results and failures are unchanged. The earlier EXE does not contain
subsequent source changes; a new package still needs native build/start/login
verification before distribution.

For future candidates, acceptance distinguishes application integrity from model
quality: usable student workflows, explicit failure/retry behavior, visible
uncertainty, data isolation and unchanged publication/grading boundaries are
required. A safe error is a handled failure, not evidence that the student
received useful instruction. Model quality observations remain visible without
automatically triggering another model-selection or scoring campaign.

```powershell
.\build_package.bat --help
.\build_package.bat --prod
.\build_package.bat --prod --output-dir "dist\SLMEducator-next"
.\build_package.bat --test --database "C:\synthetic-fixtures\education.db"
```

Modes and data boundaries:
- `--prod`: Creates an account-free database in disposable staging and marks it
  eligible for local first-launch administrator setup. The working database, WAL/SHM files and local
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

Production builds never create or bundle a shared login. Each installation owner
chooses credentials locally on first launch. Do not redistribute a database after
setup: it contains that installation's accounts and private data. Test snapshots
retain their explicitly selected accounts and are never converted into a new
first-run installation.

The frozen launcher uses the executable's directory for relative runtime paths,
so the packaged admin database and configuration work when launched from another
directory. Use a writable package location. Explicit runtime `SLM_DB_PATH` and
`SLM_CONFIG_FILE` overrides remain supported. Source-run launch behavior is
unchanged.

Test snapshots may contain personal information, accounts and encrypted provider
settings. Use synthetic data and do not distribute them. Encryption keys are not
exported; encrypted records require the matching key in the test runtime.

The `--prod` label is a build mode, not a production-readiness certification.
Automated packaging tests exercise real SQLite and first-run preparation with a
simulated freezer. A native Windows build and packaged startup/login smoke test
are still required before distributing an executable.

### Windows installer (Inno Setup)

`build_installer.bat` wraps a fresh `--prod` payload in a per-user Windows
installer. It reuses `scripts/build_package.py --prod` for the payload and
compiles `installer/SLMEducator.iss` with Inno Setup 6 (`ISCC.exe`).

```powershell
.\build_installer.bat --payload-dir "C:\builds\SLMEducator payload" --output-dir "C:\builds\SLMEducator setup" --version 2.0.0
```

Both directories must be new and absolute. The installer installs under
`%LOCALAPPDATA%\Programs\SLMEducator` without administrator rights, keeps the
installation database and generated `env.properties` as user data across reinstall
and uninstall, and refuses to update an existing installation in place.
See [the installer recipe](docs/WINDOWS_INSTALLER.md) for boundaries and limits.

## Teacher-reviewed local evaluation

New accounts require an authenticated administrator or teacher. Bootstrap remains create-only. Teachers create their own learners; resource access follows enrollment and authorship. The password-change screen uses `/api/auth/change-password` and revokes previous sessions after rotation.

New courses and assessments are drafts. Review and publish a course before assigning it. Assigned material is immutable; create a separate draft for revisions. AI-generated subjective grading remains provisional until the assessment author reviews it. Provider failure never becomes a final failing grade.

Assessment authors can configure assistance during open attempts: hints only, explanations, or disabled. See [assistance policy](docs/ASSISTANCE_POLICY.md). Timezone settings use an explicit UTC default or your chosen IANA zone; old offset-free history stays labelled unknown until a field-scoped, backed-up conversion with a known source zone. See [portability and recovery](docs/PORTABILITY_RECOVERY.md).

See [the implementation boundary](implementation_documents/LEARNING_LOOP_PLAN.md) for the two-teacher/two-learner synthetic scenario and the separate browser, native Windows and human-pilot acceptance gates.

## Repository Layout

```text
src/            application code (api, core, frontend)
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
.\venv\Scripts\python.exe scripts\seed_admin.py --interactive
```

This command never resets an existing account or clears a lockout. For a known password, use the application's password-change flow after signing in. If access is lost or the account is disabled, stop and arrange an explicit recovery procedure with the administrator; changing bootstrap variables will not recover the account. Do not delete the database to regain access.

## Security Notes

- Do not commit real API keys, local logs, or runtime databases.
- Keep `.env`, `env.properties`, `settings.properties`, `logs/`, and `*.db` out of publishable exports.

## License

MIT. See `LICENSE`.
