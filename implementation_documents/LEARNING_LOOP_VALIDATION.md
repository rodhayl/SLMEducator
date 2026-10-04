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

## Single aggregate gate and focused repairs

The one applicable offline aggregate run was executed against frozen local
`cdbe0956a80ae05e24a7210f77885140220a4571`: **505 passed, 15 failed, 23 skipped,
5 real-AI tests deselected**, 235.42 seconds. Manual tests, real-provider suites
and tests requiring an existing browser server were excluded. Unexpected provider
transport fails closed in the synthetic test fixtures.

The 15 failures were traced to a missed canonical exception import, a valid
legacy flat-plan shape rejected by the new parser, and 13 help/session fixtures
or expectations inconsistent with the new authorization contract. The import
and legacy normalization were repaired; fixtures now establish actual enrollment
and assignment, and invalid resource IDs must fail without writes.

After these repairs and bounded edge-case hardening, **186 affected tests passed**
(75.71 seconds), including all 15 previously failing cases. The **22-case DOM
suite passed**. A later five-case generation slice additionally verifies persisted
cancellation, explicit retry, reserved order and preserved teacher edits. Critical
flake8 checks pass; focused mypy reports no issues in four new source files.
There was no second aggregate run. Do not describe the final tree as a new
all-suite green result or sum overlapping test counts.

Post-gate hardening also covers scoped participation leaderboards; missing,
corrupted, wrong-key and raw objective answer keys; immutable assigned assessment
rules; timer clearing; draft demotion; malformed HTTP-200 result recovery; and
saved API keys staying bound to the configured destination. Connection testing
uses a decrypted runtime credential without returning it to the browser.

## Approved requirement map

| Approved requirement | Code/deliverable | Evidence or remaining boundary |
| --- | --- | --- |
| Small reproducible local scenario and role matrix | Two teachers/two learners; bilingual three-lesson fixture; create-only pilot seeder; explicit policy | Synthetic API journey and seed refusal tests pass; no real people or institution selected |
| Permissions across content/link/tutor/session/help/submission/contact paths | Shared policy functions and route gates, including legacy unsafe-link denial | Role/resource regressions pass; not an exhaustive security certification |
| Safe rendering, truthful saves, recovery and account-separated drafts | Bundled DOMPurify, shared API/render/draft utilities, failed/malformed-result retention | DOM/source tests pass; live browser blocked, XSS/browser acceptance unverified |
| Password/settings/score/retry integrity | Token revocation, secret-redacted settings, bounded attempts, durable replay/rewards, strict-key handling | API, concurrent/slow-provider and corruption tests pass |
| Reviewed course, assignment version and coherent practice | Draft/review/publish, immutable assigned content/assessment rules, actual assessment drafts, reserved order and per-item retry | Full synthetic three-lesson API journey passes; human usability not established |
| Maintained UI, keyboard alternatives and languages | Existing Bootstrap/tokens/modules retained, non-drag controls, focus/status handling, English/Spanish pilot strings, Continue Learning | Static/DOM contracts pass; full keyboard, screen reader, theme/zoom/reflow and bilingual browser journeys unverified |
| Grounded optional AI with source limits | Bounded authorized text, source/page/section/hash/coverage, hint/explanation modes, typed failures and saved rubric/model/prompt provenance | Deterministic source/failure cases pass; source references are not automatic factual verification |
| Teacher-configurable assessment-assistance policy | Author/admin settings for hints, explanations or disabled; strictest open attempt applies across tutor/Q&A, including omitted context and delivery recheck; UI and portable mode | API/DOM contracts pass; requested hint semantics still need real-model evaluation. See ASSISTANCE_POLICY |
| Real-model usefulness and latency/cancellation | Proposed 12-case educator evaluation pack; bounded generation cancellation/resume | No real model/hardware or educator-rated evaluation; requires separate authorization and observation |
| Confidence, observed attempts and review | Confidence stored separately; final linked assessment scores drive review heuristic; legacy evidence labelled | Idempotent observed-review tests pass; heuristic is not validated learning efficacy |
| Exports, transactional import, backup and upgrade | Preview-first learner/teacher packages, remapped IDs/books/rubrics, encrypted private database archive, new-path restore, copy-first schema reconciliation | Synthetic roundtrip, corruption, wrong-key and packaging regressions pass; archive excludes keys/config/external files |
| Reproducible local setup/offline assets | Runtime/dev dependency separation, no launch-time install/upgrade, pinned bundled assets | Source/asset/package tests pass; native Windows build/start/restore and real offline browser operation unverified |
| Consistent legacy timestamps/user-local day | Offset-preserving UTC writes, explicit IANA setting/UTC default, known-instant day arithmetic, unknown legacy labels/guards, field-scoped copy-first migration | Temporal/auth/cache/scoring/recovery tests pass; unknown source zones remain unresolved by design, not silently guessed |
| Chosen shared deployment and protected Windows secret custody | Safe local-only default retained; backup requires matching separately held key | No remote-classroom deployment or OS-protected key-store rollout selected/validated |
| Pilot, evaluation and evidence-driven expansion | Synthetic scenario, proposed cases, observation template and conservative evaluator | Tooling tested; human pilot, institution/minors review, teaching acceptance and continuation decision not performed |

Implementation and real-world acceptance are tracked separately. Unknown historical timezone semantics and external acceptance gates remain explicit; no automatic inference or real-world readiness is claimed.


## Assistance and temporal completion checkpoint

The two previously partial code contracts are now implemented:

- Instructor-owned assistance mode is saved through a separate authorized API,
  enforced across chat and Q&A during open attempts, rechecked before delivery,
  exposed in the teacher/learner UI and preserved in teacher package import.
- New application timestamp writes preserve UTC offsets in the existing SQLite
  DATETIME schema. Offset-free history remains explicit unknown data. Daily goals
  and streaks use a selected IANA zone or an explicit UTC default. Conversion is
  opt-in, field-scoped, copy-first and backed up; DST gaps/folds are rejected.
  A field mixing unknown origins remains unresolved until provenance is supplied.

The final bounded integrated **policy/temporal/learning/recovery/packaging gate
passed 281 tests** (121.08 seconds); the **30-case DOM-emulation suite passed**.
This was an affected-contract gate, not a second aggregate suite. Earlier worker
batches of 105, 107 and 72 are overlapping scopes and are not added to this total.
Focused mypy passes five assistance/temporal modules, and critical lint, compilation,
JavaScript syntax and whitespace checks pass. No live provider was used.

The complete synthetic journey is tested, but native Windows execution, live
browser/assistive-technology acceptance, real-model quality and an authorized
human pilot remain unverified. The prepared pilot evaluation cannot mark mock
results as human evidence. No merge, deployment or visibility change is included.

## Final review regression

An independent frozen review passed 48 assistance/temporal/migration tests. It
found that Q&A failure responses fell back to unrestricted response metadata even
when the request had enforced hints only. The fallback now preserves the applied
policy and assistance mode for empty provider answers, provider exceptions and
service-construction failures. All three cases failed before the fix; the final
focused assistance/resource run passed 21 tests (5.46 seconds). Critical lint,
focused route type checking and whitespace checks pass. This metadata correction
does not change the server-side authorization or claim model-level compliance.
