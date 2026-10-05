# Assessment and feedback browser acceptance — 2026-10-05

## Source and scope

Based on `5e867df0b090e8ae6cebf46552df560e9e3fbb90` from
`feat/local-acceptance-recovery-20261004` (runtime parent `a2cfa065`).
Work is isolated on `feat/assessment-browser-acceptance-20261005`.
No main update, merge, deployment, real learner data or real provider calls.

The new Chromium journey uses the existing fresh database/server fixture and
teacher_a, teacher_b, learner_a and learner_b. The fixture adds a nonempty
synthetic 10-point rubric before publishing its existing manual assessment.

The learner follows dashboard links, answers, reviews, returns to editing and
submits. The receipt and history stay pending with no fabricated final zero.
Only the first exact grade POST is intercepted with 503. The visible error,
score/feedback inputs and complete server submission snapshot are checked.
One explicit real retry publishes 0/10. Real history links, reload and Back/
Forward preserve feedback without reserving another attempt. The learner gets
neither private answer keys nor the nonempty rubric. Foreign teacher/learner
deep links and grade writes receive real server 403 responses; the published
submission and assessment definition remain unchanged.

## Reproduced defects and repairs

The initial focused journey passed, but screenshot review exposed two real
style defects, each reproduced with a failing Chromium assertion:
- The selected grading detail still showed the empty placeholder. A later
  display utility overrode the hidden class. Hidden flex/grid combinations now
  have sufficient specificity; the actual grading flex case is checked.
- Hovering the selected history row painted a light background beneath white
  text. Generic hover styling now excludes active rows; actual computed
  background color is checked after hover.

The first seven-case consolidation was **6 passed, 1 failed**: the existing
teacher-preferences test observed “Grade (Optional)” instead of “Grade Level”.
An imperative profile-loading overwrite raced with localization. Removing that
overwrite preserves the existing translation markup and test contract.
Dashboard asset versions and the service-worker cache were advanced together.

No assertion was weakened to hide these failures. Failed local logs are retained
outside Git; only code, tests and this sanitized report are published.

## Verified local results

- Final exact-byte real Chromium consolidation: **7/7 passed**, 26.55 seconds.
- Serial DOM regressions: **160/160 passed**, 10.24 seconds.
- Focused scoring/session API suite: **45/45 passed**, 9.46 seconds
  (one existing Starlette deprecation warning).
- Focused style/frontend-safety checks: **18/18 passed**, 1.63 seconds,
  including vendored asset hashes.
- New-test compilation, critical Python lint, focused typing, formatting,
  dependency consistency and opt-in collection/skip behavior passed.
- Three new synthetic screenshots were visually reviewed: pending submission,
  visible failed-save/retry state, and published zero-score learner feedback.

Local browser evidence uses Python Playwright 1.56 and official Chromium 1194,
compatible with the repository's pytest-playwright 0.7.2 requirement
(`playwright>=1.18`). No dependency file was changed. The first system-Chromium
launch failed at profile socket creation; the default Playwright 1.63 browser
download then returned corrupt archives. Neither is reported as a product
failure or browser pass. The supported compatible toolchain ran without altered
security flags or OS permission changes.

Source materialization initially added trailing newlines and normalized one
vendored license's CRLF bytes. Those local-copy mismatches were restored against
the Git blobs; the final vendor-hash gate passed. No vendored bytes are changed.

## CI and remaining limits

Only the exact new branch was added to the existing browser workflow trigger.
The offline workflow remains unchanged and runs on every push. Automatic CI for
the published SHA must be read back separately; local focused checks are not a
claim that the entire backend/coverage gate ran locally. No exploratory CI
pushes or reruns were used.

This is source-run synthetic acceptance. Native Windows packaging/restoration,
real-provider educational quality, native zoom/accessibility and an authorized
human pilot remain separate gates. Browser fixtures disable service workers,
so cache versioning was reviewed in source rather than presented as a browser
upgrade test.
