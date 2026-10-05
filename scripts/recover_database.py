#!/usr/bin/env python3
"""Explicit encrypted backup, create-only restore and copy-first schema upgrades."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parser() -> argparse.ArgumentParser:
    """Describe commands without reading any database, configuration or key."""
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--result-file", type=Path,
                      help="Write a new JSON receipt (required for a windowless packaged launcher)")
    commands = root.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="Encrypt a snapshot into a new archive")
    backup.add_argument("--database", type=Path, required=True)
    backup.add_argument("--output", type=Path, required=True)
    restore = commands.add_parser("restore", help="Restore into a NEW database path only")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)
    upgrade = commands.add_parser("upgrade", help="Back up and upgrade a NEW copy; preserve the source")
    upgrade.add_argument("--database", type=Path, required=True)
    upgrade.add_argument("--output", type=Path, required=True)
    upgrade.add_argument("--backup", type=Path, required=True)
    upgrade.add_argument(
        "--source-timezone",
        help="Known IANA zone of legacy naive timestamps, e.g. Europe/Madrid. "
             "Omit to preserve timestamp bytes. Ambiguous or nonexistent local times stop conversion.",
    )
    upgrade.add_argument(
        "--timestamp-field", action="append", dest="timestamp_fields",
        help="Exact table.column with this known source timezone; repeat for each field. Required with --source-timezone.",
    )
    inspect_command = commands.add_parser("inspect", help="Validate database integrity and the matching key")
    inspect_command.add_argument("--database", type=Path, required=True)
    return root


def main(argv=None) -> int:
    """Run only with an explicitly supplied original encryption key environment."""
    args = parser().parse_args(argv)
    if args.result_file and (args.result_file.exists() or args.result_file.is_symlink()):
        if sys.stderr is not None:
            print("Result file already exists; choose a new path.", file=sys.stderr)
        return 2
    if args.result_file and any(
        args.result_file.resolve() == value.resolve()
        for value in (getattr(args, "database", None), getattr(args, "backup", None), getattr(args, "output", None))
        if value is not None
    ):
        if sys.stderr is not None:
            print("Result file must be separate from database, backup and output.", file=sys.stderr)
        return 2
    key = os.environ.get("SLM_ENCRYPTION_KEY", "").encode()
    if not key:
        message = "SLM_ENCRYPTION_KEY must contain the original encryption key; no key is generated."
        if args.result_file:
            from src.core.services.recovery_service import write_new

            write_new(args.result_file, json.dumps({"success": False, "error": message}).encode())
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        return 2
    from src.core.services.recovery_service import (
        MAX_ARCHIVE_BYTES, create_backup, inspect_database, key_fingerprint,
        restore_backup, upgrade_database, write_new,
    )
    try:
        fingerprint = key_fingerprint(key)
        result: dict[str, object]
        if args.command == "backup":
            write_new(args.output, create_backup(args.database, key))
            result = {"backup": str(args.output), "key_fingerprint": fingerprint}
        elif args.command == "restore":
            if args.backup.stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError("Backup archive exceeds the supported size")
            summary = restore_backup(args.backup.read_bytes(), args.output, key)
            result = {"database": str(args.output), "summary": summary}
        elif args.command == "upgrade":
            result = upgrade_database(
                args.database, args.output, args.backup, key, source_timezone=args.source_timezone, timestamp_fields=args.timestamp_fields,
            )
        else:
            result = {"summary": inspect_database(args.database, key), "key_fingerprint": fingerprint}
        if args.result_file:
            write_new(args.result_file, json.dumps({"success": True, **result}, indent=2).encode())
        if sys.stdout is not None:
            print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        if args.result_file:
            write_new(args.result_file, json.dumps({"success": False, "error": str(error)}).encode())
        if sys.stderr is not None:
            print(f"Recovery stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
