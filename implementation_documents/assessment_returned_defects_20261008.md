# Assessment returned-defect repair (2026-10-08)

Source: returned report at `implementation_documents/auto_testing_2026-10-08_001/DEFECTS.md`, GitHub report tree `16a2dd9ba84fbaf103aff056fee8b07372c5102e`. This work covers SLM-AUTO-008, 009 and 010 only. It uses synthetic data and offline provider-free tests.

## Reproduced before changes

- Six added API regression cases failed: stored linkage omitted from detail, PUT linkage ignored (including edits that should have been blocked), and missing typed notices for closed, timed-out and unknown-time attempts.
- Six added DOM cases failed: missing saved linkage controls/preview values, missing rubric grading controls in EN/ES, and missing separated localized lifecycle notices in EN/ES.
- Three subsequent per-answer regression cases failed for the same fixed-English-message pattern on unanswered work, unavailable answer keys and unavailable automatic grading.

## Repairs and contracts

### SLM-AUTO-008: usable rubric grading

The corrections page now passes its already-authorized assessment definition to the grading workspace. A subjective question uses its own rubric(s), falling back only to the assessment-wide rubric. It never borrows another question's rubric. Multiple question-specific rubrics can be selected explicitly.

The scoring aid shows criterion names, descriptions, maxima and integer inputs. Zero is valid; empty, fractional, negative and excessive values are not. The visible calculation converts the earned rubric proportion to the question's maximum and rounds to the nearest whole point. This handles rubric/question totals that differ without silently assuming they match.

Applying a rubric fills a local grade draft and adds a readable criterion breakdown to feedback, preserving existing teacher text. It performs no mutation. Re-applying replaces only the exact previously inserted breakdown from this mounted helper. The teacher then uses the existing save boundary and last-question/final-total confirmation. Unapplied criterion inputs participate in dirty navigation protection and block grade saves until applied or explicitly cleared. AI suggestions remain provisional.

Persistence uses existing question score and feedback fields. The saved breakdown is available to teacher and learner after reopening. Criterion input controls start fresh on reopen, as the UI explains; this is a grading aid with a saved readable breakdown, not a new structured criterion-score storage model. Manual scores and comments remain editable. No database migration was added.

### SLM-AUTO-009: visible, editable linkage

`GET /api/assessments/{id}` includes `study_plan_id` and `topic_id`. The author preview displays them and the reopened editor retains both controls. A draft save includes null for a cleared link; omission in an API update preserves the old value. Copies remain standalone until linked explicitly.

`PUT /api/assessments/{id}` validates replacement course/content permissions using the same policies as creation. Link edits join the existing immutable-definition boundary: rejected after any attempt, and rejected for an assigned published assessment even before its first attempt. Validation occurs before link assignment. A permitted edit returns the definition to draft for review/publication. Read-only IDs remain visible when attempts prevent editing.

### SLM-AUTO-010: system messages separated from feedback

Submission detail adds `system_notices`, containing translation keys derived from durable timing/status rather than from the teacher feedback field. New closed/late/unknown-time attempts no longer write English lifecycle text into feedback. Notices remain visible after a teacher writes a grade or comment; they do not alter scores, answers, consumed attempts, timestamps or provisional grading.

Both result reading and corrections render notices in a separate localized system-notice section. Fixed automatic question messages also use typed localized notices at the API presentation boundary; an unavailable AI suggestion is no longer silently hidden solely because its score is absent. Explicitly reviewed question feedback stays unchanged.

Compatibility for old attempt rows is deliberately narrow and read-only. Exact old fixed wording is treated as a system notice only when the stored attempt facts agree and no teacher approval has been recorded. After teacher approval, identical wording could be either an old system string or an explicit teacher comment, so it stays visible verbatim with a localized explanation that historical authorship cannot be determined. Arbitrary, extended or nonmatching feedback is never translated or erased. No historical database rows are rewritten.

## Validation

Focused tests and final counts are recorded by the task coordinator. Baseline and successive local gates included:

- `tests/trust/test_assessment_returned_ux.py` and existing assessment revision, authoring fidelity, review, trustworthy scoring/session and AI-settings/grading suites
- `tests/frontend/assessments-workflows.test.tsx`, `assessments-contracts.test.ts`, `assessment-timezone.test.tsx`, `assessment-navigation-continuation.test.tsx`
- Frontend TypeScript and focused assessment ESLint
- Python critical syntax/name checks for the changed API and test module

Final focused results: 141 Python tests passed across the six listed assessment/API suites; 131 DOM/contract tests passed across four listed frontend files. The newest per-answer review guard was separately rechecked with all 12 returned-defect API tests passing. Frontend TypeScript, focused assessment ESLint, and Python critical syntax/name checks passed. Python emitted the existing Starlette/AnyIO deprecation warning. The coordinator's combined repository gate remains separate.

## Remaining acceptance boundaries

No real provider request, model quality claim, native Windows execution, packaged application verification, production database migration or GUI/browser acceptance run was performed. The implementation is validated by deterministic API and synthetic DOM tests. Final frontend asset build and combined repository checks belong to integration after all domain edits are complete.
