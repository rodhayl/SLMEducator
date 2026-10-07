# Migration and recovery guide

The maintained procedure is [Course portability and database recovery](PORTABILITY_RECOVERY.md).
Use its copy-first, encrypted backup and create-only restore/upgrade flow for an
existing installation. Do not delete or reset the original database to recover
access, resolve schema errors or replace an encryption key.

## Before changing an installation

1. Identify the explicit source database path, original encryption key and local
   configuration. Keep the key private and securely retained separately from the
   backup; never print it, paste it into an issue or write a plaintext key dump.
2. Use the original managed key as `SLM_ENCRYPTION_KEY` in the recovery process.
   Follow the [key-handling instructions](PORTABILITY_RECOVERY.md#preserve-the-original-encryption-key)
   without exposing its value. Recovery does not discover or generate a key.
3. Save pending application work. Create destination directories and choose new,
   unused output filenames. Protect backups and restored databases as private
   information. Archive uploaded files and required configuration separately;
   the database archive does not include them, the encryption key or JWT secret.

## Back up, restore and verify

Run from a prepared source checkout, replacing these example absolute paths with
operator-selected paths. Existing output files and symlinks are refused.

```powershell
.\venv\Scripts\python.exe scripts\recover_database.py backup --database C:\SLM\slm_educator.db --output C:\Backups\before-upgrade.slmbackup
.\venv\Scripts\python.exe scripts\recover_database.py restore --backup C:\Backups\before-upgrade.slmbackup --output C:\SLM-Recovered\restored.db
.\venv\Scripts\python.exe scripts\recover_database.py inspect --database C:\SLM-Recovered\restored.db
```

SQLite's online backup API captures committed WAL data in a consistent snapshot;
a plain copy of only a live `.db` file can miss it. The backup may manage source
SQLite sidecars/read marks but does not change source rows. Uncommitted work is
excluded. Restore verifies the archive and matching key before creating a new
database. Keep the source and verified backup available until the new copy has
been checked and deliberately accepted.

## Upgrade an existing schema

If startup reports an incomplete or unstamped schema, use the explicit
[copy-first schema upgrade](PORTABILITY_RECOVERY.md#explicit-schema-upgrades):

```powershell
.\venv\Scripts\python.exe scripts\recover_database.py upgrade --database C:\SLM\slm_educator.db --output C:\SLM-Upgraded\upgraded.db --backup C:\Backups\pre-upgrade.slmbackup
.\venv\Scripts\python.exe scripts\recover_database.py inspect --database C:\SLM-Upgraded\upgraded.db
```

Upgrade verifies an encrypted backup, restores into a new path and reconciles
compatible additions there. It preserves source rows and account security state;
it does not infer destructive schema changes or recover a lost encryption key.
Leave legacy timestamp values unchanged unless the source timezone is independently
known for each explicitly selected field. See the detailed recovery guide for
limits, timestamp provenance and failure handling.

After verification, stop the old application before deliberately selecting the
new database through `SLM_DB_PATH`. Configure the original encryption key in that
runtime and verify expected records and sign-in behavior. The CLI does not switch
databases automatically. A failed new copy is never a reason to delete the source.

## Credentials and session secrets

An encryption key must match the records it protects. Generating a new key cannot
recover old ciphertext. If the original key is unavailable or a validation fails,
stop and arrange an administrator-reviewed recovery; preserve the original files.
Do not share databases, keys, tokens or private configuration in support reports.

Preserve the installation's managed JWT secret separately when appropriate;
changing it invalidates existing signed sessions. Signing in again does not repair
encrypted data. Bootstrap credentials are create-only and do not reset existing
accounts. Use the authenticated password-change flow or an explicit administrator
recovery procedure, as described in the [project README](../README.md#initial-admin-account).

Synthetic recovery tests exercise disposable data. They do not establish native
Windows acceptance or recovery of a real installation.
