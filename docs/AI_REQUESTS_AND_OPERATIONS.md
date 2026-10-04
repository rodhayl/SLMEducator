# Request limits and explicit account recovery

The supported local installation permits one active tutor/Q&A provider request
per account and 100 started requests per UTC calendar day. These are explicit
application policy constants, not a configurable cost budget. Lessons, notes and
teacher help remain usable when the AI ceiling is reached. Each request has a
90-second local delivery deadline. Cancelling or timing out suppresses delivery;
the provider may continue working or charging. Its active slot remains occupied
until the underlying call returns, preventing an accumulation of detached calls.

Responses include a request receipt with provider/model, elapsed time, output cap,
reported token count when available and daily usage. Unknown tokens and monetary
cost remain unknown. The server commits request claims before inference, preserves
same-ID replay briefly in memory and refuses blind duplicate inference after a
restart loses the receipt. Preparing a new request is an explicit user decision.
Policy, source revision and current resource access still govern cached responses.
This is a single-process local guard, not a distributed job queue.

Teacher-help requests have their own durable owner-scoped replay identity and
captured session revision. Retrying the same request does not create a second
queue item. Altered content with the same identity is rejected. The additive
`20261004_request_context` upgrade preserves old help rows without inventing past
source context; use the documented backup/new-copy recovery procedure.

Administrators can include inactive accounts in their lists, explicitly activate
or deactivate a selected account, and reset another account's password. The UI
identifies the account and asks for confirmation. Status actions revoke previous
sessions even when the requested active state is already set. Self-deactivation
and removing the last active administrator are refused.

Password recovery accepts a password entered by the operator; the app does not
generate, email, store in a browser draft or return a plaintext credential. The
new credential revokes earlier sessions and clears the selected account's lock.
Historical authentication attempts, including unknown legacy timestamps, remain
unchanged; an explicit audit-ID boundary distinguishes attempts before recovery.
Use the current-password change flow for your own account. If no administrator
can authenticate, use an approved operator recovery procedure; bootstrap is not a
reset and deleting the database is never an account-recovery step.

# Course transfer formats

Teacher transfer uses `slmeducator-course` JSON version 2, with a validated ordered
graph and explicit course reference, review version and source-text identity.
Version 1 remains accepted as a new private draft. Future versions are rejected
before writes. Original outline metadata is preserved separately when the ordered
link graph is canonicalized. An imported course receives its own identity and
records its source package digest; it does not inherit publication authority.

Learner HTML, Markdown and JSON handouts retain approved instructional sections,
vocabulary and visible questions while omitting hidden grading assets and raw
teacher source documents. HTML is inert escaped text with no scripts, styles or
external assets. These are reading formats, not restorations of teacher courses.
Teacher packages retain answer keys and source provenance and must be shared only
with intended instructors. Original binaries, linked media and external files are
explicitly excluded; PDF extraction is not OCR and is not complete-media import.
Private encrypted backups remain a separate operation with the original key and
a new restore destination.
