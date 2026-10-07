"""Create-only test databases; never reset a supplied path or its sidecars."""

from pathlib import Path

from src.core.services.database import DatabaseService


def new_synthetic_database(path: Path) -> DatabaseService:
    """Create a database only at an explicit, unused absolute test path."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Synthetic database path must be absolute")
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = path.with_name(path.name + suffix)
        if candidate.exists() or candidate.is_symlink():
            raise FileExistsError("Synthetic database destination must be new")
    return DatabaseService(str(path))
