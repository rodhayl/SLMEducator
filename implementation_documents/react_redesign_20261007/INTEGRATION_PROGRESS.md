# React migration integration progress

This is a source-level checkpoint, not final acceptance or any of the three requested final whole-codebase audits.

## Parent integration fixes

- Disabled query observers have a distinct inert key. They cannot replace an active shared query function or read cached private data through a null/disabled observer. Two red cases were reproduced before the fix.
- Tutor, assistance and progress domains are registered in the common feature graph; enrolled-student detail can open the existing authorized messaging composer. Learning completion and grading invalidate progress through the shared query boundary.
- Missing teacher identity now returns no enrolled students before querying. SQL NULL must not accidentally select unclaimed learners.
- Assessed mastery ignores missing assessments/students and nonpositive denominators before producing records. Nullable ORM scores are explicitly narrowed; a genuine zero remains an assessed zero. Eight existing mypy errors in policies/assessed_review are resolved, without disabling typing checks.
- Synthetic offline workflow uses the React lockfile and complete frontend check/build instead of the retired CJS entry point. No hosted workflow was executed.
- Auth page integration checks verified React output, legacy 307 bridges and retired-asset 404s; invalid login still runs against a disposable synthetic database.

## Scoped evidence

- The prior integrated frontend check passed 596 cases across 40 files plus TypeScript, ESLint and build. Later migration edits require a fresh final run; this count is not current final acceptance.
- Missing-identity tests initially failed 3/3. After corrections, the selected mastery/product suites passed 18 cases. A later offline subset including auth delivery, transport guards and mastery passed 12 cases. These scopes overlap and must not be summed.
- Mypy passed the two affected source files; focused Ruff passed changed parent source/test files after preserving reusable pytest fixture exports.
- Other domain, packaging, browser-harness and draft-migration reports retain their own scopes. Native browser, Windows and real-model checks are not implied by these results.

Legacy deletion remains gated by replacement assertions and maintained harness/documentation migration. Final codebase review count: 0/3.

## Retirement checkpoint

After replacing the missing migration assertions and browser/native harness contracts, 71 exact legacy files were retired: 46 old GUI/vendor files, 22 old UI-test/tooling files, and three unsafe existing-server E2E harness files. LEGACY_RETIREMENT.json records original byte/blob hashes and replacement coverage. No new GUI route retains an implementation-placeholder fallback; every navigation destination is bound to a implemented feature. Old service-worker fixtures and redirect adapters remain bounded compatibility test/runtime contracts, not a retained GUI.

Post-retirement full frontend verification: 671 tests across 45 files, TypeScript and ESLint passed. Canonical final build is recorded separately after completion. Real browser/Windows acceptance remains unavailable here: command-line Chromium failed at AF_UNIX setup, and a supported cloud browser opening an inert loopback probe returned ERR_BLOCKED_BY_CLIENT. No alternate-host or security-flag bypass was attempted.
