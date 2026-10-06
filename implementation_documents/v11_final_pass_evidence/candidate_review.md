# Lesson claim consistency: reviewed local candidate

## Identity and scope

Source commit: `a9d3760e541ae8a60b572b372d47f3e90b2e8894`, parent `ae42d5d6c46222ab5f318bfe97a6a843e8b94b08`. Source-commit tree: `626c74ac1de70728bda97468c58cdc86737c84b5`; application `src` tree: `359f6da21725cd361a72aa337874905870acae14`. The follow-up documentation commit adds this evidence only; it is not the evaluated application commit.

Eight frozen files were reviewed independently and checked against their hashes. The complete source commit preserves all 396 unrelated existing blobs and adds three test/fixture files. Application changes are a consolidation of the existing generate_lesson system instructions and lesson-only prompt-version provenance. The effective system text is reduced from 5,619 to 4,349 characters at a 4,000-token budget. No tokenizer, profile registry, dependency, model judge, escaping/rejection layer, transport replacement or retry was introduced.

The single evidence rule now applies to title, sections, summary, vocabulary, discussion questions, source-review descriptions and teacher questions. Literal task/source serialization, selection and receipt hashes stay unchanged. All other 48 AIService methods and the shared source-review instructions are unchanged. New saved lessons use `teacher-reviewed-v11-consistent-lesson-claims`; exercises/assessments retain `teacher-reviewed-v10-separated-lesson-request`. Tutor and historical saved versions, replay IDs/positions and job fingerprints are preserved. The separately reviewed harness typing fix uses an explicitly typed case list without changing its output or control flow.

## Verification and limits

Author checks: 191 affected offline tests PASS (36.70 seconds), focused flake8 PASS, mypy PASS on four changed application/harness modules, diff whitespace check PASS. Independent reviewer: same 191 tests PASS (39.91 seconds), six additional inverse partial-generation/replay cases PASS (4.45 seconds), same frozen hashes and mypy PASS. The sole test warning is the existing Starlette/AnyIO deprecation. The six-case test initially assumed assessment generation and saved replay had identical JSON; the test was corrected to verify persisted identity/content rather than that false assumption. That correction did not change production code or the 191-test source receipt.

The six supplemental cases are preserved as a text evidence artifact, not installed as additional repository tests. No real model inference, weight download, dependency installation, full repository suite/coverage, browser run, Windows binary, Actions, merge, deployment or pilot is evidenced here. Sources/accounts in tests are synthetic. Logs with local paths and runtime secrets are not included.

The historical v9 result stays 37/44. The previous v10 single pass stays 35/44 historical regression and separately 8/12 development. Nothing is rescored; offline test success is not model or pedagogical acceptance. A new exact-commit single pass remains necessary.

## Characterization-pair caveat

The new six contrast pairs (12 variants) were frozen before application edits and are not a holdout, an extra scored battery or replacements for historical cases. One expected_behavior description, objective_scope/irrelevant_extra, calls unrelated carton mass “optional.” The actual application contract, both before and after this change, requires OMITTING unrelated details. Preserve the eight-file source receipt as reviewed; do not adopt that ambiguous wording as a future oracle. Any wording correction must be a separately identified fixture/documentation follow-up, not attributed to this unchanged 191-test source commit. No fixture wording was changed for publication.

## Reuse recommendation and deferred evidence question

Production keeps the existing HTTPX transport and Jinja dependency. The maintained LM Studio SDK already offers template rendering, token IDs and loaded-instance metadata/configuration; use it for a separately authorized, bounded inspection rather than implementing a tokenizer or framework. Use already-loaded handles; named model acquisition can load an absent model. The evaluation SDK is not a newly added or pinned application dependency.

Saved native evidence proves literal rendered control-marker exposure, not special-token interpretation in the backend. It contains no token IDs or backend special-token parsing provenance. Utility tokenization alone would not prove inference-path parity. No guard, escaping or profile inference is authorized by this evidence; that issue remains deferred.

Official references: [tokenization](https://lmstudio.ai/docs/python/tokenization), [model info](https://lmstudio.ai/docs/python/model-info/get-model-info), [loaded models](https://lmstudio.ai/docs/python/manage-models/list-loaded), [loading behavior](https://lmstudio.ai/docs/python/manage-models/loading), [prompt templates](https://lmstudio.ai/docs/app/advanced/prompt-template).

## Evidence

[Source manifest](lesson_claim_consistency_20261006_evidence/source_manifest.json), [verification receipt](lesson_claim_consistency_20261006_evidence/verification.json), [independent review](lesson_claim_consistency_20261006_evidence/independent_review.md), [supplemental test text](lesson_claim_consistency_20261006_evidence/inverse_partial_test.txt).
