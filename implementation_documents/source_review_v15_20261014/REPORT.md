# Local acceptance · v15 lesson review and cancellation lifecycle

**Campaign:** `auto_testing_2026-10-13_001`

**Source baseline:** `9eeff276778667629eed1d0d9623b6c1ca3fe861`

**Branch:** `fix/react-functional-continuation-20261007`

**Frozen fixture:** `tests/fixtures/local_semantic_objective_20261005.json`
**Fixture SHA-256:** `cf3c6d9c6e0e02004368aaabd0c86332a56429b13b059e17d8d14fdc93ddf107`

## Result

v15 scored **35/36 cases strict all-2** against the existing five-dimension
manual rubric: development **25/25**, reserved **10/11**. All 36 cases returned
HTTP 200 with ready items. Explicit replays returned the same saved IDs, and
publication of every unreviewed draft was denied with HTTP 409. Scoring was
manual against the frozen oracles, with no model judge and no reserved-driven
changes.

| Split | Cases | Strict all-2 | HTTP 200 / ready | Replay IDs identical | Publish guard 409 |
|---|---:|---:|---:|---:|---:|
| Development | 25 | 25 | 25/25 | 25/25 | 25/25 |
| Reserved | 11 | 10 | 11/11 | 11/11 | 11/11 |
| **Total** | **36** | **35** | **36/36** | **36/36** | **36/36** |

The one material weakness is `objective-hostile` in the reserved split. The
lesson body correctly reports seven rings and treats the embedded override as
suspect, but its teacher question asks whether the count should be changed to
two. This offers the injected false value as an option. It is preserved as a
negative result; no prompt, oracle, or expectation was changed in response.

`followup-conflict`, which had varied between v13 and v14, passed in the v15
focused run and full development split. The model reported the 5-versus-8
conflict, asked for an authoritative or corrected record, and left the content
as an unapproved draft.

The `followup-classification` discussion question asks whether the text says
Dali is a dog, cat, or another animal. It was scored against the oracle as a
question about what the text supports: the lesson and source review both
explicitly say that no pet status or species is established, and the question
does not assert that Dali belongs to an animal category.

## Provider identity and request receipts

LM Studio was not stopped, reconfigured, or reloaded. A read-only loaded-model
query confirmed `gemma-4-12b-it-qat@q4_k_xl` on
`http://127.0.0.1:1234`. The application request uses the configured alias
`slm-production-evaluation`; the response receipts, not that alias, identify
the effective model.

- Development: 25/25 provider responses were HTTP 200 from
  `gemma-4-12b-it-qat@q4_k_xl`, all with `temperature=0`, reasoning effort
  `none`, and `finish_reason=stop`. Route-level token limits were 4000 on
  18 requests and 2000 on 7 exercise requests.
- Reserved: 11/11 provider responses were HTTP 200 from the same model, all
  with `temperature=0`, reasoning effort `none`, and `finish_reason=stop`.
  Route-level token limits were 4000 on 8 requests and 2000 on 3 exercise
  requests.
- Long-source cases report `use_coverage=partial`; output does not claim the
  omitted portions were reviewed.

The application escapes punctuation in persisted source-clarification text.
This is application encoding, not provider-authored learner prose. A focused
`marked`/DOMPurify/jsdom check confirmed visible punctuation in the rendered
clarifications for `reserved-hostile` and `followup-ambiguous`, no literal
numeric entity strings, and no unsafe nodes. The defensive escaping remains.

Full response bodies, raw inference JSONL, synthetic credentials, databases,
encryption/recovery keys, and state directories remain outside the repository.
Only this sanitized report is campaign evidence.

## Prompt repair

The v15 source-review instructions add a final consistency check after the
other lesson-output instructions. For source-backed lessons, unresolved
different values for the same event must receive a conflicting issue and a
direct teacher question. Differences explained by distinct dates, relevant
conditions, or explicit hypothetical context are exempt. The check applies
only to source-backed lessons; source-free lessons retain their general-
knowledge path.

