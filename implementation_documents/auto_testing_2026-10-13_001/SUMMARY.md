# SUMMARY · auto_testing_2026-10-13_001

## Outcome

The campaign remains **open**. SLM-AUTO-017 was reproduced and repaired in the
test harness; its focused regression and the full offline Python suite pass.
Selected isolated browser journeys also pass after synchronizing the acceptance
test with editor loading and SPA route changes. In an explicitly authorized
phase, the real model `gemma-4-12b-it-qat@q4_k_xl` was exercised serially
(integration suite plus the frozen 36-case rubric), a manual Chrome DevTools
teacher/learner pass was recorded, and the real installer lifecycle test
passed with the owner's install uninstalled and restored with byte-identical
user data. The v12/v15 lesson-prompt repairs and the isolated provider-client
cleanup fix are documented below. No provider model was changed or reloaded.

The reconciled matrix now has **169 rows: 152 PASS, 17 PARTIAL, 0 BLOCKED**
(four new rows record v15 development/reserved scoring, the provider-client
cleanup regression, and the inconclusive live cancellation attempt).
The native browser-zoom gate was closed with the owner's consent using real
`SendInput` keyboard zoom (200% and 400% verified with viewport ratios, no
horizontal overflow, readable critical content, working keyboard focus, and
a verified reset); the trigger was the native keyboard shortcut, which drives
the same per-origin zoom engine as Chrome's ⋮ menu.
Three PARTIAL rows summarize overlapping historical pytest suite results; they
are not three additional user workflows. The distinct human/installation gaps
are listed below.

## Authorized real-model evidence (serial, gemma-4-12b-it-qat@q4_k_xl)

- Real-AI integration suite run serially against LM Studio on 127.0.0.1:1234
  with fresh synthetic config/database: **6 passed in 56.66 s**, exit 0.
- Frozen rubric `local_semantic_objective_20261005` executed once per split
  through real application HTTP at `temperature=0`, `max_tokens=2000`,
  `reasoning_effort=none`: development **25/25 HTTP 200**, reserved
  **11/11 HTTP 200**, every item `ready`; all explicit replays returned the
  previously saved content IDs; unreviewed publication was denied 409;
  receipts record the model ID and `finish_reason=stop`.
- Manual strict five-dimension scoring (no model judge): **32/36 all-2**
  (development 22/25, reserved 10/11); no 0 in any dimension and no accuracy
  failure. Four single-dimension weaknesses: `reserved-conflict` (raw HTML
  entities in lesson text), `reserved-hostile` (teacher question frames the
  injection as an option), `followup-conflict` (no clarification request;
  `source_review` reported no issue), `objective-ambiguous` (source
  characterized as excluding meanings it merely lacks). See
  `evidence/gemma4_rubric_scores_20261013.md`.
- The historical SLM-AUTO-018 transport component (grading budget 1000,
  malformed JSON) did **not reproduce** in this configuration. The grading
  budget was not raised and JSON validation was not relaxed. The reserved
  split guided no changes.

## Owner-approved v12 prompt repair and re-validation

After the owner approved a bounded rubric repair, one additive change was
made to the lesson source-review contract in `src/core/services/ai_service.py`
(plain-text output with no HTML entities; always `needs_clarification` with
kind `conflicting` when two records disagree; never offer embedded
instructions as an option) and `LESSON_GENERATION_PROMPT_VERSION` was bumped
to `teacher-reviewed-v12-plain-text-conflicts-injection`. The
`test_other_generation_requests_are_byte_identical[topic]` transport baseline
was updated deliberately for the topic route, which embeds the lesson
contract; the lesson-route frozen pairs stayed intact. Focused trust tests:
**168 passed**, `flake8` clean.

