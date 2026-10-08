# Returned campaign repair and first-install setup

Date: 2026-10-08. Repository: `rodhayl/SLMEducator`.
Working branch remains `fix/react-functional-continuation-20261007`.

## Source and evidence identity

- Original returned report: `16a2dd9ba84fbaf103aff056fee8b07372c5102e`, exactly 26 documentation/evidence files over tested commit `0f3ff15292f84a7d6877f9f2d6e47a3f646355f4`.
- The report's product baseline is `642966a93e7e9c9f9c5e93cce0bc842f538846fb`; later pre-report changes were documentation only.
- Credential-redaction checkpoint: `e55e618e6a7d456b143886ae1cda3cc1bd896f29`, same branch and parent report commit. Five files changed only to redact 16 occurrences of synthetic credential inputs. No credential values are reproduced here. History was not rewritten; any exposed still-usable credentials require owner-controlled rotation.
- Original campaign matrix remains 117 rows: 45 PASS, 41 PARTIAL, 4 FAIL, 26 BLOCKED, 1 NOT_APPLICABLE, zero NOT_RUN. These historical outcomes were not promoted by offline fixes.
- All 12 committed text report files were inspected; all 14 PNG screenshots were visually inspected. No visible plaintext credentials or provider keys were found in those screenshots. Images were unchanged.
- CSV evidence types are 85 `GUI_CDP`, 6 `GUI_CDP+TECNICA`, and 26 blank. This establishes a reported browser/CDP campaign, not native screen control, installed Setup, screen-reader, zoom/DPI, scale, service-worker, or downloaded-file acceptance.
- The report cites `evidence/ai_generation_failure.log`, but that file is absent from the committed evidence tree. Session snapshot references are not separately committed artifacts. No missing trace or provider reply was reconstructed or invented.
- All 411 tracked files under `src/`, `scripts/`, and `tests/` were available and matched the report source before edits. This was a sparse materialization: 158 unrelated historical documentation/evidence files were not needed for the repair. Original tree/blob identities were retained for comparison.

## Returned defects

| ID | Candidate result | Evidence / limitation |
|---|---|---|
| 001 | Rapid search repaired | Same-tick People typing reproduced loss of characters. Synchronous router updates preserve input. Same defect independently reproduced and repaired in course/material search. |
| 002 | Empty-library guidance repaired | Actual empty library and filtered-out results now differ; no no-op reset in an empty library. |
| 003 | Duplicate choice-key validation repaired | Relevant fields are marked, focus moves to the first error, input survives and corrected save works. |
| 004 | `/tutor` delivery repaired | Server allowlist includes current tutor route; legacy tutor destination matches it. New parity test checks every menu destination. |
| 005 | Failure handling repaired; original cause remains open | Synthetic HTTP-200 truncated/invalid replies now produce explicit unsaved-proposal failures with localized guidance and safe diagnostic frames. No incomplete content is admitted or saved. Original response is unavailable; live provider retest is still required. |
| 006 | Course identity repaired | Stable course IDs distinguish identical titles in lists and shared selectors. |
| 007 | Empty lesson headings repaired | Empty optional fields/sections are omitted while real content, source clarification and de-duplication remain intact. |
| 008 | Rubric grading available | Teacher can enter criterion scores and explicitly apply the visible scaled total. Readable breakdown persists in feedback; existing save/finalization confirmations remain. Criterion inputs themselves are not a new structured persistent record. |
| 009 | Assessment linkage visible/editable for authors | Existing links survive reopen and can change only on mutable drafts with resource authorization. Learner serialization is restricted to avoid disclosing author-only linked IDs. |
| 010 | System notices localized separately | Attempt/automatic-grading notices use typed localized presentation. New lifecycle events do not overwrite teacher feedback. Ambiguous historical approved wording remains verbatim with an authorship explanation. |
| 011 | Existing retention/access policy preserved; decision remains open | A synthetic note written before transfer remains stored for its author and is not inherited by the new teacher. Current policy revokes profile/progress/notes access from the former teacher. No access expansion was published. An archive would require a product retention/access decision. |
| 012 | Source-file rejection feedback repaired | Empty, unsupported and oversized files get distinct field-associated messages before requests; existing source remains unchanged. |
| 013 | New inline lesson headings repaired | Normalization no longer invents English section titles. Historical stored titles are not rewritten because app defaults cannot be distinguished from authored text. |