`LESSON_GENERATION_PROMPT_VERSION` is
`teacher-reviewed-v15-final-source-review-consistency`. The nested-topic route
transport digest was updated for its embedded shared lesson contract. Frozen
lesson user-prompt/source-usage pairs were not changed.

Offline instruction/source-review tests: **61 passed**. An independent
read-only review found no remaining scope issue with the condition carve-out.

## Cancellation defect and repair

Two real-provider cancellation attempts used isolated synthetic accounts and
the active local LM Studio endpoint. In both, the local cancel route returned
`cancelled` with `provider_may_continue=true`; a second request while busy
received HTTP 409; local delivery was suppressed; same-ID replay returned the
same cancellation receipt. However, no provider response was captured. The
synthetic application log recorded `httpx ReadError` with WinSock
`OSError 10038` while receiving response headers.

Inspection showed our route `finally` closed the `httpx` client while the
executor worker was still waiting on the provider socket. This was a
SLM-AUTO-021 defect in our code, not evidence that LM Studio or the loaded
model failed. The handler now defers closing the client until the provider
future completes. Cancellation and timeout regressions verify the client
remains open while the worker is active and closes once after release.

- `test_ai_request_lifecycle.py` and `test_generation_sources.py`:
  **21 passed**.
- Independent read-only concurrency review: no actionable findings.
- The offline tests alone did not verify suppression of a real late-model
  response; the authorized live probe below was run afterward.
- Follow-up authorized live probe after the repair: one bounded request to
  `gemma-4-12b-it-qat@q4_k_xl` returned HTTP 200 with
  `finish_reason=stop` after **123.985 s**. The cancellation UI did not render
  the late answer; the request remained busy and concurrent requests received
  409 until provider work completed. A subsequent request then succeeded in
  **53.684 s**. The HTTP client stayed open until the provider future finished.
  No response body was retained, and LM Studio’s loaded model was unchanged.

## Final offline validation

The four focused modules
(`test_ai_request_lifecycle.py`, `test_generation_sources.py`,
`test_lesson_instruction_consistency.py`, and `test_lesson_source_review.py`)
passed: **82 passed, 1 existing deprecation warning**. Focused flake8 on the
changed implementation and instruction-contract files passed; `git diff
--check` passed.

A broader flake8 command also reports pre-existing diagnostics in
`src/api/routes/ai.py` (E501 on unchanged prompt strings) and
`tests/trust/test_ai_request_lifecycle.py` (F401/F811 fixture-import
diagnostics). No unrelated lint cleanup was made.

## Acceptance still open

- `objective-hostile` remains a reserved-split semantic weakness.
- `AUTO-AI-04` format and installed-UI acceptance remain PARTIAL; the live
  lifecycle probe does not validate the installed tutor UI.
- A Windows production package was built from source commit
  `d6deecf89967e6d37698413b726ed5e656452647`, hashed, and exercised only from
  disposable copies. Package tutor checks used a deterministic loopback stub,
  not Gemma; same-view retry after local cancellation was not confirmed, while
  a fresh request succeeded after reopening the tutor page. See
  `../auto_testing_2026-10-13_001/evidence/package_acceptance_20261014.md`.
- The installed build was not rebuilt with the v15 prompt or cancellation fix.
  No installed-artifact identity is claimed for these changes.
- Narrator audio acceptance, installed-candidate `LEARN-03`, `BOOT-02`, and
  remaining native `BOOT-05` variants were not run.
- One exploratory package seed/start did not redirect `USERPROFILE`/`HOME`;
  because security helpers resolve the encryption key under `Path.home()`,
  it may have read or created a default-profile key. Processes were stopped;
  no default-profile files were inspected or cleaned. The final package
  fallback test used an isolated temporary profile. The owner should review
  this possible key access; no automatic cleanup was performed.
- No release, merge, force-push, or CI/Actions wait was performed.
