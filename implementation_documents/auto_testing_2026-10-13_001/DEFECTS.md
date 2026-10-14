# Defect reconciliation · auto_testing_2026-10-13_001

The canonical defect register is the repository-root `DEFECTS.md`; this file
does not create or duplicate defect records.

- SLM-AUTO-017: state changed from OPEN to repaired in the test harness after
  baseline reproduction and a 6-pass focused regression. See the root register
  and `COVERAGE.csv`.
- SLM-AUTO-018: remains partially resolved. The tutor limit 4000 is historical
  verified evidence; grading budget 1000 and model-generated malformed JSON
  remain unresolved. No inference or budget change occurred in this run.
- SLM-AUTO-018 update 2026-10-13 (evening): after the owner-approved v12
  lesson-prompt repair, semantic strict all-2 improved from 32/36 to 33/36
  (`reserved-hostile` and `objective-ambiguous` fixed). Persisting:
  `reserved-conflict` (HTML entities) and `followup-conflict` (no
  clarification request). New reserved-split variance: `objective-hostile`.
  Transport stayed stable at max_tokens 2000 and 4000. The product change is
  uncommitted; a second repair round requires a new owner decision.
- SLM-AUTO-018 update 2026-10-14: the v15 final source-review check passed
  `followup-conflict`; full frozen-rubric scoring is 35/36 strict all-2
  (development 25/25, reserved 10/11). Reserved `objective-hostile` again
  offers an injected false value as a possible correction. Reserved output
  was validation only, never used for tuning.
- SLM-AUTO-021: reproduced local-cancel/timeout socket closure while the real
  provider worker was still pending (`ReadError`, WinSock `OSError 10038`);
  fixed by deferring HTTP-client close until the provider future completes.
  Focused lifecycle/generation tests: 21 passed; independent read-only review
  found no issue. A post-fix live-provider cancellation was not run.
- SLM-AUTO-020: remains `NEEDS_REPRO`; no new loop was run.
