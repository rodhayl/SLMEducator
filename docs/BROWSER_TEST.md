# Maintained browser acceptance

Updated 2026-10-07. Follow [current contracts](FUNCTIONAL_REQUIREMENTS.md),
not the former 2025 registration/publication examples. Scope: one local process,
loopback, synthetic adult accounts. Browser automation is separate from native
Tk acceptance, real inference and the human pilot.

## Safe setup and reproducible automation

Use a fresh synthetic installation, administrator, two teachers and two learners.
Never connect these tests to a user's installation. Teachers create/enroll their
own learners; unauthenticated self-registration or role selection is not allowed.
`scripts/seed_admin.py` is create-only; save its generated credential privately.
Restart must preserve an existing administrator's password and disabled state.

Prepare the project's development environment, then in PowerShell:

```powershell
$env:SLM_OFFLINE_TESTS = '0'
$env:SLM_BROWSER_ACCEPTANCE = '1'
$env:SLM_BROWSER_EXECUTABLE = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:SLM_BROWSER_ARTIFACTS = "$PWD/temp/browser"
venv/Scripts/python.exe -m pytest tests/browser -q
```

Build and verify the React frontend first with `npm run check` in `src/frontend`.
The maintained fixture starts a disposable database/server on an ephemeral
loopback port, explicitly selects the repository's verified React dist, writes
synthetic configuration and refuses an existing synthetic database. Its provider
is a deterministic stub with outgoing provider transports disabled. Every browser
context/profile is new. Ordinary journeys block service workers and use the
current React accessible names, roles and routes; they do not invoke removed
page-global handlers. The isolated smoke test covers startup, signed-in navigation,
role menus and application status. Public self-registration is not a test setup
path. Never run obsolete existing-port E2E scripts against port 8080 or user data.

`test_service_worker_update.py` separately allows workers and uses a frozen,
SHA-256-checked copy of the actual prior v22 worker at the exact `/sw.js` URL.
Only that opt-in server mode supplies inert synthetic old precache dependencies;
it never loads a removed GUI tree. A private fixture marker switches `/sw.js` to
the production `RETIREMENT_WORKER`. Loading the React entry requests the update.
The test keeps an actual dirty React generation form open, checks that retirement
waits and neither reloads the document nor changes its controller, closes the
other controlled tab, and confirms the last dirty tab still blocks activation.
After that last tab closes, normal activation removes exactly these caches:

- `slm-educator-v22-session-locale`
- `slm-educator-v22-session-locale-auth-validation`

It verifies unregistration, retained unknown/foreign caches with their contents,
and retained owner and foreign browser drafts. A separate fresh profile must
register no worker and create no cache. There is no forced activation, client
claim, reload message or test `skipWaiting` shortcut. The previous offline-legacy-
asset journey is intentionally retired; it is not a requirement for React.

Neither suite certifies model quality. Clear the environment overrides after the
run. Each fixture stops only its own subprocesses. Interactive `tests/manual`
remain a separate manual boundary.

For real inference start `tests/browser/local_provider_server.py --state-dir NEW
--port FREE_PORT`, with LM Studio listening only on 127.0.0.1:1234 and the chosen
model loaded as `slm-production-evaluation`. It creates a new synthetic directory,
accounts and encrypted recovery key, and records actual transport responses.
`tests/browser/evaluate_local_provider.py` executes the fixed rubric through
application HTTP; run development first and reserve the other split until prompts
are stable. Preserve every result. Never publish that installation or credentials.

For the final 2026-10-05 evaluation use
`--cases-file tests/fixtures/local_semantic_objective_20261005.json --max-tokens 4000 --reasoning-effort none`.
The 25 previous cases are development regressions; 11 new sources were reserved
before v8 inference. The earlier follow-up fixture/results remain historical
evidence, including the erroneous half definition already present in its source.
Native LM Studio uses the pinned model/configuration in the production
readiness report. For `run_tests.bat --real-ai --yes`, use an isolated config with
temperature 0/max 4000 and `SLM_REAL_AI_REASONING_EFFORT=none`; the fixture verifies
the actual service parameters. Other providers/configurations are separate scope.

## Manual GUI and direct API checks

