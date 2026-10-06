# Source trust: findings and local candidate

## Result

The v9 historical result remains **37/44 accepted** with all seven recorded failures. This local candidate repairs a reproducible framing ambiguity and separates lesson application instructions from task/source data. It has **not** been evaluated by the actual model and does **not** establish a semantic fix or release readiness.

Pinned source: `25d3f9e6942c4996d5dfd3d46361a1084ab74489` on `test/windows-v9-semantic-gui-20261006`. Read-only GitHub connector retrieval populated an isolated local selected-file checkout. Retrieved source and historical final-evidence blobs were verified against their Git SHA-1 identities, including original CRLF bytes. No user database or private configuration was retrieved. Local tests use disposable synthetic databases/configuration; installed test dependencies live in a separate virtual environment. Native Windows runtime was unavailable.

## What the evidence actually establishes

1. `generate_lesson` previously sent one large user message containing application rules, teacher fields and source text. Existing provider adapters already support a separate system channel. The configured temperature legitimately overrides the method's default; the historic temperature-zero run was valid.
2. `source_prompt` used fixed opening/closing prose around a literal fragment. A newly authored archive/token source reproduced two indistinguishable opens and closes while preserving a complete receipt. At least one historical attack also contains the old `END SOURCE DATA` phrase. Delimiter ambiguity is a mechanical defect; it is not proved to be the cause of every historic semantic failure.
3. The current review checker validates the shape of the model's declared concerns and makes declared teacher questions visible before lesson prose. It cannot tell whether the model found every false definition, whether a concern is genuine, whether cited text supports a claim, or whether a question offers an invented reconciliation. `no_issue_reported` is not a truth certificate.
4. All 44 final application receipts record HTTP 409 for unreviewed publication. The four historical open-answer grading checks remain provisional. No publication/grade guard bypass is alleged or changed by this work.

## Historical failures and oracle alignment

The six substantive failures remain: malformed definitions endorsed or silently corrected (two); injected directives treated as factual alternatives (three); and an unsupported reinterpretation of a same-event conflict (one). Role separation and better framing may help, but only native semantic evaluation can measure that.

`dev-explanation` is a separate objective/oracle alignment issue. Its actual request asks to explain observed petals and explicitly says to omit unrelated source details. The actual output explains four blue petals. The frozen oracle additionally requires daily watering quantity. Preserve the historical FAIL and 37/44; do not retrospectively rescore or alter the frozen fixture. Future rubric design should have an explicit decision on whether unrelated facts are required. The new development set includes a distinct objective-scope control with unrelated parcel mass, and does not retrofit the original case.

## Candidate contracts

- One inference per generated item; no second model, model judge or preflight pass.
- Lesson system message contains application rules; task JSON preserves topic, objectives, level and duration as literal data. Source remains literal selected text in the user channel.
- Deterministic collision-checked source token; 6000-character selected-source budget and all selection receipt values are unchanged. No attack-word filter, data deletion, fabricated fact validator or special-case reserved answer.
- Existing native output ceilings remain: lesson request 4000, capped by a positive configured ceiling. Temperature override and LM Studio `reasoning_effort` are preserved. Input text/role overhead changes, so actual tokenizer/context usage still needs native verification; no inferred token count is presented as measured.
- OpenAI/LM Studio/OpenRouter use their existing system/user message serializers; Ollama uses its existing `system` field. No new transport capabilities or structured-output parameter are assumed.
- The same source-review schema, parser/normalizer, teacher-question rendering, draft status, source-support `unverified`, publication approval and grading review remain intact.
- `_fingerprint` is unchanged. A v9 ready item is replayed with its v9 receipt and teacher edit. Only missing items actually generated after upgrade get a v10 receipt. Repeated v10 completion is idempotent; no new positions or duplicate items are introduced by a retry. No global job version hides mixed provenance.
- Tutor requests retain their existing prompt version. Shared framing also affects source-backed exercises, assessments and planning prompts; saved package items use the new generation-specific version accordingly.

## Why not a larger workflow now?

| Option | What it establishes | Trade-off / decision |
|---|---|---|
| Existing channels plus collision-checked framing | Auditable instruction/data transport and literal receipts | Small supported correction; selected for native evaluation |
| JSON-schema constrained output | Output shape where provider/model supports it | All 44 already passed structure; does not establish conceptual correctness or genuine conflict; not added |
| Per-objective review/evidence ledger in the same output | More reviewable declarations and mechanically checkable quote/span references | New output schema and token costs; matching quotes does not validate truth or completeness; defer |
| Review preflight followed by teaching call | Distinct workflow stage and opportunity to stop after declared concerns | Adds calls, failure/retry/accounting state and still relies on model judgment; no evidence yet that it outperforms the minimal change; not implemented |

The phrase “review before teaching” remains a model instruction plus the existing human approval boundary, not a separately executed semantic verifier. Do not call JSON key order or a declared empty issue array a completed correctness review.

## Official compatibility references

- [Gemma 4 prompt formatting](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4): unlike older Gemma guidance, Gemma 4 documents a system role. This does not verify the specific deployed GGUF's chat template.
- [LM Studio chat completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions): documents system/user messages and automatic chat-template application. Inspect the actual rendered native input in a later authorized run.
- [LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output): documents schema/grammar-constrained formatting, with model capability caveats. Shape is different from factual validation.

