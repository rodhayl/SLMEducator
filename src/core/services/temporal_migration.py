"""Explicit timestamp conversion for a backed-up, newly created SQLite copy.

Legacy naive values do not identify an instant. Only an operator-supplied IANA
source zone can resolve them; ambiguous and nonexistent local times fail closed.
This module intentionally does not import the application models or load keys.
"""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import json
import sqlite3
from zoneinfo import ZoneInfo

from src.core.services.temporal_service import utc_now, validate_timezone

MIGRATION_VERSION = "20261004_explicit_source_timezone_v1"
AUDIT_TABLE = "slm_temporal_migrations"
_DATETIME_TYPE = re.compile(r"DATETIME(?:\(\d+\))?", re.IGNORECASE)
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,6})?)?)?"
)


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _datetime_columns(connection: sqlite3.Connection) -> list[tuple[str, str]]:
    """Discover declared DATETIME columns without interpreting other field types."""
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [
        (table, row[1])
        for (table,) in tables
        if table != AUDIT_TABLE
        for row in connection.execute(f"PRAGMA table_info({_quote(table)})")
        if _DATETIME_TYPE.fullmatch(row[2].strip())
    ]


def _utc_value(value: object, zone: ZoneInfo, field: str) -> str | None:
    """Return a naive value's UTC representation, or None for an aware value."""
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValueError(
            f"Invalid timestamp in {field}; no timestamp changes committed"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return None
        candidates = set()
        for fold in (0, 1):
            instant = parsed.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
            if instant.astimezone(zone).replace(tzinfo=None) == parsed:
                candidates.add(instant)
    except (ValueError, OverflowError) as error:
        raise ValueError(
            f"Invalid timestamp in {field}; no timestamp changes committed"
        ) from error
    if not candidates:
        raise ValueError(
            f"Nonexistent local timestamp in {field}; no timestamp changes committed"
        )
    if len(candidates) != 1:
        raise ValueError(
            f"Ambiguous local timestamp in {field}; no timestamp changes committed"
        )
    return candidates.pop().isoformat()


def _convert_column(
    connection: sqlite3.Connection, table: str, column: str, zone: ZoneInfo
) -> dict[str, int]:
    """Convert distinct naive strings; binary matching preserves aware bytes."""
    table_sql, column_sql = _quote(table), _quote(column)
    counts = {"converted_values": 0, "preserved_aware_values": 0, "null_values": 0}
    counts["null_values"] = connection.execute(
        f"SELECT COUNT(*) FROM {table_sql} WHERE {column_sql} IS NULL"
    ).fetchone()[0]
    values = connection.execute(
        f"SELECT {column_sql}, COUNT(*) FROM {table_sql} WHERE {column_sql} IS NOT NULL "
        f"GROUP BY {column_sql} COLLATE BINARY"
    ).fetchall()
    for value, count in values:
        converted = _utc_value(value, zone, f"{table}.{column}")
        if converted is None:
            counts["preserved_aware_values"] += count
            continue
        connection.execute(
            f"UPDATE {table_sql} SET {column_sql} = ? WHERE {column_sql} COLLATE BINARY = ?",
            (converted, value),
        )
        counts["converted_values"] += count
    return counts


def _record_audit(
    connection: sqlite3.Connection, zone: str, counts: dict[str, int], fields: list[str]
) -> dict[str, str | int]:
    """Record provenance and aggregate counts, never row contents or credentials."""
    completed_at = utc_now().isoformat()
    connection.execute(
        f"CREATE TABLE IF NOT EXISTS {_quote(AUDIT_TABLE)} ("
        "id INTEGER PRIMARY KEY, migration_version TEXT NOT NULL, "
        "source_timezone TEXT NOT NULL, completed_at TEXT NOT NULL, selected_fields TEXT NOT NULL, "
        "columns_inspected INTEGER NOT NULL, converted_values INTEGER NOT NULL, "
        "preserved_aware_values INTEGER NOT NULL, null_values INTEGER NOT NULL)"
    )
    connection.execute(
        f"INSERT INTO {_quote(AUDIT_TABLE)} (migration_version, source_timezone, completed_at, "
        "selected_fields, columns_inspected, converted_values, preserved_aware_values, null_values) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            MIGRATION_VERSION,
            zone,
            completed_at,
            json.dumps(sorted(fields)),
            counts["columns_inspected"],
            counts["converted_values"],
            counts["preserved_aware_values"],
            counts["null_values"],
        ),
    )
    return {
        "migration_version": MIGRATION_VERSION,
        "source_timezone": zone,
        "completed_at": completed_at,
        "selected_fields": json.dumps(sorted(fields)),
        **counts,
    }


def migrate_timestamps(
    path: Path, source_timezone: str, fields: list[str]
) -> dict[str, str | int]:
    """Convert naive DATETIME fields atomically in an explicitly selected copy.

    Args:
        path: Existing new copy created by the encrypted recovery workflow.
        source_timezone: Operator-confirmed IANA timezone of the selected values.
        fields: Exact table.column names known to share that source timezone.

    Returns:
        Persisted migration provenance and aggregate conversion counts.

    Raises:
        ValueError: Invalid zone, invalid/ambiguous timestamps or SQLite failure.
    """
    if not fields:
        raise ValueError(
            "Select timestamp fields with a known source timezone; no global inference is supported"
        )
    zone_name = validate_timezone(source_timezone)
    zone = ZoneInfo(zone_name)
    target = Path(path).resolve(strict=True)
    try:
        with closing(
            sqlite3.connect(target.as_uri() + "?mode=rw", uri=True)
        ) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                available = {
                    f"{table}.{column}": (table, column)
                    for table, column in _datetime_columns(connection)
                }
                if set(fields) - set(available):
                    raise ValueError("Selected field is not a declared DATETIME column")
                columns = [available[name] for name in sorted(set(fields))]
                counts = {
                    "columns_inspected": len(columns),
                    "converted_values": 0,
                    "preserved_aware_values": 0,
                    "null_values": 0,
                }
                for table, column in columns:
                    for name, count in _convert_column(
                        connection, table, column, zone
                    ).items():
                        counts[name] += count
                audit = _record_audit(connection, zone_name, counts, list(set(fields)))
                if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise ValueError("Timestamp migration failed its integrity check")
                connection.commit()
                return audit
            except BaseException:
                connection.rollback()
                raise
    except sqlite3.Error as error:
        raise ValueError(
            "Timestamp migration failed; no timestamp changes committed"
        ) from error
