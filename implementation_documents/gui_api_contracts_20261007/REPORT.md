# Minimal GUI API contract repairs · 2026-10-07

## Verified milestone

The approved minimal backend changes are implemented in the isolated redesign source tree. The new real-router/disposable-SQLite contract suite passes **26/26**. A broader affected regression run passes **181/181**; the final test-only expansion subsequently adds the passing-score case and learner-feedback assertion. No external inference, installed-user data, host/security changes, Actions, publication, or schema migration was used.

This is a backend milestone, not completion or visual acceptance of the entire GUI replacement.

## Exact implementation ownership

- `src/api/routes/study_plans.py`: preserve real zero averages and zero passing rates; reject a topic outside the authorized course; filter topic-grade assessments by both topic and course. Remove one pre-existing unused import for focused lint.
- `src/api/routes/dashboard.py`: absence of any finalized grade is `null`; an actual zero remains `0`. Wrap one pre-existing overlong line for focused lint.
- `src/api/routes/classroom.py`: JSON resolution DTO and durable notes; existing contact authorization before search and limit; deterministic ID tie-break for names.
- `src/api/routes/assessment.py`: preserve a teacher's zero ahead of a stale AI suggestion in provisional totals; additive capability and persisted attempt-timing read fields.
- `tests/trust/test_gui_api_contracts.py`: offline API/database regression coverage.

`changes.patch` contains exactly these owned edits and the new test file, relative to the captured pre-work source. Its dry-run applies cleanly to that source. Concurrent course-worker additions of `creator_id` to course DTOs are excluded from the patch. `file_hashes.json` records the combined source files tested, including those independently owned course additions.

No `auth.py`, frontend, badge endpoint, policy, database model, migration, AI-provider, or service-selection code was edited by this work.

## Characterized gaps and contracts

1. Course/topic summaries used truthiness and returned `null` for an actual zero average or zero passing rate. They now distinguish absent, zero, and positive values. Teacher dashboard absence also remains unknown rather than becoming an invented zero.
2. Help resolution accepted query notes while the UI sends JSON. `POST /api/classroom/help/{id}/resolve` now accepts `{ "notes": "..." }`. JSON takes precedence when a body is present; omitted/null notes preserve existing text; an empty string clears it. Legacy no-body/query requests remain compatible, with the query parameter marked deprecated. Authorization, resolution authorship, existing response shape, and separation from sending a message are unchanged. Resolution text is not newly exposed through list responses.
3. Contact search previously limited before checking `can_message`, allowing inaccessible users to exhaust the result window. Existing policy now determines candidate IDs before role/search/limit. This preserves explicit/legacy enrollment, administrator scope, inactive/self exclusions, and message-send boundaries. It reuses the policy rather than inventing a second authorization model. It is not a new scalable directory/pagination architecture.
4. Student-detail badges are a frontend actor-selection defect: `/api/gamification/badges` already correctly refers to the signed-in actor. A regression proves that supplied `student_id` cannot change the actor. No third-party badge endpoint was added. The frontend owner must omit the misleading card, per the approved plan.
5. Topic grades authorized the course without checking topic membership, then aggregated across all courses using that topic. A foreign private topic could therefore expose its grade aggregate through an unrelated owned course. Membership now accepts the direct course association or explicit course-content link, and aggregation is course-bound. A cross-plan isolation regression covers both mismatched and legitimately linked topics.
6. A provisional AI total used `score or suggestion`, replacing a recorded teacher zero with a stale positive suggestion. Explicit `None` checks preserve the human grade. The test enters via the real submission API with a synthetic detached provider and an overlapping persisted teacher score. AI remains provisional; no real provider is contacted.
7. Assessment summary/create/update/detail DTOs now include `can_manage: bool`, calculated by the existing author/admin policy. This is presentation capability metadata, not replacement authorization.
8. Submission-detail GET now includes `started_at`, `expires_at`, `timing_provenance`, and `time_limit_minutes`. GET and explicit start share a timing serializer. Start is the persisted value; expiry exists only when the current frozen assessment limit and a known-offset start establish it. Naive legacy start values stay naive with `legacy_unknown` and no invented expiry. Repeated GET does not reserve, start, close, or consume an attempt. Authorship after learner reassignment and learner-hidden answer keys remain protected.

## Evidence

- **Expected FAIL, pre-repair characterization:** 15 failed / 6 passed. `characterization_red.txt` names every reproduced failing case.
- **PASS, final focused contracts:** 26 passed, one dependency deprecation warning; `contracts_final.txt`.
- **PASS, affected regression set:** 181 passed, one dependency deprecation warning, 188.18 seconds; `regressions.txt`.
- **PASS, focused flake8:** all four edited backend files and the new test file, with the repository config.
- **PASS, patch dry-run:** all four source paths and new test path apply to the captured baseline.
- **FAIL, configured mypy:** eight existing dependency errors, byte-for-byte identical before/after; `mypy_baseline.txt` and `mypy_final.txt`. Repository configuration ignores route-module errors; this command must not be described as independent strict typing of these routes.
- **NOT RUN here:** whole-codebase test/coverage gate, React/browser/visual acceptance, Windows executable/installer, real model/provider quality, remote publication/CI.

All commands used the existing interpreter `/workspace/scratch/1e4fc9d3fe09/slm-best-effort-6109-20261006/.venv/bin/python`. Test commands set `SLM_OFFLINE_TESTS=1 USE_REAL_AI=0`; the repository fixture blocks real HTTP transports. Databases were synthetic disposable fixtures.

Final focused command:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 "$PYTHON" -m pytest tests/trust/test_gui_api_contracts.py -q --basetemp=/tmp/slm-gui-api-final-20261007
```

Affected regression command:

```sh
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 "$PYTHON" -m pytest tests/trust/test_gui_api_contracts.py tests/integration/test_trustworthy_scoring_sessions.py tests/trust/test_resource_contracts.py tests/trust/test_temporal_contract.py tests/trust/test_assessment_revision_contract.py tests/core/test_classroom_messages.py tests/features/test_help_queue.py tests/features/test_gamification_mastery_annotations.py tests/integration/test_dashboard_studyplan_assessment.py -q --basetemp=/tmp/slm-gui-api-regression-20261007
```

## Pending codebase typing cleanup (unchanged by this patch)

These remain pending in the parent task's final completion scope; they were deliberately not folded into this bounded repair.

| Owning file | Line | Exact mypy error |
|---|---:|---|
| `src/core/services/assessed_review.py` | 19 | `"Mapped[Any]" has no attribute "topic_id" [attr-defined]` |
| `src/core/services/assessed_review.py` | 40 | `Unsupported operand types for * ("int" and "None") [operator]` |
| `src/core/services/assessed_review.py` | 40 | `Unsupported operand types for / ("int" and "None") [operator]` |
| `src/core/services/assessed_review.py` | 59 | `Item "None" of "User | None" has no attribute "settings" [union-attr]` |
| `src/core/services/assessed_review.py` | 63 | `Item "None" of "User | None" has no attribute "settings" [union-attr]` |
| `src/api/policies.py` | 55 | `Argument 2 to "teacher_student_ids" has incompatible type "int | None"; expected "int" [arg-type]` |
| `src/api/policies.py` | 126 | `Argument 2 to "teacher_student_ids" has incompatible type "int | None"; expected "int" [arg-type]` |
| `src/api/policies.py` | 172 | `Argument 2 to "teacher_student_ids" has incompatible type "int | None"; expected "int" [arg-type]` |
