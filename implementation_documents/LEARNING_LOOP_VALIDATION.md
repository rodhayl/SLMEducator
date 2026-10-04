# Learning-loop implementation validation

## What is implemented

- One reproducible synthetic two-teacher/two-learner, three-lesson fractions
  scenario (`scripts/seed_pilot.py`), with explicit draft/review/publish/assign flow.
- One resource policy for content, plans, enrollment, submissions, help and
  messaging; private material cannot gain visibility through an unauthorized link.
- Bounded source context reaches the tutor, with references/version/coverage;
  AI output is a suggestion, never automatically source-verified.
- Password rotation/revocation; round-tripped AI settings without redisplaying
  keys; durable scoring/session replay with bounded points and teacher-controlled
  provisional subjective grading. Slow providers do not hold the write transaction.
- Shared maintained HTML sanitizer, HTTP error handling and account/attempt-scoped
  expiring drafts; local pinned frontend assets, keyboard ordering, recovery states,
  independent practice and explicit teacher publication controls.
- Canonical content, executable generated assessment drafts and durable per-item
  generation retry that preserves existing teacher edits. Partial/invalid generation
  never claims all items were saved. Cancellation takes effect between provider calls.
- Preview-first learner/teacher export, transactional draft import with remapped
  references/rubrics/books, encrypted private database backup, new-path restore and
  copy-first additive schema upgrades. Setup is explicit; launch does not install.
- Final assessed evidence is separated from confidence and historical review data;
  versioned proposed evaluation cases and conservative pilot-observation tooling.

## Executed evidence so far

Checkpoint 1: 48 focused authorization/auth/course/scoring tests passed, with an
independent 53-test scoring/grading slice. The staged delta had no gitleaks findings.
A parent independent frozen-source run passed the 10 resource contract tests.

Checkpoint 2 development: source/generation retry tests, a complete synthetic API
journey through three lessons/notes/resume/attempt/teacher-feedback/export/import,
observed-review separation, pilot seeding/evaluation and explicit-setup tests pass.
The scoring/recovery worker passed 46 focused tests and a 66-test portability plus
bootstrap/packaging slice. Counts overlap and must not be summed as unique tests.
Checkpoint 2 frozen affected integration slice: 69 passed. Frontend: 18 jsdom
behavior checks and 24 source/style/served-page checks passed; JavaScript syntax
checks passed. Focused mypy passed four new source files and focused critical
flake8 checks passed. These counts describe separate, overlapping scopes.

The final applicable offline aggregate gate is recorded after the implementation
stabilizes; these bounded passes are not that gate.

## Evidence limits, not invented acceptance

- Browser navigation from the available cloud browser to the isolated local test
  server returned `ERR_BLOCKED_BY_CLIENT`. DOM emulation/source tests are not a live
  browser, keyboard, screen-reader, zoom/reflow or visual acceptance result.
- Windows executable tests use a simulated freezer on Linux. Native clean-machine
  build/start/rotation/restart/shutdown/restore remains a separate acceptance gate.
- No real model calls, paid inference or model-quality/hardware latency evaluations.
  Proposed teaching cases still need educator review and actual observed responses.
- No human pilot, real learner information, child-suitability finding, institution
  approval or legal acceptance. `evaluate_pilot.py` cannot promote synthetic results
  to a human acceptance decision or educational efficacy claim.
- One local application process and SQLite remain the supported evaluation scope.
  No hosted/multi-school deployment, main merge or public-visibility change.
- Private backup excludes encryption/JWT keys, runtime configuration and external
  uploads. Matching existing encryption key is required; source schema upgrades
  refuse destructive/type-changing inference and preserve the original file.
