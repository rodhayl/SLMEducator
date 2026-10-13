# Source-review consistency candidate, 2026-10-13

## Result and scope

Partial delivery: the bounded v13 instruction change and its offline regression
are verified. Model compliance is NOT_RUN, not fixed or accepted by inference.
The historical 33/36 semantic result is unchanged. No new provider calls, model
downloads, native installation, user-data inspection or release occurred.

Base: `99bb6066e0e949f35907dc63249aa3860eec7aeb`, tree
`0f1e1002928715ecd423bc022f92ec577821583f`, branch
`fix/react-functional-continuation-20261007`. Its v12 change was already
published. The earlier campaign RESUME.json is a pre-commit session snapshot:
its cc0c41d identity and uncommitted descriptions must not be read as current
branch state. Historical campaign receipts were not changed.

The six-file code/test diff SHA-256 is
`044545ffa58d99104cccce355c75a6e06520faa4779dc266629677b96374baef`.
This report and accompanying evidence are documentation additions after that
diff, not further product changes. The containing Git commit identifies all
published bytes.

## Changes

- Eight additive lines in the shared lesson source-review instructions require
  source_review to agree with unresolved conflicts described in the model's
  own sections or summary. Merely describing both values does not replace a
  conflicting issue and a direct teacher question.
- New lesson version: `teacher-reviewed-v13-review-prose-consistency`.
  Tutor and other generation versions are unchanged.
- The nested-topic transport digest changes intentionally because this route
  embeds the shared contract. The fixture now labels this exception explicitly.
  Frozen lesson request/source-usage pairs and semantic rubrics are unchanged.
- Two route-level instruction checks and a synthetic punctuation-encoding test
  were added. The shared backend/frontend rendering fixture gained a fresh
  synthetic case, without modifying any previous case.
- No semantic keyword classifier, automatic approval, renderer modification,
  validation relaxation or provider configuration change was introduced.

The development followup-conflict observation motivated the consistency check.
Reserved validation cases did not guide this change. A prompt change is an
attempt to improve compliance, not proof that the real-model weakness is fixed.

## Corrected diagnosis: encoded clarification text

In the historical development case named reserved-conflict, teacher_question
is plain text. `require_lesson_source_review` deliberately escapes punctuation
into numeric entities when creating the leading source_clarification section.
This protects literal questions from Markdown/HTML interpretation. That means
the entities in the saved JSON cannot be attributed to Gemma merely because
they occur in the returned lesson.

The unchanged ContentRenderer safeContent implementation was transpiled and
executed with marked 15.0.12, DOMPurify 3.4.16 and jsdom 24.1.3. All 24 checks
across 12 synthetic fixtures passed: the leading question and flattened body
retain the literal question without active script/image/SVG/iframe or event
handler nodes. The historical development clarification also rendered exactly
as its plaintext teacher_question, with no visible numeric colon entity.

This is evidence about encoding provenance and DOM text. It does not certify
native painted layout, audio, the whole historical lesson, or a new semantic
score. The original 33/36 report is preserved; its attribution of this entity
pattern to model noncompliance is not supported by the observed application
pipeline. The escape boundary remains intact.

## Checks executed

- Baseline selected source-review/instruction suites: 57 PASS.
- Final eight-suite offline regression: 242 PASS in 39.75 s, exit 0. See
  [offline-tests.txt](offline-tests.txt).
- The first expanded attempt had 240 PASS and two harness failures because
  pytest-asyncio was missing. After installing the declared pytest 9.0.2 and
  pytest-asyncio 1.3.0 into an isolated temporary dependency directory, the
  complete selected set was rerun successfully. No failed test was excluded.
- Source-review plus instruction suites alone after additions: 61 PASS.
- Renderer boundary: 24 synthetic checks and the historical development
  clarification passed. See [render-checks.json](render-checks.json).
- flake8 7.3.0: modified product files and instruction test pass; see
  [lint.txt](lint.txt). The source-review test file retains three existing
  F401/F811 diagnostics from fixture imports; no new diagnostics were added.
- `git diff --check`: PASS.
- Independent read-only review: no blocking findings. Reviewer reproduced both
  topic request hashes, checked version propagation and unchanged frozen
  expectations, and requested the baseline-exception annotation now included.

Command, from a prepared checkout, with isolated synthetic test state:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest \
  tests/trust/test_lesson_source_review.py \
  tests/trust/test_lesson_instruction_consistency.py \
  tests/trust/test_ai_generation_boundaries.py \
  tests/trust/test_generation_prompt_budget.py \
  tests/trust/test_generation_sources.py \
  tests/trust/test_provider_transport_contract.py \
  tests/trust/test_source_documents.py \
  tests/trust/test_tutor_text_fallback.py \
  -q --basetemp=/tmp/slm-test-r8
```

Execution was in a lightweight Linux x86-64 source snapshot, Python 3.12.14,
with no available Windows desktop or real-model endpoint. Source bytes were
verified against Git blob identities when materialized. This was not a full
requirements installation or whole-repository suite. Synthetic databases and
logs were created by the repository's isolation fixtures. Disk pressure on the
main workspace required temporary storage; the published source/evidence is
the recoverable result, not that temporary directory.

## Still open

- V13 real-model quality: NOT_RUN. Keep the historical score and failed cases;
  do not claim a 36/36 result or silently rerun/tune the reserved split.
- Full offline aggregate, complete frontend gate, Windows build and installed
  native acceptance: NOT_RUN for this candidate.
- Previous installed-build identity, backup retention, Narrator, launcher and
  installed LEARN-03 items remain as recorded by the original campaign. No
  assumption that installed 29df5ed contains this source change.
- Provider cancellation/unavailability/recovery and SLM-AUTO-020 reproduction
  remain unclosed. This narrow change does not establish those outcomes.

The next dependent step is explicitly scoped real-provider validation when
the authorized endpoint is available, or native acceptance on a connected
Windows executor. Publication alone is neither installation nor acceptance.
