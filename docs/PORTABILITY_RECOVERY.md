# Course portability and database recovery

Use demonstration data when evaluating these workflows. Never distribute a
private database backup or teacher answer package as a learner handout.

## Three distinct audiences

- **Learner handout:** authorized course text, practice prompts/options and
  published assessment questions. It excludes answer keys, grading rubrics,
  teacher generation/review state and all account/student records. A handout is
  not an importable teacher course package.
- **Teacher course package:** the author's reusable course structure, ordered
  content, executable assessment definitions, encrypted-at-rest answer keys
  decrypted for the package, question/assessment rubrics and useful generation
  context. The downloaded JSON contains answers in plaintext. It excludes
  accounts, credentials, learner assignments, submissions, notes and messages.
- **Private database backup:** an administrator-only encrypted SQLite snapshot,
  including accounts, enrollment, work and provider credential records. The
  backup never contains the encryption key, JWT secret, local configuration or
  uploaded files outside the database. It is not a full installation image.

The portability page previews counts, inclusions, exclusions and warnings before
an explicit export/import/backup action. Browser responses use `no-store` and a
native download; no file is automatically shared with another account or service.
A teacher package imports as a **new private draft owned by the importing
teacher**. Publication/assignment approvals are reset. IDs, prerequisites,
linked assessment IDs, book chapters and question-scoped rubrics are remapped; phase/item order
and saved source/generation context are preserved where it references included
items. Import validation and the database savepoint prevent partial courses.

## API

All routes require authentication.

- `GET /api/portability/plans/{id}/preview?audience=learner|teacher`
- `GET /api/portability/plans/{id}/export?audience=learner|teacher`
- `POST /api/portability/import/preview`, JSON `{"package": {...}}`
- `POST /api/portability/import`, JSON `{"package": {...}, "confirm": true}`
- `GET /api/portability/backup/preview` (administrator)
- `POST /api/portability/backup`, JSON `{"confirm": true}` (administrator)

Import bodies are limited to 10 MB while streaming, before JSON decoding. The
private backup supports database snapshots up to 128 MB and archive inputs up to
192 MB. There is deliberately no web endpoint for overwriting a running database.

## Preserve the original encryption key

Before moving installations, securely retain the original key separately from
the archive. The backup preview/manifest contains only a SHA-256 key fingerprint.
The recovery CLI requires `SLM_ENCRYPTION_KEY` to be supplied explicitly; it does
not create, discover or print a replacement key. A missing, mismatched or invalid
key stops recovery. Invalid ciphertext, size/digest mismatches and changed schema
or row-count manifests also stop recovery before creating the destination.

On Windows, an operator who manages the installation can load an existing key
into their current PowerShell process without printing it:

```powershell
$env:SLM_ENCRYPTION_KEY = (Get-Content -Raw "$HOME\.slm_educator\encryption.key").Trim()
```

If the installation uses a different key location or an environment-managed key,
use that existing managed key instead. Do not paste keys into messages or save
them in repository commands. Losing this original key can make encrypted data
unrecoverable; a new key with the same database filename does not recover it.

## Backup and restore to a new path

Use an explicit source database and unused destination filenames:

```powershell
.\venv\Scripts\python.exe scripts\recover_database.py backup --database C:\SLM\slm_educator.db --output C:\Backups\before-upgrade.slmbackup
.\venv\Scripts\python.exe scripts\recover_database.py restore --backup C:\Backups\before-upgrade.slmbackup --output C:\SLM-Recovered\restored.db
.\venv\Scripts\python.exe scripts\recover_database.py inspect --database C:\SLM-Recovered\restored.db
```

Destination directories must already exist. Existing output files, including
symlinks, are refused. SQLite's online backup API captures committed WAL data;
it may manage SQLite sidecars/read marks on the source, but does not change source
rows. Uncommitted work is excluded. Credentials and grading assets remain inside
the encrypted archive; a restored database contains the original stored records.
Protect the restored database as private information.

After verification, stop the old application before deliberately selecting the
new file with `SLM_DB_PATH`. Configure the original encryption key in that runtime.
Back up needed uploads and local configuration separately; the database archive
cannot reconstruct files it explicitly excludes. The CLI does not switch the
application to the restored database or alter the original installation.

## Explicit schema upgrades

`create_all` cannot reconcile an existing table's missing columns. Startup now
refuses an incomplete model schema with an actionable upgrade message, rather
than launching into missing-column failures or silently changing existing data.
Use the copy-first upgrade workflow:

```powershell
.\venv\Scripts\python.exe scripts\recover_database.py upgrade --database C:\SLM\slm_educator.db --output C:\SLM-Upgraded\upgraded.db --backup C:\Backups\pre-upgrade.slmbackup
```

The command first verifies an encrypted backup, restores it into a new database,
then adds missing compatible tables/columns and indexes. Existing source rows
and account security state stay unchanged. Safe defaults come from current model
scalar defaults; missing required identity fields with no safe defaults stop the
upgrade. Unknown migration revisions stop reconciliation. The source and verified
backup remain available even if the new copy cannot be reconciled.

A successful copy is stamped `20261004_reconcile` only after model fields and
SQLite integrity checks pass. Unstamped legacy `create_all` installations must
use this workflow; directly applying the historical first Alembic migration can
conflict with pre-existing tables. Destructive downgrade is intentionally refused:
restore the verified pre-upgrade backup into a new path instead. Existing column
meaning/type changes that need a bespoke migration are not inferred by this
additive reconciliation tool.

## Validation boundary

Focused synthetic tests cover learner/teacher field exclusions, owner scope,
question keys and rubric round-trip, phase/reference remapping, transaction
rollback, WAL capture, matching-key restore, tampered archive rejection,
create-only destinations, startup schema refusal and explicit schema upgrade.
The tests do not establish a native Windows packaged build, a backup of external
uploads, or operational recovery from a real school's private installation.
