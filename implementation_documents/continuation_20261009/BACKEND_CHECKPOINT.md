# SLMEducator backend continuation, 2026-10-09

## Provenance and scope

- Repository: `rodhayl/SLMEducator`; branch: `fix/react-functional-continuation-20261007`.
- Read source commit: `abd33afd1bf2708064f3f80466fa993f360d3490` (actual tree `c63582f86287a99f349aed5ef92addca594e68bc`).
- This is a SHA-verified materialization through the connected GitHub API, not a Git clone. All 547 selected text/source files match their original Git blob identity before edits. All files under `src/`, `scripts/`, and `tests/` were recovered. Historical bulky evidence and binary screenshots were not materialized; they must remain unchanged in the remote base tree.
- Read repository working rules, README, CONTRIBUTING, campaign reports and defects. No `.agents/skills` entries exist in the current tree.
- Python 3.12.14 on Linux, dedicated venv installed from pinned requirements-dev.txt; no user database, existing installation, provider, model download, or paid inference used.

## Checkpoint 1: UTF-8 boundaries

The pilot CLI has three applicable text reads: the seed fixture, the evaluation case catalogue, and the evaluation observations supplied to the CLI. They now declare UTF-8. The first-admin masking source assertion and operational-documentation assertions now read their UTF-8 source documents explicitly.

A scoped pytest fixture changes only implicit `Path.open` text defaults to cp1252, including Python's `encoding='locale'` path. It leaves explicit UTF-8 and binary I/O intact. This reproduces the Windows decoding condition on a UTF-8 Linux host without claiming to have run Windows.

RED: 5 failed, 13 passed before read-boundary changes:

1. First-admin masking assertion misread the bullet character.
2. CONTRIBUTING raised UnicodeDecodeError under cp1252.
3. Real synthetic pilot seeding persisted `RecuperaciÃ³n` instead of the exact source title.
4. Evaluation catalogue could not match a synthetic accented case ID.
5. Evaluation CLI corrupted an accented observation value.

GREEN: 85 tests passed across first-run, operational docs, pilot Unicode, existing pilot tooling and seed_admin tests. Existing database refusal and bootstrap boundaries remain covered. Focused style lint passed for all six encoding checkpoint files.

Files and exact content hashes are in `backend-manifest.json`; the bounded diff is `encoding.patch`. Two pre-existing long string literals were wrapped without changing their string values so the affected scripts pass focused style lint.

## Checkpoint 2: additional contract coverage

74 tests passed across provider transports, tutor request lifecycle, private note retention and historical lesson titles. Additions verify:

- All four provider adapters receive lesson budgets 1000 and 4000, but tutor budgets 1000 and 1200, for account ceilings 1000 and 4000 respectively.
- Both tutor API routes report the same effective ceiling in request receipts as is sent to transport.
- A student's teacher assignment transferred away and back retains each teacher's own note and unrelated settings; neither teacher inherits the other's note or retains access after losing the assignment.
- Repeated author and learner reads under English/Spanish headers preserve historical titles, ciphertext and updated_at. A newly synthesized section remains untitled; existing authored headings are never rewritten.

The diff is `contracts.patch`. No production budget, role, retention or title-normalization logic was changed by this checkpoint. Initial test-fixture construction omitted a required provider response `model`; that test setup was corrected before the 74-pass run and is not a product defect.

## Similar-I/O review

The audit used AST call inventory and then traced the actual paths and payload contracts. Runtime settings, translations, frontend artifacts and source uploads already declare UTF-8. Binary key handling and exclusive bootstrap-marker file descriptors are binary; the remaining JWT secret text is generated ASCII. Existing ASCII fixture readers were not rewritten blindly.

Additional proven issue, not yet applied in these checkpoints: LoggingService's two file handlers and the launcher's api.log omit explicit encoding. An isolated subprocess with simulated cp1252 file handlers drops nonrepresentable warning records with UnicodeEncodeError; even accented messages are not stored as UTF-8. `logging_locale_probe.py` and `logging-red.log` record this synthetic reproduction. It does not establish the cause of the historical generation HTTP 500.

## Aggregate checks and limits

- pip check: pass.
- Critical Python lint (`E9,F63,F7,F82`): pass across src/scripts/tests.
- Audited four-file domain mypy gate: pass.
- Full offline Python and whole-source coverage gate before logging changes: PASS, 1750 passed, 57 skipped, 5 deselected, one warning, 1430.78 seconds. Whole-source coverage 86.72% (9691 statements, 1287 missed), above the 80% requirement. This result covers the stable ten-file backend checkpoint; a later logging change requires fresh verification.
- The existing lifecycle test's imported pytest fixtures trigger its existing broad-style F401/F811 messages; critical lint is clean. New checkpoint files introduce no such fixture warnings.
- Native Windows GUI, installer/update/uninstall, first-admin credential entry and LM Studio remain outside this Linux execution. No historical campaign status or evidence was rewritten.

## Checkpoint 3: Unicode diagnostics and UTF-8-mode-safe regression simulation

New production writes use UTF-8 in both LoggingService file handlers and the launcher's api.log basicConfig. No existing log file is rewritten or migrated; older bytes may retain their original encoding. Real Windows and the historical HTTP 500 remain unverified.

The first locale simulator intercepted Path.open, but Python's explicit UTF-8 mode resolves omitted encodings inside Path.read_text first. The CI workflow sets PYTHONUTF8=1. A targeted self-test demonstrated this harness defect; the product UTF-8 fixes were unaffected. The simulator now intercepts Path read_text/write_text/open before implicit-codec resolution and tests implicit reads/writes, explicit UTF-8, explicit locale and binary preservation. Likewise, logging simulation intercepts FileHandler construction and basicConfig's own default-resolution boundary.

A separate control materialization restored only the old product read/logging code while keeping the final regression simulators. It produced exactly seven failing regressions and fifteen passes under both PYTHONUTF8=0 and PYTHONUTF8=1. This proves the CI flag does not mask a recurrence. The final candidate produced 89 passes under both flags (23.30 and 22.14 seconds respectively).

- Final five-file diff: logging.patch.
- Final five-file hashes and base identities: logging-manifest.json, relative to remote commit 3253431875eec4e51e8f1391498f44fb9a3d7b6b.
- Original-code controls: locale-control-mode-0-red-final.log and locale-control-mode-1-red-final.log.
- Candidate checks: utf8-mode-0-green-final.log and utf8-mode-1-green-final.log.
- An earlier logging affected suite passed 193 tests before the simulator strengthening; this is retained as earlier evidence, not substituted for final verification.
- Short-lived aggregate attempts were deliberately interrupted while the simulator was corrected; their partial logs are retained and are not passes.
- Final aggregate with PYTHONUTF8=1: PASS, exit 0. 1754 passed, 57 skipped, 5 deselected, one warning in 1527.54 seconds. Whole-source coverage: 86.71963677639046%, 8404 covered of 9691 statements, 1287 missed. All final five-file hashes remained unchanged. Exact final results, all 13 backend-file hashes and evidence hashes are in final-validation.json.
