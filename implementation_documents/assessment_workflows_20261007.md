# Assessment and grading React migration

Date: 2026-10-07. Task-local implementation; no publishing, provider calls, native build, or legacy deletion.

## Implemented paths

- `/evaluaciones`: role-aware list and retained URL filters
- `/evaluaciones/nueva`, `/evaluaciones/:assessmentId/editar`: shared React Hook Form editor, accessible question/choice/criterion rows and ordering, explicit draft save, policy save, reviewed publication and preview
- `/evaluaciones/:assessmentId`: learner preflight or read-only staff preview; GET never reserves attempts
- `/evaluaciones/historial`, `/evaluaciones/:assessmentId/historial`, `/envios/:submissionId`: own submission history/results, including real zero and terminal closure
- `/intentos/:submissionId`: persisted attempt GET reload, server deadline, exact-owner/resource/attempt drafts, explicit restore/discard, review, confirmed submit/close, uncertainty reconciliation
- `/correcciones`, `/correcciones/:submissionId`: author-scoped queue with URL filter, question/total grading and reviewed AI suggestions

Route registration and safe-return-path integration belong to the foundation worker. Both locale catalogs are complete and all pages use shared auth, resource/mutation transport, controls, errors, content sanitization, draft, time, and dirty-navigation adapters.

## Important contracts

- Staff preview cannot reserve student attempts or earn XP. Enrollment visibility never grants assessment editing or grading: the server's `can_manage` is checked for both.
- Resume/history load persisted timing via GET. Offset-free timestamps retain unknown provenance; the UI never restarts a timer. Expiry explains server review behavior and does not automatically replay a mutation.
- Blank grading input is not zero. Last-question saves explicitly announce immediate finalization; total save and accepting all AI suggestions also require confirmation.
- A local draft is labeled local and unsubmitted. Unknown mutation responses preserve inputs; the confirming portal closes so it cannot bypass reconciliation. Same-account reauth preserves mounted inputs but does not replay mutations; another account gets a new private scope.
- New choices use `{choices: {value: label}}`. Historical arrays and raw dictionaries retain their original submitted text semantics. Values and display labels remain independent; labels can contain commas.

## Narrow backend additions

`src/api/routes/assessment.py` now exposes safe `options_supported` compatibility metadata and author-only per-question `rubrics` and `content_metadata`. Create/update preserve these authoring assets; global rubric serialization excludes question-linked rubrics. A legacy client that replaces rich questions without explicitly carrying these assets is rejected before mutating fields. Student question reads expose no answer key, rubric, explanation, hints, or opaque metadata.

`options_supported=false` identifies a stored key that cannot match offered legacy values. React blocks start/submit and requests author review rather than inventing a letter-to-position mapping. Existing stored answers, grades, and backend comparison semantics are unchanged. Real synthetic API tests demonstrate that array `['3','4']` with key `'4'` grades text `'4'` correctly, whereas a key `'B'` historically does not. Raw maps have the same historical text behavior. New nested keyed choices submit the key explicitly.

The pure `generatedAssessmentValues` adapter and `AssessmentProposalEditor` are exported for package previews. They preserve question rubrics, explanation/hints and unknown metadata; they do not guess ambiguous answer keys. `onDirtyChange` allows the containing authoring page to aggregate its guard, and `onSaved` reports the confirmed draft identity. The caller must key the editor by proposal identity.

## Maintained tests and verification

- `tests/frontend/assessments-contracts.test.ts`: contract validation, choice semantics, zero/null, exact drafts, timestamps, mutation receipts, immutability, bilingual keys, opaque asset fidelity and generator adaptation
- `tests/frontend/assessments-workflows.test.tsx`: learner/staff workflows, ES/EN grading, no start on read, reauth/account switch, dirty guard, uncertainty, single flight, policy gates and unsupported legacy definitions
- `tests/frontend/assessments-fixtures.ts`: synthetic shared fixtures only
- `tests/trust/test_assessment_authoring_fidelity.py`: actual generator-persistence -> author GET -> edit -> copy -> GET preservation, student privacy, legacy scoring characterization, and lossy-client rejection

Verified backend gate: 82 passed across authoring fidelity, assessment revision, assistance policy and trustworthy scoring/session suites, with `SLM_OFFLINE_TESTS=1` and disposable test directories. One pre-existing Starlette/AnyIO deprecation warning.

Focused frontend tests: 46 cases. Focused ESLint and full flake8 for the changed assessment API/test files pass. Root aggregate checks remain separate; the most recent global typecheck was temporarily blocked only by an in-progress authoring test signature mismatch outside this scope, already reported to that owner. Earlier global typechecks passed after assessment implementation.

Browser visual acceptance, final aggregate checks, packaged runtime and native validation are not claimed here and remain the parent's integration responsibility.
