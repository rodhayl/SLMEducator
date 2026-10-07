# Native launcher redesign: implementation report

Date: 2026-10-07. Scope: `src/starter.py`, `src/startup_utils.py`,
`src/starter_headless.py`, and focused launcher tests. This report is source and
synthetic-test evidence, not native Windows or packaged-binary acceptance.

## Delivered

- Replaced the fixed 500×400 control window with a resizable native Tk/ttk view.
  Uses the approved AAC-derived cream, green and teal palette, system-family
  point-sized typography, wrapping status text and a prominent Open SLMEducator
  action. Recent activity is secondary, collapsible and bounded to 80 entries.
- ES/EN labels, status details, confirmations, clipboard/browser failures and
  console text share the launcher's maintained catalog. OS locale selects the
  initial language; the visible selector updates the view and previous activity.
  No installation settings or account preferences are written.
- A readonly, keyboard-focusable address field supports selection and copying.
  Ctrl+L selects it, Enter/Ctrl+O opens when ready, Ctrl+Q closes, and ordinary
  Tab/Space activation remains available. An unchanged poll does not reset the
  address text or keyboard selection.
- All launch paths use direct loopback HTTP `/api/status`, requiring HTTP 200,
  JSON media type and `{status: online, version: 2.0.0}`, with a live owned child
  checked before and after the response. No TCP-only readiness remains.
- Probes bound response size to 4096 bytes. Connect has a 0.4-second timeout and
  an absolute 0.4-second transport timer interrupts slowly trickling response
  headers/body. Redirects and proxy settings are not used. Connections and
  response handles are closed on every path. GUI probes run outside Tk; only the
  GUI thread applies results, and stale generations after Stop/restart are ignored.
- Starting becomes slow after 10 seconds and a visible startup error after 30.
  Ready requires a valid status response. Loss of health disables Open and can
  recover; startup timeout requires Stop before retry if the child remains alive.
  Process exit is a visible error, including a secondary exit-code diagnostic.
- Browser opening is single-flight, handles both false returns and exceptions,
  and offers a copyable URL on failure. A queued open rechecks generation and
  readiness before launching. `--no-browser` suppresses automatic opening in
  GUI and console modes; headless always suppresses it.
- Stop and X explain the browser-work impact before acting. They operate only on
  the `multiprocessing.Process` created by this window. Termination is followed
  by nonblocking polling; after four seconds, only that child can receive kill,
  followed by two seconds of verification. Only confirmed exit reports Stopped.
  A shutdown failure keeps the window open, with a retryable Stop action. Joins
  in the GUI lifecycle use timeout zero.
- Console fallback and headless share the lifecycle helpers. Headless retains
  fixed port 8000 and rejects an already occupied port before spawning; the GUI
  and ordinary console retain the existing port search starting at 8000.
- Preserved frozen path/bootstrap setup, `freeze_support`, recovery dispatch,
  installation state and existing API contract. No new dependencies, modules in
  the packaging allowlist, provider calls, installer edits, PID scans, foreign
  process termination, host changes or security-policy changes.

## Verification

Prepared Python: the existing `slm-best-effort-6109-20261006/.venv` (Python 3.12).
All test databases were disposable synthetic fixtures.

- Launcher + package/bootstrap gate: **162 passed** in 79.80 seconds.
  Command: `SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest
  tests/test_launcher_lifecycle.py tests/test_build_package.py
  tests/test_seed_admin.py -q` (with isolated basetemp and coverage output).
- That checkpoint measured **87% combined line coverage** for the three launcher
  modules: starter 81%, startup utilities 100%, headless 100%. This is focused
  coverage, not the whole-repository coverage gate. The untouched frozen module
  reconstruction and actual server entry are the main uncovered paths.
- Final follow-up adds response-handle cleanup and checks against a browser
  launch queued before Stop / a console child exiting after a status response.
  Final focused launcher gate: **87 passed** in 15.03 seconds.
- Focused flake8, mypy (`--follow-imports=skip` for the three launcher modules),
  and compileall **pass on the final edits**.
- Tests cover wrong HTML/JSON/status/version/content-type, redirects, errors,
  oversized/deeply nested responses, response deadlines, dead/stale children,
  slow/timeout, health loss/recovery, duplicate starts/opens, confirmation cancel,
  successful/failed terminate and kill, retry, close-after-exit, occupied ports,
  browser/clipboard failures, URL keyboard wiring, unchanged-selection behavior,
  language/key/placeholder parity, bounded diagnostics and console/headless/recovery
  dispatch. Declared normal-text color pairs measure at least 4.5:1 contrast.

## Acceptance boundaries and remaining native work

No native display or Xvfb was available in this executor. Mocked widget wiring
and state-machine tests do not establish actual appearance, focus visibility,
screen-reader output, Windows 200% DPI, browser launching or a frozen executable.
The declared token contrast check does not certify every OS-rendered state.

The existing status endpoint does **not** expose process identity or frontend
build health. Readiness therefore checks its current contract at the chosen
loopback origin plus the owned child's liveness. Port bind preflight is not an
atomic reservation; no claim is made of authenticated server ownership or
frontend/native acceptance. No API identity token or additional endpoint was
introduced in this task.

Before distribution, validate the final identified Windows artifact with
synthetic data: normal/slow/failed startup, a conflicting port, no browser,
browser failure, keyboard URL selection/copy/open, ES/EN, resizing and 200% DPI,
double start/open, Stop/Cancel/X, process exit and restart, first login/change
password/restart, recovery, and the existing installer lifecycle gates.
