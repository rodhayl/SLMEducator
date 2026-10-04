"""Create-only encrypted SQLite backup/restore without implicit key generation."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time

from cryptography.fernet import Fernet, InvalidToken

BACKUP_FORMAT = "slmeducator-private-backup"
BACKUP_VERSION = 1
MAX_DATABASE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 192 * 1024 * 1024
ENCRYPTED_COLUMNS = {
    "contents": "content_data", "study_plans": "content_metadata",
    "assessment_questions": "correct_answer", "question_responses": "response_text",
    "ai_model_configurations": "api_key",
}


def key_fingerprint(key: bytes) -> str:
    """Identify a required key without returning or saving the key itself."""
    Fernet(key)  # Validate the supplied key before touching a database.
    return sha256(key).hexdigest()


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _read_connection(path: Path):
    source = path.resolve(strict=True)
    if not source.is_file():
        raise ValueError("Database source must be an existing regular file")
    return sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)


def snapshot_database(source: Path, destination: Path) -> None:
    """Capture committed WAL data without changing the source database rows."""
    deadline = time.monotonic() + 30

    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError("Database snapshot timed out; retry when writers are idle")

    with closing(_read_connection(source)) as original, closing(sqlite3.connect(destination)) as snapshot:
        original.backup(snapshot, pages=256, progress=progress, sleep=0.1)
        snapshot.execute("PRAGMA journal_mode=DELETE")
        if snapshot.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("Database snapshot failed its integrity check")
    if destination.stat().st_size > MAX_DATABASE_BYTES:
        raise ValueError("Database exceeds the supported 128 MB backup limit")


def inspect_database(path: Path, key: bytes | None = None) -> dict:
    """Report schema/counts and verify encrypted fields with a supplied key."""
    with closing(_read_connection(path)) as connection:
        if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed")
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        columns = {table: [row[1] for row in connection.execute(f"PRAGMA table_info({_quote(table)})")]
                   for table in tables}
        counts = {table: connection.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0] for table in tables}
        if key is not None:
            cipher = Fernet(key)
            for table, column in ENCRYPTED_COLUMNS.items():
                if column not in columns.get(table, []):
                    continue
                for row in connection.execute(f"SELECT {_quote(column)} FROM {_quote(table)} WHERE {_quote(column)} IS NOT NULL"):
                    value = row[0]
                    if isinstance(value, str) and value.startswith("gAAAA"):
                        try:
                            cipher.decrypt(value.encode())
                        except InvalidToken as error:
                            raise ValueError("The supplied key does not decrypt the database") from error
        schema = sha256(json.dumps(columns, sort_keys=True).encode()).hexdigest()
        return {"table_count": len(tables), "row_counts": counts, "schema_fingerprint": schema}


def backup_preview(key: bytes) -> dict:
    """Describe the private archive's scope before an administrator downloads it."""
    return {"audience": "private_backup", "format": BACKUP_FORMAT,
            "key_fingerprint": key_fingerprint(key),
            "includes": ["all database accounts, roles and enrollment", "course content and grading assets",
                         "student work, notes and messages", "encrypted provider credential records"],
            "excludes": ["encryption key", "JWT signing secret", "local configuration files",
                         "uploaded files stored outside the database"],
            "warnings": ["Keep this private archive and the original encryption key separately.",
                         "Restore requires the matching key and always creates a new database file.",
                         "This is a database backup, not a copy of the complete installation."]}


def create_backup(source: Path, key: bytes) -> bytes:
    """Create an encrypted database snapshot; no plaintext archive is published."""
    fingerprint = key_fingerprint(key)
    with tempfile.TemporaryDirectory(prefix="slm-backup-") as folder:
        snapshot = Path(folder) / "snapshot.db"
        snapshot_database(source, snapshot)
        metadata = inspect_database(snapshot, key)
        raw = snapshot.read_bytes()
    archive = {"format": BACKUP_FORMAT, "version": BACKUP_VERSION,
               "created_at": datetime.now(timezone.utc).isoformat(), "key_fingerprint": fingerprint,
               "database_sha256": sha256(raw).hexdigest(), "database_bytes": len(raw),
               "database": Fernet(key).encrypt(raw).decode(), "summary": metadata}
    return json.dumps(archive, sort_keys=True).encode()


def write_new(path: Path, data: bytes) -> None:
    """Write a new file with restrictive permissions and never clobber a target."""
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def restore_backup(archive_bytes: bytes, destination: Path, key: bytes) -> dict:
    """Verify key, archive and SQLite before writing a new restore destination."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Restore destination already exists; choose a new path")
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("Backup archive exceeds the supported size")
    archive = json.loads(archive_bytes)
    if archive.get("format") != BACKUP_FORMAT or archive.get("version") != BACKUP_VERSION:
        raise ValueError("Unsupported backup format/version")
    if archive.get("key_fingerprint") != key_fingerprint(key):
        raise ValueError("Encryption key fingerprint mismatch; original key required")
    try:
        raw = Fernet(key).decrypt(archive["database"].encode())
    except (InvalidToken, KeyError, AttributeError) as error:
        raise ValueError("Backup decryption/integrity check failed") from error
    if len(raw) > MAX_DATABASE_BYTES or len(raw) != archive.get("database_bytes"):
        raise ValueError("Backup database size mismatch")
    if sha256(raw).hexdigest() != archive.get("database_sha256"):
        raise ValueError("Backup database digest mismatch")
    with tempfile.TemporaryDirectory(prefix="slm-restore-") as folder:
        candidate = Path(folder) / "candidate.db"
        write_new(candidate, raw)
        summary = inspect_database(candidate, key)
        if summary != archive.get("summary"):
            raise ValueError("Backup schema or row-count manifest mismatch")
    write_new(destination, raw)
    return summary


def upgrade_database(source: Path, destination: Path, backup_path: Path, key: bytes) -> dict:
    """Back up and reconcile a NEW database, preserving the source installation."""
    source, destination, backup_path = Path(source), Path(destination), Path(backup_path)
    if destination.exists() or backup_path.exists():
        raise FileExistsError("Upgrade destination and backup must both be new paths")
    if destination.resolve() == backup_path.resolve():
        raise ValueError("Upgrade database and backup must use different paths")
    archive = create_backup(source, key)
    write_new(backup_path, archive)
    restore_backup(archive, destination, key)
    from src.core.services.schema_migrations import reconcile_database
    try:
        changes = reconcile_database(destination)
    except Exception:
        # The unchanged source and verified backup remain available. The failed
        # destination is retained for inspection and is never silently promoted.
        raise
    return {"backup": str(backup_path), "database": str(destination), "changes": changes,
            "summary": inspect_database(destination, key)}