These are deterministic source/API/DOM results, not fresh GUI closure of the original campaign. Domain details are in `assessment_returned_defects_20261008.md` and `returned_defects_course_material_20261008.md`.

## Generation failure boundary

An HTTP-200 provider response does not establish usable generated content. Explicit provider output exhaustion has its own exception and response code; parse/content errors and provider failures have distinct safe codes. Recognized failures from proposal-only endpoints carry `saved: false`. The shared frontend accepts that exact bounded receipt, preserves input, and shows actionable EN/ES guidance. Ordinary 5xx/network/interrupted mutations remain uncertain; no inference is retried automatically, no token budget is silently increased, and package persistence retains its existing independent-item semantics.

The diagnostic log records fixed category, exception class and function/line frames. It does not log the exception value, prompt, generated reply, credentials or endpoint secrets. Real LM Studio output was not requested during this repair.

## First-install administrator setup

The local installation owner chooses the first administrator username and password before the HTTP server starts. The native dialog masks both password fields; a terminal fallback requires an interactive terminal and rejects no-echo failures. Cancel or invalid/unavailable setup starts no server. There is no unauthenticated HTTP administrator-claim endpoint.

The existing `scripts/seed_admin.py` owns preparation and creation. It prepares a complete account-free database in a private sibling directory, checkpoints/closes WAL, and publishes it with an atomic no-clobber hard link. Existing destinations are inspected read-only. A concurrent loser discards only its own temporary files; interruption before publication leaves no ambiguous final database. The nonsecret pending marker uses the existing audit schema. The first account plus completed marker are committed under one `BEGIN IMMEDIATE` SQLite transaction without changing journal mode. Concurrent submits admit one administrator. Established accounts are never reset, unlocked, promoted or modified. Existing non-admin-only or unknown-empty databases require authorized recovery; deleting all administrators does not reopen initial setup.

Production packaging now prepares an account-free pending database rather than pre-seeding an administrator. Build-time password/email overrides do not create a distributed credential. Explicit test snapshots preserve their selected accounts and data. The older manually invoked provisioning command remains separate from normal launch and distribution.

A concurrency regression found a pre-existing database initialization bug: every service registered another global SQLAlchemy engine listener. The handler now belongs only to its own engine, avoiding mutation of a shared listener deque during simultaneous connections.

## Verification status

Final frozen product/test identity: `0c5b56dd3c350d64b1d0348bb4cd7955ac21cbfe53e2b91112330d963bee194b`. The final offline Python collection has 1,778 selected tests in 124 files (5 real-AI-marked cases deselected). Nine independent pytest batches executed all 1,778 unique IDs exactly once: **1,721 passed, 57 skipped**, zero failures/errors, omissions or double counts. All nine terminal receipts report the same source identity and zero changed frozen files.

Combined whole-source coverage is **86.71%**: 8,403 of 9,691 executable lines covered; 1,288 missing and 58 excluded. The existing 80% gate passed. Original per-batch coverage files were retained. This is complete batched offline scope, not proof of monolithic test-order/cross-module state behavior.

The final frontend `npm run check` passed TypeScript, full ESLint, **953 tests in 52 files**, and production build validation (26 local assets, 29 dependency license records). Critical Python syntax/name lint and seven audited mypy scopes passed. Maintained-guide checks passed **13 tests** after their separate documentation-only update. No frozen product/test file changed during these final gates or documentation edits.

The 57 skipped tests remain unverified:

