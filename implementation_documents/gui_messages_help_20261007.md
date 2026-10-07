# React messages and help requests · 2026-10-07

## Delivered scope

- `/mensajes`: inbox, sent and archived folders, URL search and selected detail, exact-ID reply/compose, role/name/username contact search, visible-result selection, read/unread, archive/unarchive, and confirmed permanent deletion. Bulk operations report each confirmed result, stop on the first unconfirmed operation, and require a refresh before another bulk action.
- `/ayuda`: student request list and request creation. `/solicitudes` exposes the same authorized queue for staff. `/solicitudes/:requestId` reads the authorized list and locates the request because the existing API has no request-detail GET endpoint.
- Help list search, status and priority filters persist in the URL and return link. Detail includes actual open/resolved status, priority, student ID, course/material links and available question context.
- Staff response text, AI proposal and resolution notes are separate. Sending a response posts a classroom message to the request's numeric `student_id`. Resolving posts JSON `{ "notes": string | null }`; the backend persists `resolution_notes`. Neither operation silently performs the other.
- Contextual creation accepts positive `content_id`, `study_plan_id`/`plan_id`, explicit `session_id` and `question_id`. A supplied session requires material context. `from_session=1` is a legacy origin flag and is never interpreted as a session ID. Context is rechecked through the read-only AI context endpoint; creation does not require an online teacher or a provider call.
- The standalone tutor and personal Q&A are owned separately at `/tutor`. Help requests link there without presenting the queue as a replacement for tutor functionality. Existing contextual `LearningHelp` was not modified or duplicated.

## Verified API behavior retained

| Operation | Actual contract and user-facing meaning |
|---|---|
| Contacts | `/api/classroom/users?limit=100&search=...&role=...`; only server-authorized active contacts, with server visibility filtering before the limit. Search can reach contacts outside the original response window. Selection uses numeric ID, including homonymous people. |
| Messages | `GET /api/classroom/messages?folder=inbox|sent|archived`, `POST /api/classroom/messages` with `recipient_id`, `subject`, `body`. A returned message must match owner, recipient and exact contents before send success is displayed. |
| Message state | `POST /read`, `/unread`, `/archive`, `/unarchive` on each message. Archive state is shared by sender and recipient, not an invented per-account archive. |
| Delete | `DELETE /api/classroom/messages/:id` permanently removes the shared record for both participants. The confirmation explains this. There is no trash, undo or recoverable-delete claim. |
| Help creation | `POST /api/classroom/help` preserves a `client_request_id` across explicit identical retries. Edits cannot silently reuse that request identity. Creating a different request after uncertainty requires an explicit choice. |
| Resolution | `POST /api/classroom/help/:id/resolve` with JSON `notes`. Omission/null preserves existing notes. The GET response does not expose resolution notes, a response-message ID, unread status or responder metadata, so none is fabricated. |
| AI draft | Explicit `/api/ai/chat` when authorized source context exists; otherwise `/api/ai/answer-question`. Source version, assistance policy, request identity and receipt are validated. An AI draft remains a proposal until explicitly applied, and applying over existing response text is confirmed. |
| AI interruption | Explicit retry uses the same captured request/ID. Cancellation suppresses local delivery and does not promise provider termination or zero cost. Preparing another request is separate and warns about possible additional cost. No request starts during initial render, refocus, refresh or reauthentication. |

## Buffers, privacy and migration

The old `inbox.js` composer used DOM fields and module-level recipient/selection state. The old dashboard help form used DOM fields and an in-memory pending request identity; staff response and resolution text also lived in DOM fields. These paths had **no localStorage/sessionStorage draft schema** to import. The old dashboard's theme/language storage is unrelated.

The React composer, request form, staff response, resolution notes and AI proposals likewise remain memory-only. The interface says that closing or reloading may lose unsent work. It does not extend the approved persistent-draft kinds, write private text to browser storage, or claim an automatic migration from open legacy tabs. Before a GUI cutover, users must finish or copy unsent text from old tabs.

Account-keyed mounts, shared scoped Query/auth/API, signal cancellation and mount/credential checks protect asynchronous continuations. Same-account reauthentication preserves hidden/inert buffers and never replays a write. Replacing the account discards the old buffer. Malformed success, network uncertainty and interrupted writes preserve text and require explicit review before another non-idempotent send. Confirmed writes remain confirmed even if a subsequent read refresh fails.

## Deliberate UI differences and remaining cross-domain parity

- Reading a message detail does not automatically mark it read. Explicit Read/Unread controls expose the existing API operations; this avoids a mutation merely from a restored URL. The legacy inbox marked messages read when expanding them. If automatic read-on-open is required for retirement, it remains a product parity decision and must be tied to an explicit user opening action, never a route render/revalidation.
- Inbox search and bulk selection now operate on the actual subject/body/name fields and current visible folder/results. The old code's selectors and global selection could produce stale or hidden selections; that behavior is intentionally not reproduced.
- Legacy priority categories were normal (1), important (2), urgent (3+). The new queue exposes all five actual API values explicitly rather than flattening priorities 3–5.
- The old contact picker searched a previously limited contact response. The new picker performs an authorized server search, reports the 100-result window and preserves an explicit selected recipient ID even when outside current results. Server send policy remains authoritative.
- The global sidebar unread-count badge is shell-owned. The messages page shows per-message read state and invalidates `['messages']` after writes; shell integration can use `['messages', 'unread-count']` with `/api/classroom/messages/unread-count`.
- The People detail messaging shortcut is People-owned. Its replacement target is `/mensajes?recipient_id=<validated id>&compose=1`; the composer accepts this prefill by ID. This link was reported to the root integrator rather than editing another domain.
- The shared navigation guard currently warns on same-path query changes while dirty. Messages retains its compose buffer across folder/search/detail changes, but query-only navigation may conservatively require confirmation until the shell supplies a preserved-query policy.

## Evidence and limits

Executed with synthetic data only:

- `npm test --prefix src/frontend -- messages-contracts messages-workflows help-contracts help-workflows`: 40 tests passed on the final focused run (4 files).
- Focused ESLint: messages/help feature directories and their tests passed.
- `npm run typecheck --prefix src/frontend`: passed on the final run after concurrent integration.
- Prepared project Python, `SLM_OFFLINE_TESTS=1`, `pytest tests/trust/test_gui_api_contracts.py -k 'resolution or contacts' -q --basetemp=/tmp/slm-messages-help-pytest-20261007`: 11 passed, 15 deselected. The fixture uses disposable synthetic databases; the provider is disabled. One existing Starlette/AnyIO deprecation warning remains.

No real messages, users, provider calls, credentials or live databases were used. No backend, launcher, legacy GUI, publishing, host or GitHub Actions files were changed by this domain task.

These DOM/unit/API checks do not certify native Windows packaging, actual browser layout/zoom/focus, screen-reader operation, browser-specific BFCache/multi-tab behavior, service-worker retirement in an open dirty tab, or a live provider. Those remain integrated acceptance gates before deleting legacy source or claiming complete native/browser parity. No legacy deletion is authorized by this report.