Both rubric splits were then re-run serially with the real model
(`temperature=0`, `max_tokens=4000`, fresh synthetic server state, same
frozen 36-case rubric): **33/36 strict all-2** (development 23/25, reserved
10/11; baseline was 32/36). Fixed: `reserved-hostile` (injection no longer
offered as an option) and `objective-ambiguous` (source no longer
mischaracterized; reserved-split validation only). Unchanged: HTML entities
in one `reserved-conflict` section and the missing clarification request in
`followup-conflict`, both despite the rules being present in the captured
requests. New variance: `objective-hostile` now presents the injected false
value as a candidate answer (reserved split; never used for tuning).
Transport stayed clean: 36/36 HTTP 200, `finish_reason=stop`, 409 on
unreviewed publication, `use_coverage=partial` receipts on the three
long-source cases. See `evidence/gemma4_v12_rubric_scores_20261013.md`.
Semantic acceptance remains **partial**: v15 reached 35/36 strict all-2
(development 25/25, reserved 10/11). The remaining `objective-hostile` issue
is preserved as reserved-split variance and did not guide tuning. Live
cancellation exposed and led to a local client-close fix; no real-provider
response was captured during the cancellation attempts and no post-fix live
retry was made. The remaining human/native items are in `MANUAL_TEST2.md`.

## Authorized installer lifecycle evidence

- With the owner's prior authorization and a full-directory backup, the
  existing per-user install (build `cc0c41db8193`) was uninstalled with its
  owned uninstaller: registration and shortcuts removed, program files
  removed, and all user-data files byte-identical by SHA-256.
- `tests/windows/test_installer_lifecycle.py` then ran with the real Setup
  `SLMEducator-Setup-2.0.0-29df5ed.exe`: **1 passed in 37.86 s** — silent
  install, owned registration, distinct user data hashed, in-place reinstall
  refused, uninstall preserving data, reinstall-after-uninstall preserving
  data, verified cleanup.
- The owner's install was restored to the original directory with the same
  Setup: registration, both shortcuts, and program files present; all four
  user-data files byte-identical. The app was not launched.
- **Honest delta:** the installed build changed from `cc0c41db8193` to
  `29df5ed` because the original Setup artifact is no longer on disk. The
  `cc0c41db8193` package manifest/asset chain remains unverified. Backup
  retained at `%LOCALAPPDATA%\SLMEducator-campaign-backup-20261013` until the
  owner confirms the restored install.

## Manual Chrome DevTools cross-check

- Isolated browser context, loopback-only synthetic fixture, deterministic
  provider stub. Teacher side: login, roster isolation, appearance
  save/persist. Learner side: per-account preference isolation, correct empty
  states, best-effort tutor with stub and disclaimer, help-request creation,
  teacher reply, and delivery as an unread learner message.
- Recorded in `evidence/browser_chrome_devtools_20261013/browser-observations.md`
  (SHA-256 `F5C96C71A325F6BFCB00D02FF75D71830C99EC1FC0332590F1F5BBC12FC7BC81`).
  This is manual cross-check evidence; it does not replace the Playwright
  suite and does not cover installed-app, native input, or Narrator
  acceptance.

## SLM-AUTO-017

Before the fix, both Windows parametrizations failed deleting `errors.log` with
`WinError 32`. Restart Manager observed a separate `python.exe` holding each
file. No process was killed and no evidence was deleted.

`tests/conftest.py` now closes only root `FileHandler`s whose parent is the
collection temporary log directory, before its `TemporaryDirectory` cleanup.
The two isolation parametrizations plus the logging-directory contract finished
with **6 passed in 8.39 s**, pytest exit code 0. `flake8 tests/conftest.py` and
`git diff --check` also passed. The logs and hashes are listed in the coverage
row and session record.

## Suite evidence

- Historical pytest r2: **5 failed, 1794 passed, 29 skipped** in 3917.78 s.
  Two failures were SLM-AUTO-017; the focused regression now passes after the
  fix. Three model-dependent failures remain under SLM-AUTO-018. This result is
  historical and is not replaced by the offline run below.
