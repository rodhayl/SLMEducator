"""Synthetic copy-first timestamp conversion and rollback regression tests."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine

from src.core.services.recovery_service import restore_backup, upgrade_database
from src.core.services.temporal_migration import (
    AUDIT_TABLE,
    MIGRATION_VERSION,
    migrate_timestamps,
)
from src.core.services.temporal_service import UTCDateTime


def _database(path: Path, values: list[object]) -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE synthetic_events (id INTEGER PRIMARY KEY, occurred_at DATETIME, "
            "calendar_day DATE, payload JSON, encrypted TEXT)"
        )
        connection.executemany(
            "INSERT INTO synthetic_events (occurred_at, calendar_day, payload, encrypted) VALUES (?, ?, ?, ?)",
            [
                (
                    value,
                    "2026-01-15",
                    '{"at":"2026-01-15 08:45:00"}',
                    "SYNTHETIC-CIPHERTEXT",
                )
                for value in values
            ],
        )
    return path


def _values(path: Path) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT occurred_at, calendar_day, payload, encrypted FROM synthetic_events ORDER BY id"
        ).fetchall()


def test_default_upgrade_preserves_legacy_bytes_without_guessing(tmp_path):
    source = _database(
        tmp_path / "source.db",
        ["2026-01-15 08:45:00.123456", "invalid-but-untouched", None],
    )
    original = source.read_bytes()
    expected = _values(source)
    destination, backup = tmp_path / "copy.db", tmp_path / "before.slmbackup"

    result = upgrade_database(source, destination, backup, Fernet.generate_key())

    assert source.read_bytes() == original
    assert _values(destination) == expected
    assert "timestamp_migration" not in result
    with sqlite3.connect(destination) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = ?", (AUDIT_TABLE,)
            ).fetchall()
            == []
        )


def test_explicit_upgrade_converts_only_naive_datetimes_and_records_provenance(
    tmp_path,
):
    source = _database(
        tmp_path / "source.db",
        [
            "2026-01-15 08:45:00.123456",
            "2026-07-15 08:45:00",
            "2026-07-15 08:45:00",
            "2026-07-15 08:45:00+09:00",
            "2026-07-15T08:45:00Z",
            None,
        ],
    )
    original = source.read_bytes()
    expected_other_fields = [row[1:] for row in _values(source)]
    destination, backup = tmp_path / "copy.db", tmp_path / "before.slmbackup"
    key = Fernet.generate_key()

    result = upgrade_database(
        source,
        destination,
        backup,
        key,
        source_timezone="Europe/Madrid",
        timestamp_fields=["synthetic_events.occurred_at"],
    )

    assert source.read_bytes() == original
    assert [row[0] for row in _values(destination)] == [
        "2026-01-15T07:45:00.123456+00:00",
        "2026-07-15T06:45:00+00:00",
        "2026-07-15T06:45:00+00:00",
        "2026-07-15 08:45:00+09:00",
        "2026-07-15T08:45:00Z",
        None,
    ]
    assert [row[1:] for row in _values(destination)] == expected_other_fields
    audit = result["timestamp_migration"]
    assert audit["migration_version"] == MIGRATION_VERSION
    assert audit["source_timezone"] == "Europe/Madrid"
    assert audit["converted_values"] == 3
    assert audit["preserved_aware_values"] == 2
    assert audit["null_values"] == 1
    assert (
        datetime.fromisoformat(audit["completed_at"]).utcoffset().total_seconds() == 0
    )
    with sqlite3.connect(destination) as connection:
        connection.row_factory = sqlite3.Row
        recorded = dict(connection.execute(f'SELECT * FROM "{AUDIT_TABLE}"').fetchone())
        assert {
            name: value for name, value in recorded.items() if name != "id"
        } == audit
        assert "SYNTHETIC-CIPHERTEXT" not in json.dumps(recorded)
    restored = tmp_path / "rollback.db"
    restore_backup(backup.read_bytes(), restored, key)
    assert _values(restored) == _values(source)


@pytest.mark.parametrize(
    ("invalid", "reason"),
    [
        ("2026-03-08 02:30:00", "Nonexistent"),
        ("2026-11-01 01:30:00", "Ambiguous"),
        ("2026-02-30 09:00:00", "Invalid"),
        ("2026-01-15", "Invalid"),
        ("2026-01-15T08:45:00+00:99", "Invalid"),
        ("2026-01-15T08:45:00.1234567", "Invalid"),
        (12345, "Invalid"),
        (b"2026-01-15 08:45:00", "Invalid"),
    ],
)
def test_invalid_or_dst_uncertain_values_roll_back_every_column(
    tmp_path, invalid, reason
):
    path = _database(tmp_path / "copy.db", [invalid])
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE earlier_events (occurred_at DATETIME)")
        connection.execute("INSERT INTO earlier_events VALUES ('2026-01-15 08:45:00')")
    before = sha256(path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match=reason):
        migrate_timestamps(
            path,
            "America/New_York",
            ["earlier_events.occurred_at", "synthetic_events.occurred_at"],
        )

    assert sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT occurred_at FROM earlier_events"
        ).fetchone() == ("2026-01-15 08:45:00",)
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = ?", (AUDIT_TABLE,)
            ).fetchall()
            == []
        )


def test_failed_upgrade_keeps_source_and_usable_encrypted_backup(tmp_path):
    source = _database(
        tmp_path / "source.db", ["2026-01-15 08:45:00", "2026-11-01 01:30:00"]
    )
    original = source.read_bytes()
    destination, backup = tmp_path / "copy.db", tmp_path / "before.slmbackup"
    key = Fernet.generate_key()

    with pytest.raises(ValueError, match="Ambiguous"):
        upgrade_database(
            source,
            destination,
            backup,
            key,
            source_timezone="America/New_York",
            timestamp_fields=["synthetic_events.occurred_at"],
        )

    assert source.read_bytes() == original
    assert _values(destination) == _values(source)
    restored = tmp_path / "restored.db"
    restore_backup(backup.read_bytes(), restored, key)
    assert _values(restored) == _values(source)


@pytest.mark.parametrize("zone", ["Not/A_Zone", "", "../UTC"])
def test_invalid_source_zone_does_not_create_output_or_backup(tmp_path, zone):
    source = _database(tmp_path / "source.db", ["2026-01-15 08:45:00"])
    destination, backup = tmp_path / "copy.db", tmp_path / "before.slmbackup"
    with pytest.raises(ValueError, match="IANA"):
        upgrade_database(
            source, destination, backup, Fernet.generate_key(), source_timezone=zone
        )
    assert not destination.exists()
    assert not backup.exists()


def test_quoted_identifiers_and_without_rowid_work_and_repeat_is_idempotent(tmp_path):
    path = tmp_path / "quoted.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            'CREATE TABLE "event""history" ("when""at" DATETIME PRIMARY KEY) WITHOUT ROWID'
        )
        connection.execute(
            'INSERT INTO "event""history" VALUES (?)', ("2026-01-15 08:45:00",)
        )

    first = migrate_timestamps(path, "Asia/Kathmandu", ['event"history.when"at'])
    second = migrate_timestamps(path, "America/New_York", ['event"history.when"at'])

    assert first["converted_values"] == 1
    assert second["converted_values"] == 0 and second["preserved_aware_values"] == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT * FROM "event""history"').fetchone() == (
            "2026-01-15T03:00:00+00:00",
        )
        assert connection.execute(
            f'SELECT COUNT(*) FROM "{AUDIT_TABLE}"'
        ).fetchone() == (2,)


def test_utc_datetime_type_is_discovered_and_aware_write_remains_unchanged(tmp_path):
    path = tmp_path / "typed.db"
    engine = create_engine(f"sqlite:///{path}")
    metadata = MetaData()
    events = Table(
        "typed_events",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("occurred_at", UTCDateTime),
    )
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                events.insert(),
                [
                    {"occurred_at": datetime(2026, 1, 15, 8, 45)},
                    {"occurred_at": datetime(2026, 1, 15, 8, 45, tzinfo=timezone.utc)},
                ],
            )
        with sqlite3.connect(path) as connection:
            original_aware = connection.execute(
                "SELECT occurred_at FROM typed_events WHERE id = 2"
            ).fetchone()[0]
        result = migrate_timestamps(path, "UTC", ["typed_events.occurred_at"])
        assert result["converted_values"] == 1 and result["preserved_aware_values"] == 1
        with engine.connect() as connection:
            values = connection.execute(
                events.select().order_by(events.c.id)
            ).fetchall()
            assert (
                values[0].occurred_at
                == values[1].occurred_at
                == datetime(2026, 1, 15, 8, 45, tzinfo=timezone.utc)
            )
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT occurred_at FROM typed_events WHERE id = 2"
                ).fetchone()[0]
                == original_aware
            )
    finally:
        engine.dispose()


def test_cli_source_timezone_help_and_missing_key_never_generate_key(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "recover_database.py"
    environment = dict(os.environ, HOME=str(tmp_path))
    environment.pop("SLM_ENCRYPTION_KEY", None)
    help_result = subprocess.run(
        [sys.executable, str(script), "upgrade", "--help"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0 and "--source-timezone" in help_result.stdout
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "upgrade",
            "--database",
            str(tmp_path / "absent.db"),
            "--output",
            str(tmp_path / "copy.db"),
            "--backup",
            str(tmp_path / "before.slmbackup"),
            "--source-timezone",
            "Europe/Madrid",
            "--timestamp-field",
            "synthetic_events.occurred_at",
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and "original encryption key" in result.stderr
    assert not (tmp_path / ".slm_educator").exists()
    assert not (tmp_path / "copy.db").exists()


def test_cli_upgrade_passes_explicit_source_timezone_to_copy(tmp_path):
    source = _database(tmp_path / "source.db", ["2026-01-15 08:45:00"])
    script = Path(__file__).resolve().parents[2] / "scripts" / "recover_database.py"
    destination, backup = tmp_path / "copy.db", tmp_path / "before.slmbackup"
    environment = dict(
        os.environ,
        HOME=str(tmp_path),
        SLM_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "upgrade",
            "--database",
            str(source),
            "--output",
            str(destination),
            "--backup",
            str(backup),
            "--source-timezone",
            "Europe/Madrid",
            "--timestamp-field",
            "synthetic_events.occurred_at",
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["timestamp_migration"]["converted_values"] == 1
    assert _values(destination)[0][0] == "2026-01-15T07:45:00+00:00"
    assert _values(source)[0][0] == "2026-01-15 08:45:00"


def test_source_zone_without_field_scope_is_rejected_before_backup(tmp_path):
    source = _database(tmp_path / "source.db", ["2026-01-15 08:45:00"])
    with pytest.raises(ValueError, match="timestamp-field"):
        upgrade_database(
            source,
            tmp_path / "copy.db",
            tmp_path / "backup.slmbackup",
            Fernet.generate_key(),
            source_timezone="Europe/Madrid",
        )
    assert not (tmp_path / "copy.db").exists()
    assert not (tmp_path / "backup.slmbackup").exists()


def test_unselected_fields_of_different_origin_remain_untouched(tmp_path):
    source = _database(tmp_path / "source.db", ["2026-01-15 08:45:00"])
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE known_utc_auth (logged_at DATETIME)")
        connection.execute("INSERT INTO known_utc_auth VALUES ('2026-01-15 08:45:00')")
    destination = tmp_path / "copy.db"
    result = upgrade_database(
        source,
        destination,
        tmp_path / "backup.slmbackup",
        Fernet.generate_key(),
        source_timezone="Europe/Madrid",
        timestamp_fields=["synthetic_events.occurred_at"],
    )
    assert _values(destination)[0][0] == "2026-01-15T07:45:00+00:00"
    with sqlite3.connect(destination) as connection:
        assert (
            connection.execute("SELECT logged_at FROM known_utc_auth").fetchone()[0]
            == "2026-01-15 08:45:00"
        )
    assert json.loads(result["timestamp_migration"]["selected_fields"]) == [
        "synthetic_events.occurred_at"
    ]


def test_unknown_or_non_datetime_field_selection_fails_without_conversion(tmp_path):
    path = _database(tmp_path / "copy.db", ["2026-01-15 08:45:00"])
    for fields in (["synthetic_events.calendar_day"], ["synthetic_events.missing"], []):
        with pytest.raises(ValueError):
            migrate_timestamps(path, "UTC", fields)
        assert _values(path)[0][0] == "2026-01-15 08:45:00"
