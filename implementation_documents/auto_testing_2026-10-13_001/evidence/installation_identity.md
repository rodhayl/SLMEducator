# Installed identity and package evidence

Read-only verification on 2026-10-13. No app launch, database/configuration
read, credential use, install, update, or uninstall was performed.

## Owner-reported GUI actions

The pre-existing 2026-10-12 coverage edit reports that the owner used the
native Setup GUI for build `cc0c41db8193` without elevation, then used the
first-run UI to cancel/reopen, create a synthetic first account, and confirm
that the prompt did not return on the second launch. This continuation did not
repeat those interactions. The durable owner report does not retain a process
ID, window title, or independently reviewable native screenshot.

## Current installed identity

- Registry display name: `SLMEducator 2.0.0 (build cc0c41db8193)`.
- Registry version: `2.0.0`.
- Registry install location:
  `%LOCALAPPDATA%\Programs\SLMEducator\` (per-user installation).
- Installed executable:
  `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe`.
- EXE size: `16,034,040` bytes.
- EXE SHA-256:
  `3698A0E0BDB91142658AF72261BBFC9D5853243405CD755F9FDC4745A6FA9251`.
- The executable's Windows `FileVersion` and `ProductVersion` fields were
  blank; the build/version attribution above comes from the registry entry.
- No matching SLMEducator process was running at the time of the check. The
  expected app ports were not listening.

The registry location and owner report support a per-user install claim. Folder
ACLs were not inspected, and no permission-denied test was performed.

## Setup and bundle-integrity limits

The previous campaign records
`SLMEducator-Setup-2.0.0-cc0c41db8193.exe`, 31,650,647 bytes, SHA-256
`C80E77FC7C3DA01BFC90471AFC614F6361D604AE6278BF7CFF9B02CF76A43E19`.
That hash is historical evidence from the prior campaign, not a hash
recomputed in this continuation.

A read-only inventory of `C:\builds` found older payload directories but no
matching `cc0c41db8193` Setup or output tree. Consequently this run did not
validate the current package manifest, bundled asset hashes, or a full Setup
to installed-payload chain. The installed EXE hash identifies that file; it
does not by itself prove integrity of every bundled asset or acceptance of
the installed application's workflows.

The personal installation was left intact and was not opened.