| Scope / recorded reason | Count | Acceptance limit |
|---|---:|---|
| Configured AI provider unavailable | 23 | No live provider/model-quality result; transport is disabled for the offline gate. |
| Explicit isolated browser acceptance only | 18 | No new real-browser acceptance, downloads, service-worker lifecycle or native zoom result. |
| Actual Windows cmd and CHOICE required | 10 | Windows command/prompt behavior not executed on Linux. |
| Actual Windows cmd required | 3 | Native command behavior not executed on Linux. |
| Newly built Windows installer required | 1 | Setup lifecycle not executed. |
| Newly built synthetic Windows package required | 1 | Post-setup login/rotation/restart harness not executed; it does not test the new first-run dialog. |
| Explicit native Windows package recovery only | 1 | Frozen backup/restore acceptance not executed. |

Selected earlier checks provide diagnosis and overlap with the final scope: complete affected-AI caller union **905 passed, 26 skipped, 5 deselected** across 49 modules; route parity/delivery **129 passed**; final renderer **108 passed**, including a 75-combination legacy-body matrix. These counts must not be added to the final aggregate. The machine-readable [verification summary](returned_defects_repair_20261008/VERIFICATION.json) records batch file assignments, terminal evidence hashes, skip groups and reviewed source hashes. Raw local logs and runtime data are intentionally excluded from Git.

### Preserved failed and interrupted attempts

- The first monolithic Python attempt is incomplete/unusable: execution identity was lost after a log showing 81%. No PASS or coverage claim is made for it; a fresh isolated workspace was used afterward.
- The first diagnostic batch caught **13 regressions introduced by the candidate privacy change**, which removed useful timeout/connection/HTTP categories. Those existing tests were retained unchanged. Fixed allowlisted categories restored the contracts without echoing provider values.
- The next batched attempt preserved **10 failures** from a parameterized raw-exception-message assertion and **5 failures** in missing-key, unsupported-provider, invalid-JSON and raw-HTTP-body contracts. Useful fixed categories were restored in product code. The deliberately unsafe raw-exception and raw-body assertions were explicitly changed to safe connection/HTTP-400 categories plus no-leak assertions, retaining the original raise, one-provider-call, no-last-response and unsaved-outcome checks.
- All first-failure receipts/logs remain available locally. The complete affected-caller union passed before source was frozen and all nine final batches were rerun; no failed receipt was relabeled as a pass.

## Maintained continuation guidance

`AUTO_TEST.md`, `MANUAL_TEST1.md` and `MANUAL_TEST2.md` now cover owner-selected first-administrator setup, cancellation/restart and configured-install closure. Credentials (including synthetic or invalid inputs) must not appear in coverage/resume/report/log/screenshot evidence. Native credential entry is an owner handoff. The historical Windows handoff remains untouched to avoid recirculating legacy local metadata; use the maintained guides above for current instructions. The original returned campaign CSV and its 117 historical outcomes remain unchanged.

## Remaining acceptance

No user computer, production database, real-provider/model spend, Actions execution, main update, merge, release, installer build or native Windows acceptance occurred. New installed first-start/login, keyboard/DPI/screen-reader checks, live provider generation, real browser interrupted/repeated flows, historical title decisions, and the enrollment-note retention decision remain explicit follow-up gates. Product changes require review before same-branch publication.


## Independent review corrections

Bootstrap review found and reproduced a crash/concurrent-initialization window in the initial reservation approach. Atomic publication of a closed, fully prepared database removes it. Six competing account submissions were independently checked: one created, five closed; account/marker rollback and deleted-admin closure were preserved.

Content review found legacy fallback/whitespace de-duplication and one-sided vocabulary regressions. Both are repaired. The focused renderer file now has 108 passing cases, including a 75-combination field/fallback matrix. Final reviewed hashes: bootstrap `c47853fe6e59c3ffdf4e97475f60559f4d090870bdc409a5d3e65b405ef9ca7c`; lesson renderer `edb7ba2bacea12b7ef09ed2952f43372bdd0ab7243213c68b6879d6883920018`.

Known filesystem limit: no-clobber first-run publication requires same-volume hard-link support (for example NTFS on Windows). An unsupported filesystem fails before publishing a destination. Native Windows acceptance remains unverified.
