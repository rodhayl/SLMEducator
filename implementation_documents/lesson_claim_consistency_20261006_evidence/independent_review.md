# Independent review: frozen lesson-instruction candidate C

## Verdict
No blocking code or contract regression found in the eight-file frozen candidate against baseline ae42d5d6c46222ab5f318bfe97a6a843e8b94b08. Suitable for the next separately authorized semantic evaluation; this is not semantic acceptance, publication approval, or evidence of model improvement.

## Independent checks
- Verified all eight file SHA256 values plus candidate/typing patch hashes against the manifest. Candidate unchanged by this review.
- Read AGENTS.md, README, contributing guidance, full production diff, affected workflow, shared source-review instructions and tests.
- Compared exact AIService method source using AST locations: generate_lesson is the sole changed method; all other 48 are byte-identical. The change stays in its system instruction string. Literal task serialization, source receipt extraction, call settings, parsing and provider implementations are unchanged.
- Independently reran the supplied affected set: 191 passed, one upstream Starlette/AnyIO deprecation warning, 39.91 seconds. Includes adversarial literal source/task strings; all four provider transports at three budgets; 12 frozen source receipt/request pairs; other-route request hashes; replay, source ingress, source review, budget and publication gates.
- Added six external synthetic cases: old v9 or v10 package with failure in lesson, exercise or assessment; upgrade and resume; replay again. All six passed in 4.45 seconds. They check missing lesson -> v11, other missing kind -> v10, old ready receipts/content/IDs/positions preserved, source-version hash unchanged, source support unverified, no repeated model call on ready replay, and publication denied without review.
- Focused mypy on all four changed Python production/harness modules passed. git diff --check passed.

## Semantic review
The consolidated text preserves the principal contracts: task values are data, objectives are not evidence, supplied observations remain attributed, derivations require premises, shared properties do not prove category membership, missing/disputed objectives require a direct teacher question in the section, and output remains bounded structured JSON. The unchanged shared block explicitly separates attribution from endorsement and handles suspect definitions without silently repairing them. New cross-field consistency and question wording address the stated claim-surface issue without introducing semantic validators or a new framework.

Recorded correction versus answer-changing directive, same-event conflict versus documented sequence, and suspect versus sound definition remain judgments for the model and human reviewer. The instructions alone cannot establish that those judgments improve. The general-knowledge-without-sources direction coexists with source-only premises wording, as before; this is not a newly introduced defect. No tokenizer, dependency, profile, escape filter, judge, transport replacement or retry was added. B remains deferred.

## Minor non-blocking observation
In tests/fixtures/lesson_instruction_contract_pairs.json, objective_scope/irrelevant_extra says the unrelated carton mass is “optional.” Both baseline and candidate instructions say to omit unrelated source details. Before using this new characterization pair as a future human grading oracle, make that wording unambiguous. It does not affect current runtime behavior or the offline assertions, and no historical oracle/score should be changed for this observation.

## Test-development disclosure
The initial external six-case test assumed first-generation assessment response and later saved replay had identical JSON shape. That assumption failed: the existing workflow returns generated assessment questions initially and the stored assessment pointer on replay. The production code for that behavior is unchanged. The corrected test checks the persisted ready-item content/identity and receipt, rather than asserting nonexistent response-shape parity. Initial failure log retained as inverse-initial-assertion.log; corrected tests in test_inverse_partial.py and inverse-tests.log.

## Scope limits
No real model, model download, browser, Windows build, full repository coverage, Actions, remote mutation or publication. Mocked structural acceptance remains explicitly separate from semantic correctness. No v9/v10 responses or scores were relabeled or rescored. Existing historical results remain unchanged.

