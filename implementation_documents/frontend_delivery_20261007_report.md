# React delivery and package boundary, 2026-10-07

## Status

Implemented and verified with synthetic tests in the shared Linux candidate. This
is delivery integration for an ongoing domain migration, **not** final GUI parity,
Windows readiness, an installer build, or real-browser acceptance. No legacy GUI
files were deleted. No Actions, publication, host, AppId or permission changes were
made. No user database, configuration or credentials were inspected or packaged.

## Files

- `src/api/main.py`: all existing API routers precede React delivery; status keeps
  the compatible `{status: online, version: 2.0.0}` response.
- `src/frontend_delivery.py`: shared schema/hash/path validation, explicit
  source/frozen/override resolution, static and SPA allowlist, legacy URL mapping,
  normal-lifecycle retirement worker, API404 and canonical API slash handling.
- `scripts/build_package.py`: explicit runtime allowlist, verified dist-only copy,
  lockfile consistency, post-copy/post-freeze validation, unchanged create-only
  bootstrap and snapshot/new-output rules.
- `tests/fixtures/frontend_artifact.py`: small synthetic lockfile/Vite/dist fixture.
- `tests/test_frontend_delivery.py`: source/frozen, routing, integrity, caching,
  redirect and synthetic service-worker behavior contracts.
- `tests/test_build_package.py`: narrow fixture inputs and package boundary tests.
- `tests/integration/test_student_pages.py`,
  `tests/integration/test_teacher_pages.py`: legacy reachability asserts deliberate
  redirects instead of requiring the retired multi-page mechanism; existing API
  authorization checks are retained.
- `README.md`, `docs/CONTRIBUTING.md`: explicit build, runtime and migration rules.

No frontend source, public directory or generated dist was edited by this work.
Foundation owns app-side existing-worker update checks and the npm build output.

## Runtime and artifact contracts

Only `src/frontend/dist` is selected by default. A frozen app uses its own
`_MEIPASS/src/frontend/dist`, or its own `_internal/src/frontend/dist` when that
runtime value is absent. It never searches neighboring source checkouts.
`SLM_FRONTEND_DIR` is the explicit override; legacy `SLM_WEB_DIR` is accepted only
as an explicit new-format dist override. Invalid/missing output fails clearly,
with UI503 and no legacy fallback. API routes and the retirement endpoint remain
independent of an unavailable UI build.

The validator checks schema 1, frontend identity, lockfile digest, unique relative
POSIX paths, every file's byte count/SHA-256, complete inventory, required
index/Vite/notices files, Vite references and local manifest-listed HTML assets.
Absolute paths, dot segments, backslashes, unsupported payload files, duplicate
records/properties, missing/unlisted files, symlinks/reparse points and tampered
bytes fail closed. Packaging also checks the source lockfile before staging and
revalidates staging, frozen output and exact staged-manifest identity.

Included runtime inputs are named root Python launcher/helper files, `.py` under
`src/api` and `src/core`, translation JSON, Alembic Python/templates, `alembic.ini`,
the existing seeder and recovery script, and the verified frontend dist. No
recursive `src/frontend` copy occurs. Frontend tooling, dependencies, tests,
source maps, source files and `src/web` are absent from staged runtime inputs.
Only included paths are inspected for links; excluded node_modules symlinks do
not cause a build failure or get followed. A final frozen frontend directory may
contain only `dist`; an unexpected legacy GUI or tooling sibling is rejected.

Known React deep links receive HTML with `no-cache`; hash-named assets receive
immutable HTTP caching. ETags support revalidation, and the bytes being served
are checked against the initialized artifact on every request. Rebuilds require
restart; a replaced file is not served under an old verified identity. API404,
unknown pages, unknown assets and private source/manifest paths do not return
SPA HTML with 200. API canonical trailing-slash redirects remain supported.

Legacy redirects translate only known pages and positive safe-integer IDs.
Dashboard redirects always enter `/inicio` with validated view/tab/context so
the client bridge can preserve the original hash > view > tab precedence.
Unknown hashes remain no-ops rather than accidentally activating a query-selected
view. Direct HTTP cannot inspect fragments. Known grading filters, course/content context, `mode=review`, `from_session=1`
and `ask_help=1` survive when relevant. Arbitrary URLs, duplicate/invalid IDs and
unknown query data are discarded. Old login returns are translated to a known
React destination before being passed as the new `return` parameter. The shared
portability destination is `/ajustes/datos`; admin-only backup remains
`/administracion/copias`.

## Service-worker boundary

`/sw.js` remains a no-store JavaScript response. The retirement worker has only
an activate handler: it removes exactly
`slm-educator-v22-session-locale` and
`slm-educator-v22-session-locale-auth-validation`, then unregisters itself. It
creates no cache, intercepts no fetch, calls no `skipWaiting` or `clients.claim`,
forces no navigation/reload and accesses no draft/localStorage/IndexedDB data.
No new worker is registered by this server. Foundation supplies the client-side
check/update for existing same-origin registrations.

