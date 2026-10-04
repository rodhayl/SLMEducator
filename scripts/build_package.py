#!/usr/bin/env python3
"""Build a Windows package without modifying an installation or local config.

Only new, disposable staging directories and a new output directory are written.
Production uses the existing create-only seeder; test data requires an explicit
SQLite source and is captured with SQLite's online backup API.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

HIDDEN_IMPORTS = (
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    # Uvicorn selects the default loop, protocols and lifespan by string name.
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.ext.baked",
    "sqlite3",
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.responses",
    "fastapi.security",
    "pydantic",
    "pydantic.v1",
    "pydantic.v1.typing",
    "pydantic.v1.fields",
    "pydantic.v1.main",
    "pydantic.v1.types",
    "pydantic.v1.validators",
    "email_validator",
    "multipart",
    "python_multipart",
    "cryptography",
    "cryptography.fernet",
    "jwt",
    "bcrypt",
    "httpx",
    "typing_extensions",
    "anyio",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "websockets",
    "click",
    "h11",
    "sniffio",
    "src.api.dependencies",
    "src.api.routes.auth",
    "src.api.routes.dashboard",
    "src.api.routes.content",
    "src.api.routes.ai",
    "src.api.routes.settings",
    "src.api.routes.generation",
    "src.api.routes.assessment",
    "src.api.routes.learning",
    "src.api.routes.mastery",
    "src.api.routes.classroom",
    "src.api.routes.study_plans",
    "src.api.routes.gamification",
    "src.api.routes.annotations",
    "src.api.routes.portability",
    "src.api.routes.timezone",
    "src.api.routes.assistance",
    "src.api.routes.upload",
    "src.api.routes.students",
    "src.core.services.auth",
    "src.core.services.database",
    "src.core.services.ai_service",
)
COLLECT_ALL = ("fastapi", "pydantic", "sqlalchemy", "cryptography", "tzdata")


def snapshot_database(source: Path, destination: Path) -> None:
    """Capture committed SQLite data, including WAL, into one standalone file."""
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("The database source must be a regular SQLite file.")
    # mode=ro prevents accidentally creating or writing the source database.
    # Do not use immutable=1: that would ignore an active WAL.
    deadline = time.monotonic() + 30

    def check_timeout(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError(
                "SQLite snapshot timed out; retry when writers are idle."
            )

    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst, pages=256, progress=check_timeout, sleep=0.1)
            # The archive must not depend on WAL/SHM files copied separately.
            dst.execute("PRAGMA journal_mode=DELETE")
            if dst.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ValueError("The SQLite snapshot failed its integrity check.")


def _is_link(path: Path) -> bool:
    """Reject symlinks and Windows junctions without following them."""
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _copy_inputs(project_root: Path, staging: Path) -> None:
    """Copy application resources, excluding runtime data and local settings."""
    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.db*",
        "*.sqlite*",
        ".env*",
        "*.properties*",
        "*.log",
        "*.bak",
        "*.tmp",
        "*.key",
        "*.secret",
        "logs",
        "data",
        "exports",
        "imports",
    )
    for name in ("src", "translations", "alembic"):
        source = project_root / name
        # Avoid dereferencing links into unrelated/private files while copying.
        if _is_link(source) or any(_is_link(path) for path in source.rglob("*")):
            raise ValueError(f"Symlinked package input is not supported: {name}")
        shutil.copytree(source, staging / name, ignore=ignore)
    for name in ("alembic.ini", "scripts", "scripts/seed_admin.py"):
        if _is_link(project_root / name):
            raise ValueError(f"Symlinked package input is not supported: {name}")
    shutil.copyfile(project_root / "alembic.ini", staging / "alembic.ini")
    (staging / "scripts").mkdir()
    shutil.copyfile(
        project_root / "scripts" / "seed_admin.py",
        staging / "scripts" / "seed_admin.py",
    )


def _build_environment(staging: Path) -> dict[str, str]:
    """Constrain application paths and PyInstaller caches to this build."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SLM_") and key != "JWT_SECRET"
    }
    # Importing the ORM initializes its key storage. Keep that build-only key
    # outside the developer's real home and outside the distributed resources.
    home = staging / ".build-home"
    home.mkdir()
    environment.update(
        SLM_DB_PATH=str(staging / "slm_educator.db"),
        SLM_CONFIG_FILE=str(staging / "env.properties"),
        PYTHONPATH=str(staging),
        PYINSTALLER_CONFIG_DIR=str(staging / ".pyinstaller"),
        HOME=str(home),
        USERPROFILE=str(home),
    )
    return environment


