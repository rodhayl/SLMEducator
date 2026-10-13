# Run · auto_testing_2026-10-13_001

**State:** continuation open; not an acceptance sign-off.  
**Date:** 2026-10-13, Europe/Madrid.  
**Scope:** recover the current checkout and evidence, reproduce/fix SLM-AUTO-017,
run the complete offline Python suite and selected isolated browser journeys,
reconcile inherited claims, and preserve the remaining interventions.

## Candidate and workspace

- Repository: `SLMEducator`, branch
  `fix/react-functional-continuation-20261007`.
- `HEAD` and the configured upstream ref:
  `cc0c41db81933fbd23b904086641ee9e05bf50a5`.
- Committed tree: `7fb5c380537c23993e64c1c9de495c49dc855782`.
- Product candidate installed by the owner: originally build `cc0c41db8193`
  (version `2.0.0`); after the authorized 2026-10-13 lifecycle exercise the
  installed build is `29df5ed`, restored to the original directory with
  byte-identical user data (see `evidence/installer_lifecycle_20261013.md`).
- This continuation changed only test teardown in `tests/conftest.py`, waits in
  `tests/browser/test_source_clarification_journey.py`, added
  `tests/browser/test_assigned_practice_journey.py`, and campaign
  documentation. No product source, installer, runtime configuration,
  database, or user account was changed.
- The existing modified `auto_testing_2026-10-12_001/COVERAGE.csv`, untracked
  worktrees, `.atl/`, and frontend output files were preserved. The new
  `COVERAGE.csv` is a reconciled snapshot, not a rewrite of that history.

## Runtime and provider boundary

- During the authorized phase the owner's install was uninstalled (owned
  uninstaller), used for nothing else, and restored; the app itself was never
  launched by this continuation.
- Uvicorn on port 8099 belongs to the separate AAC_ASSISTANT checkout; it was
  left untouched.
- LM Studio on port 1234 served `gemma-4-12b-it-qat@q4_k_xl` for the
  explicitly authorized serial runs (integration suite and both frozen rubric
  splits, `temperature=0`, `max_tokens=2000`, `reasoning_effort=none`). No
  model was downloaded, reloaded, or reconfigured; no parallel inference was
  sent.
- The installed launcher (29df5ed) was booted twice with `--no-browser` for
  the authorized BOOT-05 gates: cold start and graceful port-collision
  fallback (8000 busy → server on 8001, status online) both verified; test
  instances were force-stopped afterwards with byte-identical user data. Two
  earlier launcher exits were environmental (process dies with the parent
  shell that launched it), not product failures.
- The full Python suite passed offline with 1777 passed, 54 skipped, and no
  failures. Selected synthetic browser journeys passed in headless system Chrome
  154. Neither result is installed-app or native-GUI acceptance.

## Package boundary

The `cc0c41db8193` Setup/output directory was not found under `C:\builds`; its
package manifest and bundled asset hashes remain unvalidated. The silent
install/uninstall/reinstall lifecycle was verified end to end with the real
`29df5ed` Setup (automated lifecycle test passed; owner install restored with
byte-identical user data). Interactive GUI install and build-to-build update
paths remain unexercised.

## Evidence index

- `COVERAGE.csv`: 152 carried rows, one regression row, and five execution rows.
- `evidence/pytest_017_baseline.stdout.log`: isolated failure reproduction.
- `evidence/pytest_017_baseline.stderr.log`: empty stderr from that run.
- `evidence/pytest_017_regression.log`: post-fix regression output, 6 passed.
- `evidence/pytest_full_offline_after_017.log` and `.exit.txt`: complete offline
  Python suite, 1777 passed / 54 skipped / 0 failed.
- `evidence/pytest_acceptance_gates_skipped.log` and `.exit.txt`: explicit
  acceptance-gate audit, 7 passed / 27 skipped.
- `evidence/browser_automated_synthetic_chrome154_final.log` and `.exit.txt`:
  selected isolated browser journeys, 14 passed / 2 deselected.
- `evidence/browser_automated_synthetic_chrome154_final/`: synthetic screenshots
  from the selected journeys.
- `evidence/browser_automated_synthetic.log` and `.exit.txt`: initial missing
  Playwright Chromium attempt, retained as setup-blocker evidence.
- `evidence/browser_source_clarification_routewait_chrome154.log`: corrected
  full source-clarification journey, 1 passed.
- `evidence/browser_keyboard_narrow_chrome154.log` and `.exit.txt`: isolated
  keyboard-event and 390px login check, 1 passed.
- `evidence/browser_keyboard_narrow_chrome154/login-narrow-keyboard.png`:
  synthetic narrow-login screenshot.
- `evidence/browser_assigned_practice_chrome154.log` and `.exit.txt`: assigned
  practice journey, 1 passed; wrong/correct self-check feedback and local draft
  restoration after reload.
- `evidence/browser_assigned_practice_chrome154/assigned-practice-restored-feedback.png`:
  synthetic learner view after draft recovery. This is not an installed-app or
  graded-attempt artifact.
- `evidence/browser_native_zoom_system_chrome154.log` and
  `evidence/browser_native_zoom_system_chrome154_retry.log`: two attempts at
  actual tab zoom; both blocked before zoom assertions on extension-worker
  startup. Their exit files record code 1.
- `evidence/pytest_real_ai_gemma4_serial.log` and `.exit.txt`: serial real-AI
  integration suite, 6 passed.
- `evidence/real_ai_gemma4_development.log`, `_results.json`,
  `_inference.jsonl`, `_server.log`: frozen development split through real
  HTTP; 25/25 HTTP 200 with receipts.
- `evidence/real_ai_gemma4_reserved.log`, `_results.json`,
  `_inference.jsonl`, `_server.log`: frozen reserved split; 11/11 HTTP 200
  with receipts; not used for tuning.
- `evidence/gemma4_rubric_scores_20261013.md`: manual strict five-dimension
  scores for all 36 cases (32/36 all-2) with per-weakness rationale.
- `evidence/gemma4_rubric_digest.txt`: readable per-case output digest used
  for scoring.
- `evidence/browser_chrome_devtools_20261013/browser-observations.md`:
  manual DevTools teacher/learner cross-check observations and boundaries.
- `evidence/installer_lifecycle_20261013.md`: authorized uninstall/lifecycle
  test/restore sequence with pre/post hashes and the build delta.
- `evidence/pytest_installer_lifecycle_gemma4_run.log`: lifecycle test
  output, 1 passed in 37.86 s.
- `evidence/launcher-ready-state-20261013.png` and
  `evidence/launcher-port-fallback-8001-20261013.png`: native PrintWindow
  captures of the installed launcher's ready state on 8000 and of the
  graceful fallback state on 8001 during the port-collision test.
- `evidence/installation_identity.md`: original installed identity and
  package limits.
- `evidence/coverage_reconciliation.md`: route/role and evidence reconciliation.
- `SUMMARY.md`, `SESSION_LOG.md`, `RESUME.json`, `DEFECTS.md`: continuation
  outcome, chronology, resumption state, and defect pointer.