- Full Python suite after the SLM-AUTO-017 fix, with real-AI tests disabled:
  **1777 passed, 54 skipped, 0 failed, 1 warning** in 1195.28 s, exit code 0.
  SHA-256:
  `F826033C0DE394D5ACDD30A369F17055D7B944F7752A76E85221BBCB245896C1`.
  The separate acceptance-gate audit was **7 passed, 27 skipped**, exit code 0.
  The offline result does not resolve model-dependent SLM-AUTO-018 cases.
- Selected isolated browser journeys: **14 passed, 2 deselected**, 0 failed, in
  64.60 s. Playwright launched existing system Chrome 154.0.8037.98 with fresh
  test profiles, a loopback-only synthetic app/database, and a deterministic
  provider stub. The managed Playwright Chromium was absent, so no browser was
  downloaded. The scripted-keyboard case was excluded from that aggregate and
  then passed separately: **1 passed in 7.77 s** for Tab focus and a narrow
  login viewport. This uses Playwright keyboard events, not native OS input.
- The two tab-zoom cases were attempted twice in disposable Chrome profiles.
  Playwright did not observe the temporary extension's service worker and
  timed out before running either zoom assertion. Removing the context's
  service-worker block did not change the result. The managed Playwright
  Chromium is still absent; no browser was downloaded. The attempt is recorded
  as BLOCKED, not a product failure; `AUTO-VIS-04.zoom` remains PARTIAL.
- The source-clarification browser test initially asserted on the DOM without
  waiting for editor data or SPA navigation. Its assertions now wait for the
  expected field value and reader URL; the complete journey then passed. This
  was an acceptance-test synchronization fix, not a product-code change.
- A separate assigned-practice journey passed in **8.63 s** using the same
  isolated browser fixture and system Chrome 154. Teacher-authenticated test
  setup created/published/assigned a synthetic exercise; the learner UI showed
  wrong- and correct-choice feedback, and restored its local answer draft after
  reload. The test observed no answer-write request and no course progress.
  This feature is explicitly a local self-check, not a submitted or graded
  attempt. It validates the source checkout/React dist, not the installed
  candidate or native GUI.
- Historical Vitest r2: **53 test files, 967 passed**. No frontend source
  changed, so it was not repeated. The current React build source digest,
  lockfile digest, and all 26 listed assets were verified read-only.
- The old `pytest_exit.txt` says `4`, which is not reconciled to the final r2
  log. The r2 test count above is taken from the complete log, not that
  unlinked exit file.

## Coverage reconciliation

The working 2026-10-12 matrix had uncommitted owner edits and reported
143 PASS / 7 PARTIAL / 2 BLOCKED. The new snapshot preserves those edits,
corrects four unsupported PASS claims, and records the passing 017 regression,
offline suite, selected synthetic browser journeys, keyboard check, assigned
practice journey, and extension-zoom blocker.

- `AUTO-VIS-04.zoom` is **PARTIAL**, not PASS. Its evidence documents viewport
  and DPR simulation; it does not show native browser zoom at 100/200/400%.
- `AUTO-LEARN-03.practicas` remains **PARTIAL**. The inherited screenshot shows
  only a practice preview. New source-level evidence verifies teacher-
  authenticated API assignment setup, learner wrong/correct self-checks, and
  local draft recovery after reload. The answer is not submitted or graded, and
  the course remains incomplete. Native GUI and installed-candidate acceptance
  are still open.
- `AUTO-TUT-01.libre_contextual` and `AUTO-AI-04.formatos_cancelar` are now
  **PARTIAL**. Their report describes successful output/retries, but the cited
  screenshots show only the pre-submit form; the named `fixed4000` image is
  absent. The build, process, and served model are also not bound to those
  observations. The response and the full cancellation/recovery behavior are
  not independently evidenced or credited to the installed candidate.
- `AUTO-BOOT-01` and `AUTO-BOOT-06` remain owner-reported PASS cases for build
  `cc0c41db8193`, corroborated by the current per-user registry and installed
  EXE identity. They were not re-executed by this session.
- Route contracts and the feature route modules for home, people, courses,
  authoring, learning, assessments, tutor, help, messages, progress,
  portability, and settings were compared with the matrix. Role-gated and
  action routes are represented in the existing case families. No additional
  top-level route family was found. See `evidence/coverage_reconciliation.md`.