Synthetic Node execution verifies that no deletion occurs before activation and
that foreign/unknown caches are untouched. This does **not** establish the real
browser lifecycle, dirty-tab safety, offline update or post-reopen controller
state. Those remain NOT RUN.

## Executed verification

Python environment:
`/workspace/scratch/1e4fc9d3fe09/slm-best-effort-6109-20261006/.venv/bin/python`

Main offline focused gate:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest \
  tests/test_frontend_delivery.py tests/test_build_package.py \
  tests/test_seed_admin.py tests/test_build_installer.py \
  tests/integration/test_student_pages.py tests/integration/test_teacher_pages.py \
  -q --basetemp=/tmp/slm-delivery-20261007-08
```

Final result after hash-bridge alignment and staged-resource verification:
**214 passed**, one existing Starlette/AnyIO deprecation warning, 74.22 s.
No tests were marked pass via skip. Earlier intermediate runs passed 202 tests,
then 49 package-only tests and the one isolated resource-closure test; the final
214-test gate includes those changes plus the new route/precedence regressions.

Focused flake8 on all changed Python files: PASS. Focused mypy with
`--follow-imports=silent` on `src/frontend_delivery.py` and
`scripts/build_package.py`: PASS. Python compileall: PASS.

The first targeted run exposed two issues: one test incorrectly expected a
literal `..` URL to survive httpx normalization, and the new catch-all masked API
slash redirects. The former test was replaced by encoded traversal coverage;
the latter was fixed in delivery and has an explicit regression. The subsequent
focused gates pass. Historical failures are not presented as acceptance.

## Runtime resource closure

A reference survey of maintained Python modules found no `importlib.resources`,
`pkg_resources` or file-based prompt/schema/template loaders under `src/core` or
`src/api`; those directories contain no non-Python files besides ignored bytecode.
Schemas and provider prompts are Python data/code. Runtime disk reads are generated
configuration, user-selected source/backup/database data, security storage and the
explicit translation files. The latter are included; user data/secrets are not.

`SettingsConfigService._create_default_config` generates configuration in code.
`src/settings.properties.template` has no consumers in the surveyed source,
scripts, tests or docs, contains obsolete defaults, and was already excluded by
the former `*.properties*` copy filter. It stays out of the runtime package. It
remains untouched as an explicit cleanup candidate for the root final dead-code
pass after a complete repository-reference inventory.

`test_staged_runtime_consumes_real_resources_without_checkout_fallback` was run
separately after adding it: **1 passed** in 1.69 s, using
`--basetemp=/tmp/slm-resource-closure-20261007-07`. It launches a new Python process with cwd/PYTHONPATH
restricted to the synthetic staged tree, creates public default configuration
without the unused template, loads actual EN/ES through TranslationService,
resolves Alembic's real migration heads and revisions, and uses Alembic's real
`generate_revision` to consume the included Mako template in that disposable
staging directory. No database migration is executed. This demonstrates the
resource consumers rather than simply asserting a duplicate list of package
paths. The first direct-Mako probe omitted Alembic's injected `comma` helper;
the final test uses the actual Alembic entry point instead.

The current real-checkout allowlist staging check also passed, without freezing
or seeding: 71 Python files and 11 verified frontend files. Observed frontend
manifest SHA-256 at that check:
`a3e54ec97c7a854d61559c2193741fc34ca1bca21e00b742bbecfd90a32584f6`.
This is a snapshot of generated output and is superseded by the next build.

## Outstanding integration/acceptance

- Foundation implemented the client-only dashboard hash bridge and its focused
  tests. This Python scope verifies safe transfer to `/inicio`; real-browser hash
  navigation and dirty-blocker interactions remain a separate acceptance gate.
- Domain owners must actually consume preserved context/role/filter parameters
  and complete `/ajustes/datos`; preserving the URL is not proof of domain parity.
- Frontend builds change as domain workers land. Rebuild after integration and
  run the integrity check again before candidate packaging; the currently checked
  generated dist is not evidence that later source edits are included.
- Legacy DOM/browser suites and full domain parity remain separate gates. No old
  source was deleted and no claim is made that every route is fully implemented.
- Real browser tests are NOT RUN because the existing Chromium process-singleton
  Unix-socket EPERM blocker remains. No bypass was attempted.
- Native Windows freeze, installer, startup/login/restart/DPI/process/port tests
  are NOT RUN. Simulated freezer/recipe tests are not native proof. Launcher work
  is owned separately by root.
- Whole-source coverage and a full application backend suite are not claimed by
  this focused delivery gate. Real-provider educational quality was not tested.