def _prepare_database(
    staging: Path, environment: dict[str, str], database: Path | None
) -> None:
    """Generate public defaults and prepare a fresh admin or explicit snapshot."""
    # Reuse runtime defaults, never read the developer's properties/.env files.
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.core.services.settings_config_service import SettingsConfigService; "
            "SettingsConfigService('env.properties')",
        ],
        cwd=staging,
        env=environment,
        check=True,
    )
    if not (staging / "env.properties").is_file():
        raise RuntimeError("Default package configuration was not created.")
    if database is not None:
        snapshot_database(database, staging / "slm_educator.db")
        return
    seed_environment = environment.copy()
    for key in ("SLM_INITIAL_ADMIN_PASSWORD", "SLM_INITIAL_ADMIN_EMAIL"):
        if key in os.environ:
            seed_environment[key] = os.environ[key]
    # Seeder errors are fatal. Never publish an unseeded, inaccessible package.
    subprocess.run(
        [sys.executable, str(staging / "scripts" / "seed_admin.py")],
        cwd=staging,
        env=seed_environment,
        check=True,
    )


def _pyinstaller_command(staging: Path, work: Path, name: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--windowed",
        "--name",
        name,
        "--clean",
        "--noconfirm",
        "--distpath",
        str(work / "dist"),
        "--workpath",
        str(work / "work"),
        "--specpath",
        str(work / "spec"),
        "--paths",
        str(staging),
    ]
    for source, target in (
        ("src", "src"),
        ("translations", "translations"),
        ("env.properties", "."),
        ("alembic.ini", "."),
        ("alembic", "alembic"),
    ):
        command.extend(["--add-data", f"{staging / source}{os.pathsep}{target}"])
    for module in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", module])
    for module in COLLECT_ALL:
        command.extend(["--collect-all", module])
    command.append(str(staging / "src" / "starter.py"))
    return command


def build_package(
    project_root: Path, output: Path, *, database: Path | None = None
) -> Path:
    """Build into a new directory; existing packages and their data are untouched."""
    project_root = project_root.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(
            f"Output already exists; choose a new --output-dir: {output}"
        )
    if database is not None:
        database = database.resolve(strict=True)
    name = "SLMEducator_Test" if database is not None else "SLMEducator"
    with tempfile.TemporaryDirectory(prefix="slm-package-") as temporary:
        work = Path(temporary)
        staging = work / "input"
        staging.mkdir()
        _copy_inputs(project_root, staging)
        environment = _build_environment(staging)
        _prepare_database(staging, environment, database)
        subprocess.run(
            _pyinstaller_command(staging, work, name),
            cwd=staging,
            env=environment,
            check=True,
        )
        package = work / "dist" / name
        if not (package / f"{name}.exe").is_file():
            raise RuntimeError(
                "PyInstaller did not produce the expected Windows executable."
            )
        snapshot_database(staging / "slm_educator.db", package / "slm_educator.db")
        shutil.copyfile(staging / "env.properties", package / "env.properties")
        # mkdir is exclusive even if another build creates the target meanwhile.
        output.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copytree(package, output, dirs_exist_ok=True)
        except Exception:
            shutil.rmtree(output)
            raise
    return output


def main(argv: list[str] | None = None) -> int:
    """Parse explicit modes and report build failures with a nonzero status."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--prod",
        action="store_true",
        help="Fresh database with a unique initial admin password",
    )
    mode.add_argument(
        "--test",
        action="store_true",
        help="Include an explicitly selected SQLite snapshot",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Required for --test; contains all selected database records",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New package directory; existing directories are never replaced",
    )
    args = parser.parse_args(argv)
    if args.test != (args.database is not None):
        parser.error(
            "--test requires --database PATH; --prod does not accept --database"
        )
    if sys.platform != "win32":
        parser.error(
            "Windows packages must be built on Windows with PyInstaller installed"
        )
    # PyInstaller 6.16 cannot collect Tcl/Tk from Python's embedded zipfs layout.
    # Such a build appears successful but its windowed launcher never starts.
    import tkinter

    tcl_library = tkinter.Tcl().eval("info library")
    if tcl_library.startswith("//zipfs:"):
        print(
            "[ERROR] This Python installation stores Tcl/Tk in zipfs, which "
            "PyInstaller cannot bundle. Build with a Python installation "
            "that provides Tcl/Tk directories (verified with Python 3.13).",
            file=sys.stderr,
        )
        return 1
    project_root = Path(__file__).resolve().parent.parent
    name = "SLMEducator_Test" if args.test else "SLMEducator"
    output = args.output_dir or project_root / "dist" / name
    try:
        result = build_package(project_root, output, database=args.database)
    except (
        OSError,
        ValueError,
        RuntimeError,
        sqlite3.Error,
        subprocess.CalledProcessError,
    ) as error:
        print(f"[ERROR] Build failed: {error}", file=sys.stderr)
        return 1
    print(f"[OK] Package created: {result}")
    if args.prod:
        print(
            "Save the initial admin password shown by the seeder (or supplied in the environment)."
        )
        print(
            "Sign in as admin and rotate it. Build separately for each installation; do not share its database."
        )
    else:
        print(
            "This test package contains the selected database's accounts and private data. Do not distribute it."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
