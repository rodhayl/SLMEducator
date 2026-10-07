# Continuity fixes G1–G5

Date: 2026-10-07. Base commit:
`b6cec26254cb9ca5d0bb64f70a2cac912efeb6f3`.
This is a bounded continuation of the approved React GUI plan.

## Changes

- Q&A keeps unsaved title, question, answer and sharing state across Tutor tabs.
  Its private detail stays registered during same-account reauthentication so
  current resource access is checked before the hidden editor is exposed.
- Tutor panels mount on first use and keep their temporary state while hidden.
  Completed history survives tab changes; the same pending request can finish
  without duplicate inference. Cancel remains explicit. Account, credential,
  context, source-version and policy changes still fence stale delivery.
  Hidden panels cannot leave confirmation portals visible.
- Courses and Material library have reciprocal navigation. Staff can reach
  independent manual creation and generation without first creating a course;
  learners have authorized read access without authoring controls.
- Course search and People filters survive detail returns. Fixed local return
  links preserve selection; account-scoped canonical list keys preserve scroll
  for browser Back and explicit return, including reordered query parameters.
  People creation carries the directory origin through its result/detail.
- The shell applies the current account's validated saved animation preference
  on reopening, including outside Settings. It uses the existing scoped query
  and appearance provider, resets on account replacement/logout, and adds no
  persistent browser store. Unsaved form changes do not alter motion. The
  optional motion read does not become a new reauthentication prerequisite.

The API/query/auth adapters and AI request hook are unchanged. No automatic
mutation replay, permanent conversations, broad refactor or second GUI was added.
The previous 76 legacy retirements remain intact.

## Verification on the frozen source

| Check | Result | Scope |
|---|---|---|
| TypeScript | PASS | Full frontend typecheck |
| ESLint | PASS | Frontend source and DOM tests |
| Vitest | 825 PASS, 51 files, 0 failures | Complete synthetic frontend suite |
| Production build | PASS, 26 assets verified | Source/lockfile identity and shipped bytes |
| Affected Python | 249 PASS, 0 skips | Six synthetic API/lifecycle/delivery/build test files |
| Original audit diagnostics | 8 PASS, 0 failures | Previously 6 failed and 2 passed |
| Initial JS/CSS | 228,181 / 4,037 bytes gzip | Within the 350/80 KiB byte budgets |

Canonical frontend command:

```sh
npm run check --prefix src/frontend
```

Affected Python command, with a fresh disposable temporary directory:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest \
  tests/integration/test_frontend_vertical_contract.py \
  tests/integration/test_settings_comprehensive.py \
  tests/trust/test_ai_request_lifecycle.py \
  tests/test_launcher_lifecycle.py \
  tests/test_frontend_delivery.py \
  tests/test_frontend_build_identity.py \
  -q -ra --strict-markers --basetemp=/tmp/slm-continuity-UNIQUE
```

Execution environment: Linux, Python 3.12.14, Node 24.19.0. Python reported one
existing Starlette/AnyIO deprecation warning. No real provider calls were made.
The frozen changed-file hashes stayed unchanged during both canonical checks.

New behavior tests first produced 14 failures against the original implementation.
A later query-order scroll test also failed before canonicalizing its key.
Regression coverage includes late policy/source changes while hidden, explicit
cancellation, pending Q&A saves/suggestions, all confirmation portal surfaces,
real synthetic reauthentication with a revoked-resource 403, replacement-account
motion reads, malformed settings and direct-link return fallback.

Two old expectations intentionally changed to match the approved continuity
contract: hiding Tutor no longer discards a pending response, and a tab round-trip
retains an uncertain Q&A-save buffer until explicit readback. Both retain the
single-request/no-replay assertions. Genuine question reselection still waits
for verified detail. Shell read allowlists add only the own-account settings GET
needed to restore motion.

## Acceptance still open

The browser harness now defines measured 200%/400% tab zoom and separate 320 CSS px
reflow; its syntax was checked, but those browser cases were not executed.
DOM tests do not establish visual accessibility, keyboard/screen-reader behavior,
service-worker lifecycle, actual startup/interaction speed, long-course/list
scale, Windows package/install/launcher behavior, or provider teaching quality.
No fresh whole-source coverage result or 80% coverage claim is made. This scoped
review does not complete the remaining whole-codebase review passes.

Completed Tutor history still clears during a real authentication lock, as in
the base implementation; this change addresses tab continuity. Unsaved questions
and the Q&A editor remain temporary memory. Reloading/leaving the workspace does
not create permanent conversation recovery. Broader shared-engine consolidation
and scale measurements remain separate work.