Use Chrome DevTools with `--isolated` and an independent free profile/context.
A busy profile calls for another profile; never close the user's browser. Limit
individual waits, capture failure evidence and retry deliberately. Do not kill
unrelated processes. A disabled account or expired/revoked session must fail both
navigation and direct API writes.

| Role / journey | Checks |
| --- | --- |
| Administrator | Bootstrap, change password/restart, recover another synthetic account, activate/deactivate, enrollment and withdrawal; protect last active admin. |
| Teacher A/B | Roster isolation; direct foreign content, course, source, assessment, submission and export IDs must deny access. |
| Sources | TXT/Markdown/PDF, empty and unreadable PDF, oversized input, hostile text; visible extraction coverage/hash, saved source revision and exact generation fragment. |
| Authoring | Create/edit ordered lessons, objectives and vocabulary; replace source and invalidate review; assigned copies remain immutable; revise into a new draft. |
| Generation | Topic, Exercise and Full Package panels reachable by normal navigation; retain entered text when switching; double click/repetition reuses saved IDs; partial failure preserves good work, retry only failed items. |
| Publication | Review content and linked assessment definitions; explicitly publish the linked assessment first, then review/publish the course and assign. Schema validity/source submission does not imply factual support or teacher review. Import creates a private draft and remaps IDs; never publishes or assigns. |
| Learner A/B | Assigned course order/objectives, practice, progressive hints, pause/previous/resume and restart history; cannot retrieve another learner's notes/grades or teacher grading assets. |
| Assessment | Pending subjective grade remains pending after reload; teacher can record an actual zero and feedback, revise it and reload; automatic objective scoring must match validated keys. Read feedback without creating a new attempt. |
| Assistance | Strictest open-attempt policy; first hints do not reveal answers; missing/conflicting sources are explicit; cancellation/timeout/busy are never successful answers or final grades. |
| Portability | Preview teacher package and learner handout; handouts omit keys/rubrics/raw source; clean import preserves relationships as draft; encrypted backup is a separate operator flow requiring the separately held key. |

Assessments are saved as drafts before explicit publication. A button label or
hidden navigation item is not authorization evidence: also call the write API
with insufficient roles, foreign IDs, stale sessions and disabled users.

## GUI, accessibility and cache

Check ES/EN, actual light/dark styles, keyboard order and visible focus, field
labels, native browser 100%/200% zoom (measure it; CSS scaling is not zoom), 390px
and desktop sizes, empty/loading/error states, unsaved work after interruptions,
back navigation and repeated operations. Use existing shared rendering and CSS.

Fresh React installations do not register a service worker and do not provide
an offline application shell. The temporary `/sw.js` endpoint only retires the
two recognized old caches after old controlled tabs close. Save work before
closing those tabs; no automatic reload or broad cache/draft deletion is allowed.
API operations and AI still require the local backend. Verify failed requests
never display success; reconnect and reload to recover. Unknown caches, other
applications' storage and browser recovery drafts must remain unchanged.

Record source SHA/tree, browser/version, commands, synthetic fixture identity,
PASS/FAIL and unexecuted scope. Keep local screenshots/logs private or sanitize
them before publishing. A human teacher/learner pilot remains a separate gate.

## Verification levels and known execution boundary

`tests/browser/test_harness_contracts.py` is an offline harness check, not a
browser test result. It checks the frozen v22 fixture, the exact production
retirement response, and the native login helper's 307 → `/entrar` → integrity-
tagged React asset contract using in-process synthetic HTTP responses.
`tests/windows/exercise_native_login.py` checks that redirect/delivery contract
before packaged synthetic admin login, password rotation and old-session
revocation. Running its mocked helper tests on Linux does not certify a Windows
executable or painted UI.

On 2026-10-07 the available execution environment blocked real Chromium launch
with an AF_UNIX sandbox denial; the supported cloud browser's loopback request
also returned `net::ERR_BLOCKED_BY_CLIENT`. Do not add insecure launch flags or
alternate hosts to evade either restriction. Syntax, pytest collection and
in-process checks can be reported separately. All live React journeys, real
worker lifecycle, true 200% tab zoom, screenshots and native Windows startup
remain NOTRUN/BLOCKED here until performed in a supported prepared environment.
A collection or skip count is never a browser PASS.
