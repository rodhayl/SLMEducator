# Continued operational acceptance, 2026-10-04

## Reconciled starting evidence

This continuation starts from `59644dfb90504788024b65889887fbf47fd6670f`,
which is three commits ahead of the previous final receipt `ebc43ff6`.
The Windows changes preserve vendored bytes and explicit UTF-8 reads, and reject
unbundlable Tcl/Tk zipfs installations before package output is created.

The published Windows JUnit was inspected: 912 selected cases contain **889
passes, zero failures/errors and 23 skips**. Its coverage data reports **7,116 /
8,755 statements (81.28%)**. The Windows report separately records the earlier
seven failures and the limited executable/browser observations. This continuation
does not turn those partial observations into complete native acceptance.

Work is isolated on `feat/local-acceptance-recovery-20261004`; the Windows branch
and any unrelated local runtime data remain untouched.

## Operational recovery verified on Linux

A new subprocess regression seeds a disposable installation, authenticates over
real Uvicorn/loopback HTTP, imports teacher material, reviews/publishes/assigns the
course and saves an encrypted session. The CLI creates a backup, inspects and
restores it into a second installation with a different working directory, home,
configuration and JWT secret. Only the original encryption key is supplied
separately. Four original accounts can sign in; course content, private answer
keys, enrollment, unrelated-learner denial, notes and captured session revision
survive the restore.

Wrong keys, existing destinations, altered ciphertext, malformed JSON/manifests
and non-SQLite payloads preserve source/archive bytes and leave rejected
restore destinations absent. Two reproduced CLI failures were repaired:

- A JSON-list archive now yields an actionable object-format error.
- Authenticated non-SQLite payloads now yield a controlled recovery failure rather
  than an uncaught SQLite traceback.

The affected recovery gate passed **24 tests**, including **11 new operational
cases** and 13 existing portability/recovery checks. Critical lint and focused
recovery/CLI typing pass; an explicitly validated timestamp-field value is
narrowed before timestamp migration without a blanket ignore.

This is Linux source-run operational evidence, not restoration of a native
Windows executable or observation of a human operator.

## Real-browser scope and execution boundary

The cloud shell can use TCP loopback, but a fresh Chromium process cannot create
its AF_UNIX profile socket in this execution environment. Approval escalation did
not change that OS error. The managed cloud browser also reset before reaching
the local page; one reconciled retry returned an unknown-tab error. No OS security
setting was changed and no alternate host or tunnel was introduced.

A narrow isolated Chromium workflow is provided in
`.github/workflows/browser-acceptance.yml`. It runs only the new branch's relevant
changes or explicit manual dispatch. Its five cases cover:

- Teacher roster isolation, language/theme save and reload
- Learner notes, contextual help, pause/resume and next-item completion
- Preview-gated teacher export and import to a separate draft
- Keyboard focus and a narrow login viewport
- The isolated synthetic setup contract

The fixture creates its own loopback-only server and new database. Browser
requests to other hosts are blocked, service workers are disabled for this
isolated run, and all provider transport is replaced by an explicitly labelled
deterministic stub. Provider correctness, real inference, native browser zoom,
screen readers and Windows GUI acceptance are not claimed. Only synthetic
screenshots are retained as workflow artifacts; credentials and databases are
never uploaded. The setup contract passed locally; browser outcomes must be
recorded from the actual workflow run, not inferred from source/DOM tests.

## Remaining external gates

Native Tk button shutdown, manual Windows-package restoration, complete
Chrome DevTools/native accessibility acceptance, the user's configured real
provider and an authorized human pilot remain separate. This continuation does
not install a large model or consume paid inference. No merge or deployment.


## First real-browser run

Run `37223476147` on `0162b82e` executed real Chromium successfully: four cases
passed. Teacher roster isolation and saved English/dark preferences, learner
notes/help/pause/resume/next completion, narrow keyboard login and fixture setup
were exercised. The fifth case downloaded the teacher package but the harness
then attempted import without selecting the visible Import purpose. That hidden
panel timeout is retained as a test-harness failure, not reported as an application
defect. The harness now clicks the purpose control and verifies the import panel
is visible before uploading. Its complete rerun remains required.
