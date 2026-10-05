# Maintained browser acceptance

Updated 2026-10-05. Follow [current contracts](FUNCTIONAL_REQUIREMENTS.md),
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

The maintained fixture starts a disposable database/server on an ephemeral
loopback port. Its provider is explicitly a deterministic stub. Ordinary journeys
block service workers; `test_service_worker_update.py` enables the actual worker,
upgrades from the v14 fixture, waits for old clients to close, checks scoped offline
assets and verifies connection recovery. Neither suite certifies model quality.
Clear the environment overrides after the run. Each fixture stops only its own
subprocesses. Existing-server `tests/e2e` and interactive `tests/manual` are not
the isolated acceptance harness; do not aim them at user data.

For real inference start `tests/browser/local_provider_server.py --state-dir NEW
--port FREE_PORT`, with LM Studio listening only on 127.0.0.1:1234 and the chosen
model loaded as `slm-production-evaluation`. It creates a new synthetic directory,
accounts and encrypted recovery key, and records actual transport responses.
`tests/browser/evaluate_local_provider.py` executes the fixed rubric through
application HTTP; run development first and reserve the other split until prompts
are stable. Preserve every result. Never publish that installation or credentials.

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
| Publication | Review content and linked assessment definitions, then explicitly publish, then assign. Schema validity/source submission does not imply factual support or teacher review. Import creates a private draft and remaps IDs; never publishes or assigns. |
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

The worker caches basic pages/assets; API operations always require the local
backend. Offline assets are a reading shell, not offline writes, grading or AI.
Installation must fail if required precaching fails. An update waits for old
controlled tabs to close; close those task tabs and reopen to activate it.
Verify failed requests never display success; reconnect and reload to recover.
Cache lookups/cleanup must not consume or remove another application's caches.

Record source SHA/tree, browser/version, commands, synthetic fixture identity,
PASS/FAIL and unexecuted scope. Keep local screenshots/logs private or sanitize
them before publishing. A human teacher/learner pilot remains a separate gate.
