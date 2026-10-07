# Functional continuation after the React source checkpoint

2026-10-07. Base commit: `1ae599904666237f08939a72f570e6f98abfad0a`, tree `8b3d3b0a046d83d594bb4cdfba5c4c849c12e59f`.

This is a bounded independent functional/static review and repair checkpoint. It is not a release, installer, completed security audit, or completion of the requested three whole-codebase reviews. The original checkpoint's **one completed whole-codebase review** remains the historical count; the incomplete second review and pending third review are not relabelled by this continuation.

## Result

- Frontend gate after the legacy-body follow-up: **791 tests passed across all 49 files**, plus TypeScript, ESLint and the canonical production build, exit 0. The test phase took 79.49 seconds. All **181** frozen frontend source/test/tooling/documentation entries remained unchanged through verification.
- Final, deduplicated affected Python gate: **344 passed, 13 skipped, zero failures/errors**, exit 0 in 81.91 seconds. This is a selected functional gate, not the full Python aggregate. All **464** recovered source/test/documentation files in its frozen manifest remained unchanged. Its exact node selection is recorded in [coverage accounting](FUNCTIONAL_COVERAGE.json).
- The 13 skips require real Windows `cmd`/`CHOICE`. One existing third-party Starlette/AnyIO deprecation warning remains visible.
- Canonical build: **26 local assets and 29 dependency license records**. Python separately validated the final dist against the current source and npm lockfile. Source digest: `a5e98d493db9216f246fed7e6b4ac0d77e234f5e3c0602465b87e02fd878f624`. Generated dist and dependency trees are not source-publication inputs.
- Final critical Python lint (`E9,F63,F7,F82`) passed all ten changed Python source/test files. Focused mypy passed the three changed scripts. Portability's **59 pre-existing typing errors** match the preserved baseline after line-number normalization; API-route typing is ignored by the existing configuration, so no API typing pass is claimed. Full focused lint still reports the same two pre-existing long prompt lines in `ai.py`.

## Repairs

1. **Fresh-checkout dependency resolution.** The documented frontend-local npm install previously left repository-level tests unable to resolve Vitest, React and testing dependencies. The ordinary check failed before collection and TypeScript reported missing modules. Test-only Vite aliases and TypeScript lookup paths now use the same locked frontend dependencies. No repository-root package installation, dependency symlink, new dependency or production resolver rewrite is needed.
2. **Course continuation.** A saved location pointing at an already completed lesson no longer overrides the next unfinished item. A finished course no longer offers that completed marker as Continue. An actual active session keeps precedence.
3. **Legacy lesson snapshots.** Distinct body text is retained when historical stored snapshots also have structured sections. Selection takes the first nonblank string from content, body and text, so whitespace or truthy non-string legacy fields cannot mask usable fallback text. Source clarifications remain first, and canonical flattened body text is not repeated. Modern normalized API content was already protected; the repair addresses the legacy-snapshot shape.
4. **Generation-mode changes.** Invalid hidden fields from a previous mode no longer block the current mode. Inputs transmitted to the selected endpoint retain their existing validation and payload shape.
5. **Repeated assessment edits.** Adding, removing and adding a choice now selects the next unused default value rather than duplicating an existing choice key.
6. **Tutor/Q&A usable-answer selection.** A whitespace-only or non-string optional field no longer masks a usable parser-approved answer in another supported field. Malformed optional suggestions are omitted consistently with chat. Parser/protocol failures, grading contracts and provider/model selection remain unchanged.
7. **Readable handouts.** HTML/Markdown now retain the canonical lesson worked example, independent attempt, feedback, delayed review, prerequisite check and discussion questions already present in learner JSON. Existing audience filtering and escaping are unchanged.
8. **Pilot measurements.** Each supplied authoring, correction and baseline duration is validated before addition. Boolean, negative, nonfinite or nonnumeric components cannot masquerade as valid measured time.
9. **Source startup guidance.** Manual-run instructions now invoke the same create-only administrator seeder before Uvicorn and link the explicit frontend build and one-time credential guidance.
10. **Pilot instructions.** Printed next steps now match the maintained guide's assessment-first publication order. This is a guidance consistency repair, not a reproduced blockage of the seed's exact three-lesson course.
11. **Maintained contributor references.** The guide points to current frontend/browser/native test locations and synthetic pilot/bootstrap instructions rather than retired test directories or nonexistent account files.
12. **Installer success wording.** The wrapper correctly distinguishes an explicitly supplied initial credential from one-time seeder output and no longer invents a credential handoff file/location. Build orchestration and credential storage behavior are unchanged; no real installer was compiled.

The later legacy-body follow-up added 11 synthetic cases: 10 failed against the previous selector, and the focused reading/clarification group then passed 48 cases. Valid modern content priority, clarification/objective/body ordering and canonical duplicate suppression remain covered. The earlier 780-pass frontend checkpoint is historical and is not relabelled as the current run.

Every functional repair had a failing synthetic regression before its implementation change. The tooling repair was demonstrated by the original failed canonical typecheck/test setup, then the successful canonical check. Focused red/green results are superseded by the final applicable gates above and are not added to them.

## Review coverage and limits

[FUNCTIONAL_COVERAGE.json](FUNCTIONAL_COVERAGE.json) accounts for every one of the **191** published source-tree leaves, supporting inspected files, and the executed Python selection. Methods are explicit: **172** source leaves received complete static functional reads, **9** catalog leaves received structural/type/regression review without linguistic acceptance, **1** lockfile received identity/install verification rather than dependency implementation review, **4** leaves have partial functional coverage, and **5** security/authorization/translation leaves are excluded from this independent review.

