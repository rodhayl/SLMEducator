# Draft and navigation migration parity

Date: 2026-10-07. Synthetic browser-storage and API fixtures only.

## Persistent draft inventory

The legacy `learning-client.js` stored owner/resource/attempt-scoped entries under `slm_draft_v1:` with a seven-day lifetime. The React `DraftAdapter` uses the same envelope and encoded key layout. Recovery remains explicitly chosen; no inference or mutation starts from a restored URL or storage entry.

| Legacy kind/resource/attempt | React recovery |
| --- | --- |
| `assessment/<assessment ID>/<submission ID>` | Active attempt recovery validates the current assessment and exact submission. Closed submission/attempt views now retain and expose a separately labelled read-only local answer copy after the server submission and account are verified. Reading a closed attempt no longer deletes the draft. |
| `practice/<content ID>/<session ID>` | Existing practice recovery accepts the legacy answer-text and hint-count arrays without requiring a newer fingerprint, then revalidates current resource access. |
| `notes/<content ID>/<session ID>` | Existing session notes recovery reads the original `{notes}` shape for the verified session. |
| `learning-location/current/0` | Existing home continuation reads the original positive numeric `planId` and `contentId`, and rechecks authorized course membership before navigation. |
| `course/designer/active` | New explicit conversion into the generation setup preserves subject, level, duration, editable outline, saved course, and selected unfinished tasks. Completed tasks remain deselected. The original entry is kept until explicit discard or its original lifetime ends. |

Pre-v1 ownerless keys such as `session_notes_*`, `notes_<id>` and `assessment_progress_*` are not imported into an authenticated account. They do not establish an owner. React leaves them untouched rather than exposing another person's work or pruning unrelated storage.

The old inbox/help/authoring editors had additional in-memory/DOM buffers, but no persistent draft schema to import. An open old tab must finish or copy that unsaved text before it is closed. This work cannot reconstruct text that was never persisted.

## Course designer conversion

- Reads only the authenticated owner's unexpired original entry.
- Revalidates every saved course reference before adopting a usable converted setup. Teacher ownership is enforced; administrator access follows the existing backend policy.
- Restores only after an explicit choice. It does not regenerate, resume a batch, replay a source write, or mark local task claims as new server receipts.
- Validates saved-course access before exposing a copyable original snapshot, and registers that resource for same-account reauthentication checks.
- Preserves the entire original designer snapshot in a labelled, copyable text area, including metadata that has no new editor control. Unsupported schemas remain available there rather than being deleted or silently narrowed.
- Preserves extracted source in the new setup. A complete supported manifest keeps its source fields. Incomplete old metadata becomes clearly described unverified authored text, with the original metadata still in the untouched snapshot.
- Blocks generation while recovered source is unsaved. Saving that source requires an explicit confirmation, fresh course/ownership/workflow/source reads, a source-version race check, and a validated save receipt. A changed or read-only course fails safely.
- If the saved course already contains the identical source text, recovery adopts the verified current source without rewriting it.
- Modern and legacy draft entries may coexist. A pending modern recovery must be resolved before choosing an older setup. Local edits cannot be overwritten by the older restore control.
- The migrated setup has the same approved draft kind, owner isolation and seven-day lifetime as other course setup drafts. It introduces no token/provider-key persistence.

## Navigation contracts

- Desktop and mobile Messages navigation share the scoped `['messages','unread-count']` query and `/api/classroom/messages/unread-count` endpoint. Message mutations already invalidate this prefix. Positive safe integer counts are shown; zero is hidden; a failed/malformed count is shown as unavailable instead of a fabricated zero or stale count.
- Legacy registration `role=student|teacher|admin` now prefills the permitted account form. Teacher-created accounts remain student-only regardless of query text. Invalid and duplicate role values do not become privileges. The delivery worker owns the old `.html` redirect's matching role allowlist.
- The `/inicio` dashboard bridge preserves old hash/view/tab precedence. A valid material with `from_session=1&ask_help=1` now routes to the contextual help-request screen, whose existing read-only context validation and explicit send flow consume the IDs. It no longer drops the request-to-open-help intent.
- Grading queue/workspace filters were already consumed. `mode=review` was also unused by the old session player; its pass-through does not authorize any start/restart mutation.
- Investigation found no old `teacher_id` registration query consumer and no `plan_id` query consumers in the old standalone course designer or portability page. No unsupported URL semantics were invented.

## Verification and limitations

Focused tests cover conversion, malformed schemas, owner isolation, original-byte preservation, saved-task selection, source confirmation, modern/legacy coexistence, denied course access, stale credentials, terminal assessment recovery, unread count validation/refresh, and role/context deep links. Existing protected-shell fixtures now model the newly required unread-count GET; domain-denial assertions still reject all domain reads while allowing that shell read.

Final frozen-source checks passed: complete frontend TypeScript; complete frontend ESLint; 670 tests across 45 files. The final focused authoring/privacy rerun also passed 58 tests across two files. The complete test output is `/tmp/slm-migration-final-frozen-tests.log` in the development workspace; this log is not shipped. These unit/DOM fixtures do not certify painted browser layout, real browser storage failures across tabs, native Windows packaging, or a live model/provider. No backend change, real data, dependency install, model run, legacy deletion, or publication was performed by this task.
