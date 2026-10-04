#!/usr/bin/env python3
"""Explicit encrypted backup, create-only restore and copy-first schema upgrades."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



def parser() -> argparse.ArgumentParser:
    """Describe commands without reading any database, configuration or key."""
    root = argparse.ArgumentParser(description=__doc__)
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
    inspect_command = commands.add_parser("inspect", help="Validate database integrity and the matching key")
    inspect_command.add_argument("--database", type=Path, required=True)
    return root


def main(argv=None) -> int:
    """Run only with an explicitly supplied original encryption key environment."""
    args = parser().parse_args(argv)
    key = os.environ.get("SLM_ENCRYPTION_KEY", "").encode()
    if not key:
        print("SLM_ENCRYPTION_KEY must contain the original encryption key; no key is generated.", file=sys.stderr)
        return 2
    from src.core.services.recovery_service import (
        MAX_ARCHIVE_BYTES, create_backup, inspect_database, key_fingerprint,
        restore_backup, upgrade_database, write_new,
    )
    try:
        fingerprint = key_fingerprint(key)
        if args.command == "backup":
            write_new(args.output, create_backup(args.database, key))
            result = {"backup": str(args.output), "key_fingerprint": fingerprint}
        elif args.command == "restore":
            if args.backup.stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError("Backup archive exceeds the supported size")
            summary = restore_backup(args.backup.read_bytes(), args.output, key)
            result = {"database": str(args.output), "summary": summary}
        elif args.command == "upgrade":
            result = upgrade_database(args.database, args.output, args.backup, key)
        else:
            result = {"summary": inspect_database(args.database, key), "key_fingerprint": fingerprint}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Recovery stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
