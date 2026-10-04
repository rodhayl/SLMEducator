# Product implementation and acceptance evidence, 2026-10-04

## Stable synthetic implementation checkpoint

The approved phases 0–5 are implemented in the existing FastAPI, SQLite, HTTPX
and Bootstrap architecture. The requirements map and checkpoint history are in
[PRODUCT_CLOSURE_PLAN.md](PRODUCT_CLOSURE_PLAN.md). This record separates executed
checks from repository quality debt and external acceptance.

The single stable offline aggregate ran against local source commit
`9f9421dda1170da2d8a13e94fcaf1fe36b37c88c`, tree
`edfc33a6d6579285289cdaec5b00d82a09b538ff`:

- **721 passed, 0 failed, 23 skipped, 5 deselected**, in **404.16 seconds**.
- All 23 skips require a configured live provider. Five real-AI-marked cases were
  deselected. Manual, existing-server browser and real-provider directories were
  excluded explicitly. No inference, provider discovery or real HTTP transport ran.
- **154 serial DOM tests passed**, without cancellations, skips or failures. No
  web source changed after this DOM run. DOM emulation is not browser acceptance.
- Critical Python syntax/name lint passed. Five focused modules passed mypy with
  `--follow-imports=skip`; this is not a transitive whole-application type pass.
- Pinned installed dependencies passed the compatibility check. The committed
  phase-5 delta secret scan found no leaks. Whitespace and Python parsing passed.
- Packaging/seeder affected scope passed **58 tests** with real synthetic SQLite
  and a simulated freezer. No native Windows executable was built or run.

Python gate (from a prepared environment):

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest tests -q -ra --strict-markers \
  --ignore=tests/manual --ignore=tests/e2e --ignore=tests/real_ai \
  -m 'not real_ai' --basetemp=/tmp/slm-product-final-UNIQUE \
  --cov=src --cov-report=term --cov-report=json
```

Node gate uses the pinned `tests/ui/package-lock.json` and
`node --test --test-concurrency=1 tests/ui/*.test.cjs`. CI installs the dependencies
before these offline checks; registry access during setup is not an inference call.

## Quality work continuing after this checkpoint

Whole-`src` line coverage is **6,347 / 8,745 statements (72.58%, rounded 73%)**,
below the documented 80% target. No exclusions were added to increase the number.
The Windows launchers, older database/progress services, AI adapter/error branches
and settings code account for much of the uncovered surface. Additional meaningful
synthetic tests are required before claiming the coverage target is met.

A transitive mypy run targeting course/generation workflow reports **21 diagnostics
in five files**. A shadow-file run at the previous checkpoint produced the same
21 diagnostic identities, so this closure delta introduced none of them. They
are still outstanding work, not a passing quality gate:

- ORM relationship typing in assessment/course snapshots: relationships inferred
  as `Mapped[Any]` rather than iterable domain objects.
- Nullable ORM identifiers, positions and totals used where integers are required.
- Optional streak dates subtracted without explicit narrowing in the database and
  progress services.
- Optional assessment grading mode accessed without a declared default/narrowing.

Follow-up fixes must retain this aggregate result tied to its original source and
record their own affected checks. They must not relabel this run as evidence for
later untested changes or erase the earlier historical 505/15 run.

## Requirement map

| Phase | Maintained implementation | Automated evidence |
| --- | --- | --- |
| 0: roles/privacy/contracts | auth and annotation scope; canonical content/assessment/graph validation | role/auth, privacy, resource, ingress and annotation-mutation regressions |
| 1: curriculum/provenance | canonical sections; extraction/usage manifests; captured sessions; stale-source delivery/save guards | source documents, generation sources/ingress, product journeys |
| 2: role journeys | completion/pause/restart, attempts and feedback, grading links, enrollment/copies/admin recovery | three-lesson journey, scoring/session, account-recovery and role/assessment DOM suites |
| 3: optional bounded AI | context/policy recheck, supported settings, concurrency/quota/deadline/cancel, accurate receipts | assistance/resource/lifecycle and help/tutor/settings DOM suites |
| 4: portability/recovery | v2/v1 teacher graph, learner HTML/Markdown/JSON, preview/import, separate backups/time migration | readable portability, recovery/migration and portability DOM suites |
| 5: maintainability/acceptance | local assets, shared safety/labels, import/resource packaging audit, dead-code removal, synthetic CI | setup/source/style/packaging/DOM checks and the aggregate above; quality debt remains explicit |

## External acceptance gates

- Native Windows clean-machine build, startup/login/rotation/restart/shutdown and
  restore, including translations, source extraction and portability.
- Real-browser keyboard/focus, screen-reader, zoom/reflow and full English/Spanish
  role journeys. The prior cloud browser localhost attempt was blocked; source
  and DOM tests cannot substitute for an observed browser run.
- Real-model usefulness, grounding, assistance semantics and hardware latency with
  educator-rated cases. Mocked output is never recorded as model-quality evidence.
- An authorized human pilot and any applicable institutional/minors/privacy review.
  Synthetic adult fixtures do not establish educational efficacy or suitability.

One local process remains the supported evaluation scope. Cancellation suppresses
local delivery; a provider may continue processing and charging. Unknown usage,
source provenance and historical timezone data remain explicitly unknown.
No main merge, deployment or executable distribution is included.
