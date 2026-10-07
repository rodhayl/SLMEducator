# Frontend source/build identity, 2026-10-07

## Result

The package boundary now rejects an otherwise valid dist when its TypeScript,
CSS, public assets, build configuration or tooling differ from the inputs used
by the canonical build. Runtime still needs only the packaged dist and Python;
it neither reads a source checkout nor invokes Node/npm.

This completes the source/build integrity implementation and its focused
synthetic tests. It does **not** seal the final integrated GUI candidate: other
frontend changes were still landing during this work. Run the final canonical
build and source-aware validation after those changes finish.

## Implementation

- `src/frontend/scripts/build.mjs` is the only `npm run build` entry point. It
  invalidates the old completion manifest, fingerprints inputs, runs the locked
  local TypeScript/Vite tools through the existing Node process, then seals only
  if the input fingerprint remains unchanged. Tool failure leaves no valid
  completion manifest. It never installs dependencies.
- `src/frontend/scripts/source-identity.mjs` and `src/frontend_delivery.py` implement identical
  source identity version 1. Sorted UTF-8 paths, byte counts and SHA-256 values
  are NUL/newline framed, then hashed. Non-ASCII ordering and binary/CRLF contents
  are covered by a JS/Python parity test.
- Input inventory: `index.html`, `package.json`, `package-lock.json`,
  `tsconfig.json`, `vite.config.ts`, all files under `src/` and `scripts/`, and
  optional `public/`. Links fail closed. Dist, dependencies, docs and tests are
  not production inputs. Future imports outside this inventory must extend both
  implementations before being used in a production build.
- Tailwind's import explicitly scans `src/`, so unrelated documentation/tooling
  cannot silently affect candidate CSS. Vite has `envDir: false`; the canonical
  child environment excludes `VITE_*` injection and sets `NODE_ENV=production`.
  No private `.env` file is read for the fingerprint or loaded by Vite. The UI
  continues using relative `/api` and backend-owned settings.
- `build-manifest.json` is schema 2, with required source identity version and
  digest. A schema-1 artifact requires a rebuild. Running the manifest tool by
  itself fails rather than refreshing metadata over old output.
- The Python package builder compares source identity before and after staging,
  before any seeding/freezing. Frozen validation retains the embedded digest
  and full asset integrity/reference checks without requiring source files.
- Synthetic artifact fixtures use schema 2 and preserve their source identity
  when a test intentionally edits output. No generated source/tooling enters the
  frozen runtime allowlist.
- Requested compatibility fix: `/register.html` preserves exactly one
  `role=student|teacher|admin` to `/personas/nueva`; duplicate/unknown values and
  unrelated query data are discarded. This changes a route hint, not permissions.

A source fingerprint is an accidental-staleness/torn-build check. It is not a
signature, tamper-proof provenance proof, native acceptance result or guarantee
of reproducibility across toolchain/platform/environment differences.

## Verification

Python environment:
`/workspace/scratch/1e4fc9d3fe09/slm-best-effort-6109-20261006/.venv/bin/python`

Final affected gate:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest \
  tests/test_frontend_build_identity.py tests/test_frontend_delivery.py \
  tests/test_build_package.py tests/test_seed_admin.py tests/test_build_installer.py \
  -q --basetemp=/tmp/slm-source-identity-final2-20261007
```

**242 passed**, one existing Starlette/AnyIO deprecation warning, 92.84 seconds.
The captured summary is `frontend_source_identity_20261007_tests.txt`.
This includes **19 source-identity tests** and stale TS/CSS/add/delete source
variants in package tests. Nothing in this gate was skipped.

Checks include:

- Changed TS/CSS/entry/package/tsconfig/Vite/tooling/public inputs fail against
  an unchanged dist; new/deleted files fail before seeding/freezing.
- Source changes during staging fail the second comparison.
- Source changes during compilation cannot produce the completion seal.
- A failed canonical compiler invalidates a previous completion manifest.
- Standalone manifest refresh is rejected.
- Input symlinks are rejected; excluded outputs/dependencies/private env/docs
  do not affect the production source digest.
- JavaScript and Python fingerprints agree for Unicode paths, binary bytes and
  mixed LF/CRLF line endings.
- A separate Python process serves root/deep-link/assets from a synthetic frozen
  tree after its source checkout is deleted. PATH is empty and neither Node nor
  npm can be resolved. No source or npm lockfile is bundled with that dist.
- Allowlisted registration role redirects survive; duplicate/unknown roles do
  not. Existing redirect, asset, bootstrap, package and installer-recipe tests
  remain green.

Focused flake8: PASS for delivery, package builder, fixture and affected tests.
Focused mypy (`--follow-imports=silent`): PASS for delivery and package builder.
Node syntax checks for all three build modules and Python compileall: PASS.

An actual canonical npm build passed during integration: 2,016 modules and
25 verified local assets. Tailwind accepted the explicit src scan, and generated
CSS retained grid, stack, form-grid, button, app-shell and prose selectors.
Subsequent source changes were correctly rejected by the new Python source-aware
validation even though the existing dist/lockfile remained internally valid.
That intermediate build is superseded; it is not the final integrated artifact.

One intermediate gate had a test-fixture-only failure: the fake compiler test
used intentionally non-JSON synthetic package metadata. The test now supplies
valid package metadata, reaches the intended compiler failure and passes. A
concurrent frontend typecheck briefly observed unfinished migration-test unused
parameters; that file was owned and corrected by the migration worker. The
subsequent `npm run typecheck` rerun passed. Final integrated lint/full frontend
tests/build remain the parent gate.

## Limits and final handoff

No dependency install, private database/configuration read, Windows installer
execution, real model call, publication or browser-blocker bypass occurred.
Synthetic freezer/recipe and simulated frozen Python tests are not proof of a
native Windows executable. Real browser/paint/zoom/service-worker lifecycle and
native Windows acceptance remain separate gates.

After all frontend inputs are stable:

1. Run the final aggregate frontend checks and `npm run build` from
   `src/frontend` (the aggregate `npm run check` already ends in this build).
2. Run `validate_frontend_dist(dist, lockfile=frontend / 'package-lock.json',
   source_root=frontend)` or the package staging boundary. Do not omit
   `source_root` when certifying a checkout's build identity.
3. Record final input/manifest hashes only after those checks. Runtime calls
   intentionally omit source_root and remain source-checkout independent.
