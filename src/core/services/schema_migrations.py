"""Explicit non-destructive reconciliation for create_all-era SQLite databases.

Never invoked automatically against an existing installation. The upgrade CLI
first creates an encrypted backup and a new working copy, then calls this module.
"""
import enum
import json
from pathlib import Path

from sqlalchemy import create_engine, inspect

REVISION = "20261004_request_context"
KNOWN_REVISIONS = {"7924cdebd9c6", "20261004_reconcile", "20261004_learning_snapshots", REVISION}


def schema_gaps(connection) -> dict:
    """List model tables/columns missing from an existing schema."""
    from src.core.models import Base
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    missing_tables = sorted(set(Base.metadata.tables) - tables)
    columns = {}
    for name, table in Base.metadata.tables.items():
        if name in tables:
            missing = sorted(set(table.columns.keys()) - {item["name"] for item in inspector.get_columns(name)})
            if missing:
                columns[name] = missing
    return {"tables": missing_tables, "columns": columns}


def _default_literal(column) -> str | None:
    """Use only explicit scalar model defaults, never fabricate identities."""
    default = column.default
    if default is None:
        return None
    value = default.arg
    if isinstance(value, enum.Enum):
        value = value.name
    if default.is_callable:
        name = getattr(value, "__name__", "")
        value = {} if name == "dict" else [] if name == "list" else None
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def reconcile_connection(connection) -> dict:
    """Add missing tables/columns and indexes; reject ambiguous destructive work."""
    from src.core.models import Base
    before = schema_gaps(connection)
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "alembic_version" in tables:
        revisions = set(connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalars())
        if revisions - KNOWN_REVISIONS:
            raise ValueError("Unknown migration revision; refusing automatic reconciliation")
    quote = connection.dialect.identifier_preparer.quote
    for table_name, names in before["columns"].items():
        table = Base.metadata.tables[table_name]
        rows = connection.exec_driver_sql(f"SELECT COUNT(*) FROM {quote(table_name)}").scalar_one()
        for name in names:
            column = table.columns[name]
            default = _default_literal(column)
            if not column.nullable and default is None and rows:
                raise ValueError(f"Missing required field {table_name}.{name} has no safe migration default")
            definition = f"{quote(name)} {column.type.compile(dialect=connection.dialect)}"
            if not column.nullable:
                definition += " NOT NULL"
            if default is not None:
                definition += f" DEFAULT {default}"
            connection.exec_driver_sql(f"ALTER TABLE {quote(table_name)} ADD COLUMN {definition}")
    Base.metadata.create_all(connection)
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            index.create(connection, checkfirst=True)
    remaining = schema_gaps(connection)
    if remaining["tables"] or remaining["columns"]:
        raise ValueError("Schema reconciliation did not produce all required fields")
    return before


def reconcile_database(path: Path) -> dict:
    """Reconcile an explicitly chosen new copy and record its verified baseline."""
    path = Path(path).resolve(strict=True)
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                changes = reconcile_connection(connection)
                connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
                connection.exec_driver_sql("DELETE FROM alembic_version")
                connection.exec_driver_sql("INSERT INTO alembic_version (version_num) VALUES (?)", (REVISION,))
                if connection.exec_driver_sql("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise ValueError("Reconciled database failed its integrity check")
                connection.commit()
                return changes
            except BaseException:
                connection.rollback()
                raise
    finally:
        engine.dispose()
