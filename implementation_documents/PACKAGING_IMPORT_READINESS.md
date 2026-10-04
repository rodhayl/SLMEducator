# Packaging manifest and resource validation, 2026-10-04

Scope: phase 5 packaging/dead-import cleanup, based on `ed934f2`. Changes are
limited to the builder, its focused tests and this evidence record. This is not
native Windows executable acceptance.

## Import audit

- Remove `passlib` and `passlib.hash`: neither maintained application source nor
  runtime requirements uses them. Password hashing/verification delegates to
  `src/core/security.py`, which imports the already-required `bcrypt`. The
  manifest now names `bcrypt` explicitly.
- Remove `langsmith`, `langchain_core` and `langchain_openai`: source contains no
  imports or dynamic loads, and requirements contain none of these packages.
  `src/core/services/ai_service.py` uses HTTPX for the supported provider paths.
- Remove `tkinter.scrolledtext`: the launcher uses `tk.Text` with `ttk.Scrollbar`;
  no maintained source references the scrolledtext module. Retain `tkinter`,
  `tkinter.ttk` and `tkinter.messagebox`, which the launcher imports.
- Add `uvicorn.protocols.websockets.auto`: the pinned Uvicorn 0.40.0 default
  configuration resolves this protocol through a string import. The HTTP, loop
  and lifespan default dispatch modules were already listed. A regression checks
  all four against the installed Uvicorn configuration.
- Complete the explicit API route manifest with `portability`, `timezone` and
  `assistance`, all mounted by `src/api/main.py`. A source-AST check prevents
  mounted routes from falling out of the manifest and rejects nonexistent source
  module hints without importing the application.
- Retain existing FastAPI/Starlette, Pydantic, SQLAlchemy, multipart, crypto/JWT,
  HTTPX and server-transitive compatibility entries. They belong to the current
  dependency stack; absence from direct app imports alone is not evidence that
  framework-internal loading is unused. IANA timezone collection remains present.
- The old `export_import_service.py` contains dynamic Markdown/PDF paths but had
  no callers in application code, scripts or tests during this audit. Current
  learner exports use `portability_service.py`. The closure pass removed that unreferenced service and its otherwise unused
  Markdown/ReportLab runtime dependencies. Current readable portability and PDF
  source extraction are retained and checked by their focused regression suites.

These source/manifest findings identify removed dependencies and missing explicit
hints. They do not establish that a native freezer previously failed or that all
third-party dynamic imports have been exhaustively exercised.

## Resource and safety regressions

Tests exercise frozen path helpers from an unrelated directory against a
simulated package layout. They confirm the seeded database and generated
configuration remain relative to the executable,
web resources resolve to `_internal/src/web`, and both English and Spanish JSON
translations load from `_internal/translations`. Every public web, translation
and Alembic file in the synthetic fixture is byte-compared with its packaged copy.
The command still collects `tzdata` for Windows timezone lookup.

Existing real-SQLite/real-seeder checks preserve create-only bootstrap, explicit
WAL-aware test snapshots, unchanged production source files/sidecars, secret and
configuration exclusion, symlink rejection, refusal to overwrite outputs and
staging cleanup after failures. The new CLI check proves non-Windows invocation
fails before freezing or writing output. All database fixtures are synthetic.

## Executed checks

- `.venv/bin/python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q --basetemp=/tmp/slm-package-seeder-final-20261004-1542`: **58 passed in 21.96 seconds**.
- `.venv/bin/python -m flake8 scripts/build_package.py tests/test_build_package.py`: passed.
- `.venv/bin/python -m mypy scripts/build_package.py tests/test_build_package.py --follow-imports=skip`: passed for both files.
- `git diff --check`: passed.

This was the affected scope only, not a full-suite aggregate. PyInstaller is not
installed in the Linux test environment; the freezer is simulated. No executable
or distribution build was attempted. Temporary synthetic test directories were
removed after validation.

## External acceptance gate

Before distributing a package, build on Windows using the intended Python,
requirements and PyInstaller environment. Review freezer warnings, launch from
an unrelated working directory, verify startup/status and initial login, rotate
the password and restart, and check the main role pages, both translations,
timezone handling, source PDF upload and supported portability formats. Use only
synthetic data and a stubbed provider for this gate. Record the exact commit,
Windows/Python/PyInstaller versions and outcomes. No Windows executable was built
or run by the Linux checks described here.