## Offline evidence

Environment: Python 3.12.14, Node 24.19.0, npm 11.9.0. Runtime/development packages were installed from the repository's pinned requirement files; `pip check` passes. DOM dependencies use the unchanged lockfile and `npm ci --ignore-scripts`. These are Linux source-run checks, not native Windows verification.

- Baseline affected battery: 102 PASS before changes.
- New transport/framing regression before changes: 16 FAIL, then the same 16 PASS after the candidate.
- Focused candidate battery including new upgrade/replay cases: 125 PASS, 1 existing TestClient deprecation warning.
- Critical lint: PASS for all `src`, `scripts` and `tests` (`E9,F63,F7,F82`, serial worker).
- New test-file mypy with fresh analysis: PASS.
- Maintained four-module mypy gate: PASS with the repository's unchanged `mypy.ini` and SQLAlchemy plugin. Earlier partial-checkout runs lacked that file and reported an int/Column mismatch on both baseline and candidate. That was a local preparation issue, not a demonstrated repository defect. A provisional typed view was removed as unnecessary; no cast, `Any`, ignore, schema or model change is retained. Earlier unconfigured logs remain available but must not be read as the maintained gate result.
- Expanded offline run initially had 439 PASS / 5 FAIL because public checkout support files were not yet materialized (.bat, workflow YAML, two tooling fixtures). Those are preparation failures, not demonstrated product regressions. After retrieving the exact baseline files, the complete unchanged expanded command passed **444/444**, with one existing TestClient deprecation warning, in 213.79 seconds. Both logs are retained.
- Complete maintained DOM suite: 194 PASS, zero failures/skips, 25.31 seconds on final source bytes. Initial npm/DOM attempts failed because the default npm cache was not writable; `npm ci --ignore-scripts` with a new writable cache installed the locked dependencies, without changing package files or integrity checks.
- Complete maintained Python+coverage command on final source: **1026 PASS, 37 SKIP, 5 deselected**, one existing TestClient warning, **81.62% coverage** against the unchanged 80% minimum, in **921.67 seconds**. Skips are the 23 real-provider-dependent tests, 13 explicitly gated browser tests and one native Windows package test; five real_ai cases were deselected. The manual, e2e and real_ai directories remain excluded. No external provider, browser or Windows gate was forced.
- This local Python run took 15 minutes 21 seconds. The existing Actions workflow gives its entire job 15 minutes; Actions was not run, so local success does not certify that remote workflow timing. No timeout or workflow setting was changed. Historical 13 synthetic browser checks and all native-model results remain separate evidence.

An independent source/contract review found no runtime defect. Its separate focused run passed 125 tests in 29.89 seconds and 48 additional adversarial framing/receipt checks passed, including numeric-prefix collisions, Unicode/control characters and maximum-length inputs. AST comparisons confirmed unchanged selection, fingerprint, provider adapters, parser, output limits and source-review validator. The reviewer identified an inaccurate proof comment about substring starting positions; it was corrected to use ending positions, without changing executable behavior. The final comment-only revision passed the complete focused battery again: 125 PASS in 25.12 seconds, with the same existing TestClient warning.

Maintained aggregate command, with `SLM_OFFLINE_TESTS=1`, `USE_REAL_AI=0`, `PYTHONUTF8=1` and a new disposable basetemp:

```text
python -m pytest tests -q -ra --strict-markers
  --ignore=tests/manual --ignore=tests/e2e --ignore=tests/real_ai
  -m "not real_ai" --cov=src --cov-report=term --cov-fail-under=80
  --basetemp=<new-synthetic-directory>
npm test --prefix tests/ui
```

The independent reviewer also verified the recovered mypy.ini's exact Git blob and repeated both baseline and maintained candidate typing with fresh caches. They passed; the initial type error attribution is superseded by that evidence. No repository type change is needed.

## Development cases and later acceptance

`tests/fixtures/local_semantic_source_trust_development_20261006.json` contains twelve new development cases: forged delimiters, forged role text, suspect/sound perimeter definitions, same/different-event temperatures, an explicitly superseding source correction, an unfamiliar fictional stamp, narrow objective scope, missing evidence, arithmetic exercise and open-answer evidence limits. They are unexecuted model cases, not new holdout evidence. Their shape is compatible with the existing evaluator's `--cases-file` and `--split development` path. Do not run it during this phase.

All previously observed 44 cases are regression cases now, even where their frozen label says reserved. Preserve both original fixtures and all seven historical failures. A future untouched holdout must be authored and isolated separately after the candidate is fixed; these newly visible development cases cannot serve that purpose.

Later native control: Gemma-4-12B-it-qat-UD-Q4_K_XL GGUF SHA-256 `90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370`; LM Studio 0.4.25.0; llama.cpp CUDA12 avx2 runtime 2.51.0; loaded context 8192; configured temperature 0; maximum 4000; reasoning none. Start new synthetic state, verify per-item v10 provenance, preserve every request/response, inspect effective chat templating and usage, and use frozen historical oracles. Semantic acceptance remains pending until that authorized evaluation. No EXE, pilot or deployment follows from offline contract passes.