- Frontend foundations and supporting domains: routing, shared controls, ordinary authentication presentation, drafts, async result handling, help, home, messages, people, portability, progress, settings, tutoring and build tools. All 87 assigned entries are accounted for; catalog and lockfile limits above are explicit.
- Learning/teaching domains: all 40 assessment, authoring, course and learning feature entries, plus 23 matching test/fixture files were inspected. Synthetic tests cover ordinary repeated edits, interrupts, result certainty, navigation, recovery, locale cases and role flows. Code reading is not proof every behavior executed.
- Backend: 46 complete API/core functional file reads, plus entry-point/export/exception/logging/configuration inspection. Model relationships, AI parsing and account/profile services have the recorded partial ranges. Authentication/encryption internals, provider-adapter/model-prompt internals and the translation investigation are not represented as complete reviews.
- Packaging/documentation: 71 explicitly listed files, including verified frontend delivery and its test/helper source. Sixty-two relative Markdown links resolve against the complete saved Git tree. Historical reports are preserved and interpreted under the original checkpoint's superseding acceptance statement. Remote links and heading anchors were not revalidated.
- Static accessibility/layout review considered labels, field/error association, focus/status affordances, responsive CSS, tables and reduced-motion rules. No painted layout, native zoom, real-browser keyboard/history, screen-reader or screenshot acceptance is claimed.

## Source recovery and retirement

After the earlier filesystem replacement, **462** active source/test/build and current-document files were recovered from the immutable source commit and verified byte-for-byte against their Git blob identities. The original frontend 759-pass and Python 1,615-pass results remain previously observed results recorded in the original checkpoint; their lost raw logs/manifests were not recovered or recreated by this work. The new results above are separately executed evidence.

The saved complete baseline and published Git trees independently reconcile the retirement set: **exactly 76** deletions, comprising the 71 retirement-manifest paths and five explicitly reviewed cache/scaffolding paths. All 71 recorded retired Git blob IDs match the baseline; zero extra deletions, zero missing retirements and zero retained mode changes were found. The original publication also retains 339 unchanged baseline leaves. This continuation adds **no deletions** and does not resurrect retired GUI code or replace historical evidence.

## Open acceptance and preserved behavior

- The previously restricted security check was not retried, reconstructed or run through another route. The preliminary Windows translation-path concern remains unverified and unresolved.
- Real-browser and service-worker lifecycle acceptance remains unrun. The earlier blocked CDP/loopback route was not retried with an alias, tunnel or alternate host.
- Native Windows GUI, zoom, command-runner, packaged startup/login, installer and recovery acceptance remain open. Mocked freezing/installer tests and Linux results cannot establish them.
- No real AI/provider calls or learning-outcome validation occurred. Model-agnostic best-effort behavior remains the goal; no model-quality perfection campaign or second-model requirement was introduced.
- The full Python aggregate and whole-source 80% coverage gate were not rerun here. No complete second or third whole-codebase audit is claimed.
- Daily-goal edits retain their explicitly documented count/completion semantics. A stored-versus-current streak display inconsistency was identified statically but not reproduced or resolved as a new contract defect; it remains a follow-up question.
- As of validation completion at `2026-10-07T19:52:22.987970+00:00`, no user database or private runtime configuration had been inspected, modified or packaged, and no credential setup, hosted Actions, installer build, remote publication, main/merge/release or deployment had occurred in this continuation. Any later source publication is a separate recorded action; this statement is limited to the validation interval.

## Evidence identifiers

Final frontend gate UTC interval: `2026-10-07T19:49:08.077316+00:00` to `2026-10-07T19:50:57.598785+00:00`. Final affected Python gate UTC interval: `2026-10-07T19:50:57.599224+00:00` to `2026-10-07T19:52:21.770419+00:00`. Built-dist identity was revalidated at `2026-10-07T19:52:22.987970+00:00`. Raw run artifacts are outside the source tree; their hashes identify these executions and do not imply permanent retention or recovery of earlier logs. Earlier 780-pass and initial 344-pass run artifacts remain separate historical records.

- `frontend-followup-check.log`: SHA-256 `c86cfeb983fb3c84af03fc98a998f7228b49c9f6ccd1374591ea3698c34f659e`
- `python-followup-affected.log`: SHA-256 `d287965a17b9e2f092b8be9d529f2510906c53525bd7371f468ac64035f08335`
- `python-followup-affected.xml`: SHA-256 `2900c3eb5ef92c7ddab15959c019c673fa374c43f9b107be6c157dafcc2f488c`
- `followup_frontend_snapshot.json`: SHA-256 `a83984081ca6ea3ff09a76b6d1966a1f05f5652cf2cb51366d48f39136f1b05e`
- `followup_source_snapshot.json`: SHA-256 `60b1b67778530f37722f79806a1aaf6f0827ce8bd9e807224d21c558f2a8b252`
- `followup-legacy-body-selection-red-v2.log`: SHA-256 `29b5b32751057494560fe4b8a29ceec155ef204d94f5c5f94b1bf4b05be641c1`
- `followup-legacy-body-selection-green.log`: SHA-256 `4c0c36bc2496de9c8ae028ceb239539f93c7f96e114ad1a53a6cff3bd2a8f5a9`

The report/accounting files were refreshed after the frozen implementation checks. No implementation or test source changed after those checks.
