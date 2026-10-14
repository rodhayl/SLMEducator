# Tutor presentation contract repair — 2026-10-14

Baseline: `72c85777977c4cc3e36928dd25c94e1f88709c54`.
Scope: source prompt and synthetic HTTP integration only.

## Repair
The tutor return example is valid JSON. The student-facing explanation now follows the current question's requested length and presentation, subject to teacher policy; optional related topics and encouragement must not exceed that request. Teacher policy, source uncertainty, references, untrusted-history boundaries and grade context are preserved. No parser, route, UI, lifecycle, configuration or provider implementation changed; AST comparison outside the tutoring prompt was identical.

## Evidence
- Baseline RED with the final focal tests: **4 failed, 6 passed**, exit 1. Failures cover JSON decoding, both presentation parameters, and the route prompt assertion.
- Final GREEN: **27 passed, 1 existing Starlette/AnyIO deprecation warning**, exit 0, 8.20 s. Independent review also reported **27 passed**.
- Test selection: `tests/trust/test_tutor_prompt_presentation.py tests/trust/test_generation_sources.py tests/trust/test_resource_contracts.py -q`.
- New-test flake8 (100-character limit) and source flake8 F/E9 checks passed.
- Python 3.12.14; existing environment. HOME, USERPROFILE, APPDATA, LOCALAPPDATA, database, configuration and logs isolated before application import; only disposable synthetic test state.
- `SLM_OFFLINE_TESTS=1` and the existing transport-blocking fixture prevent external calls. The real FastAPI route and AIService/parser were exercised with synthetic provider responses.

### Reviewed file SHA-256
- `src/core/services/ai_service.py`: `ba4469e9c526aa0022b04e0c17123604b10ee9b9dea24bd29aefcd53afedc51f`
- `tests/trust/test_tutor_prompt_presentation.py`: `bcabec22a8bb8f5fc2ff7accdef9dd6cded73dde42f8976f6467e93d605c307c`

## Acceptance limits
This repair has **not** been verified in DOM, native Windows, a rebuilt package or Gemma/another real provider. Prior packaged-candidate evidence belongs to the earlier candidate and cannot certify this changed prompt. A fresh local package/provider check remains required. The reserved semantic weakness and previously open installation, launcher and accessibility gates remain open. No full-suite, merge, release or deployment claim is made. CI is intentionally skipped.