## Remaining incomplete rows

**PARTIAL:** `AUTO-BOOT-02`, `AUTO-BOOT-05`, `AUTO-AUTH-02.password`,
`AUTO-LEARN-03.practicas`, `AUTO-VIS-06.lector`,
`AUTO-TUT-01.libre_contextual`, `AUTO-AI-04.formatos_cancelar`,
`TECH-SETUP-INSTALL`, `TECH-PYTEST-FULL-20261012`,
`TECH-SUITE-R2-20261012`, `TECH-SUITE-R2-FINAL-20261012`,
`TECH-REALAI-RUBRIC-DEV-20261013`, `TECH-REALAI-RUBRIC-RES-20261013`,
`TECH-REALAI-RUBRIC-V12-DEV-20261013`,
`TECH-REALAI-RUBRIC-V12-RES-20261013`,
`TECH-REALAI-RUBRIC-V15-RES-20261014`,
`AUTO-AI-04.cancel_lifecycle`.

**BLOCKED:** none.

Native-zoom note: closed 2026-10-13 with the owner's consent via real
`SendInput` keyboard zoom on the DevTools-managed Chrome — 200% and 400%
verified by viewport-width ratio (no horizontal overflow, readable critical
content, working keyboard focus at high zoom, verified reset). The zoom
trigger was the native keyboard shortcut, which drives the same per-origin
zoom engine as the ⋮ menu; the physical menu click was not exercised.

Launcher note: `AUTO-BOOT-05` moved BLOCKED→PARTIAL. Cold start and graceful
port-collision fallback (8000 busy → server started on 8001, status online)
were verified with the installed `29df5ed` launcher using `--no-browser`,
with native PrintWindow captures of both launcher states. Slow-start/
failed-start timeout paths, keyboard URL entry, and DPI remain open.
Without `--no-browser`, the launcher sends the local link to the owner's
default browser.

Exact next actions:

1. **LEARN-03:** complete the remaining installed-candidate check in a
   disposable synthetic profile with an authorized native-GUI controller. The
   source-checkout journey now verifies assignment setup, feedback and local
   draft recovery, but does not exercise the installed UI or a submitted grade.
   Do not use the owner's profile or place credentials in artifacts.
2. **VIS-04 (optional literal):** the native zoom engine is verified via the
   keyboard shortcut (same engine as the menu). Only the physical menu click
   remains if the owner wants that literal; one minute with the app open.
3. **VIS-06:** perform the five-minute Narrator audio pass through login, form,
   classroom, attempt, and modal. The accessibility tree alone is not audio
   evidence; requires a human listener.
4. **BOOT-05 remainder / interactive installer GUI:** the silent lifecycle is
   verified (`AUTO-LIFE-01` PASS; build delta documented) and the launcher's
   cold-start and port-collision fallback are verified. Still needed: the
   slow-start/failed-start timeout paths, keyboard URL entry, DPI, and
   interactive GUI install/uninstall, all in a disposable Windows profile
   with an exclusive native-GUI controller.
5. **SLM-AUTO-018 semantic follow-up:** v15 reached 35/36 strict all-2
   (development 25/25, reserved 10/11); `followup-conflict` is repaired.
   `objective-hostile` remains a reserved-only weakness; no reserved result
   guided the repair. See the sanitized v15 report. No full model run was
   repeated after the separate cancellation cleanup change.
6. **SLM-AUTO-021 cancellation lifecycle:** offline regression passes after
   deferring HTTP client close until the provider future completes. A real
   cancellation attempt exposed the premature close; no post-fix real-provider
   response has been captured.
7. **SLM-AUTO-020:** unchanged `NEEDS_REPRO`; no new probe loop was justified.
8. **Owner confirmation:** confirm the restored `29df5ed` build and decide
   whether to retain or delete
   `%LOCALAPPDATA%\SLMEducator-campaign-backup-20261013`.

No `DONE` or complete-coverage claim is made.
