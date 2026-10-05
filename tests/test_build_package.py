"""Packaging safety contracts; real SQLite/seeder, simulated Windows freezer."""

from contextlib import closing
import ast
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from typing import Any, Iterator

import pytest

from scripts import build_package as builder


def test_windows_freezer_collects_iana_timezone_database(tmp_path):
    command = builder._pyinstaller_command(tmp_path / "staging", tmp_path / "work", "Synthetic")
    collected = [command[index + 1] for index, value in enumerate(command) if value == "--collect-all"]
    assert "tzdata" in collected


def test_freezer_omits_removed_provider_and_password_libraries() -> None:
    """Removed SDKs must not become undeclared freezer dependencies again."""
    retired = {"passlib", "langsmith", "langchain_core", "langchain_openai"}
    assert not retired.intersection(name.split(".")[0] for name in builder.HIDDEN_IMPORTS)
    assert "bcrypt" in builder.HIDDEN_IMPORTS
    assert "tkinter.scrolledtext" not in builder.HIDDEN_IMPORTS


def test_freezer_covers_all_mounted_routes() -> None:
    """Keep the explicit frozen API manifest aligned without importing the app."""
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "src" / "api" / "main.py").read_text(encoding="utf-8"))
    routes = {
        f"src.api.routes.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "src.api.routes"
        for alias in node.names
    }
    assert routes
    assert routes <= set(builder.HIDDEN_IMPORTS)
    for module in builder.HIDDEN_IMPORTS:
        if module.startswith("src."):
            assert (root / (module.replace(".", "/") + ".py")).is_file(), module


def test_freezer_covers_uvicorn_default_dispatch() -> None:
    """Uvicorn resolves these default protocol/loop modules by string name."""
    from uvicorn.config import HTTP_PROTOCOLS, LIFESPAN, LOOP_FACTORIES, WS_PROTOCOLS

    for choices in (HTTP_PROTOCOLS, WS_PROTOCOLS, LIFESPAN, LOOP_FACTORIES):
        module = str(choices["auto"]).split(":")[0]
        assert module in builder.HIDDEN_IMPORTS, module
    assert len(builder.HIDDEN_IMPORTS) == len(set(builder.HIDDEN_IMPORTS))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Copy code only; all runtime/config fixtures below are synthetic."""
    source = Path(__file__).resolve().parents[1]
    project = tmp_path / "checkout"
    project.mkdir()
    for directory in ("src", "translations", "alembic"):
        shutil.copytree(
            source / directory,
            project / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    (project / "scripts").mkdir()
    shutil.copyfile(
        source / "scripts" / "seed_admin.py", project / "scripts" / "seed_admin.py"
    )
    shutil.copyfile(source / "scripts/recover_database.py", project / "scripts/recover_database.py")
    shutil.copyfile(source / "alembic.ini", project / "alembic.ini")
    return project


@pytest.fixture
def fake_freezer(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], Path]]:
    """Keep config/seeder subprocesses real, simulate only PyInstaller's output."""
    real_run = subprocess.run
    commands: list[tuple[list[str], Path]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        cwd = Path(kwargs["cwd"])
        commands.append((command, cwd))
        if command[1:3] != ["-m", "PyInstaller"]:
            return real_run(command, **kwargs)
        assert kwargs["check"] is True
        assert kwargs["env"]["SLM_DB_PATH"] == str(cwd / "slm_educator.db")
        assert kwargs["env"]["SLM_CONFIG_FILE"] == str(cwd / "env.properties")
        assert "SLM_INITIAL_ADMIN_PASSWORD" not in kwargs["env"]
        assert "SLM_TEST_MODE" not in kwargs["env"]
        assert "SLM_WEB_DIR" not in kwargs["env"]
        name = command[command.index("--name") + 1]
        output = Path(command[command.index("--distpath") + 1]) / name
        output.mkdir(parents=True)
        (output / f"{name}.exe").write_text("synthetic freezer output")
        for index, argument in enumerate(command):
            if argument == "--add-data":
                source, target = command[index + 1].rsplit(builder.os.pathsep, 1)
                source_path = Path(source)
                assert source_path.is_relative_to(cwd)
                destination = output / "_internal" / target
                if source_path.is_dir():
                    shutil.copytree(source_path, destination)
                else:
                    destination.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_path, destination / source_path.name)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(builder.subprocess, "run", run)
    monkeypatch.delenv("SLM_INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("SLM_INITIAL_ADMIN_EMAIL", raising=False)
    return commands


def read_users(database: Path) -> list[tuple[str, str, str]]:
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute(
            "SELECT username, email, password_hash FROM users"
        ).fetchall()


def test_production_preserves_working_data_and_excludes_private_configuration(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    private = "SYNTHETIC-PRIVATE-CONFIG-NOT-FOR-DISTRIBUTION"
    files = {}
    for name in (
        "slm_educator.db",
        "slm_educator.db-wal",
        "slm_educator.db-shm",
        "env.properties",
        ".env",
        "env-test.properties",
        "settings.properties",
    ):
        path = project / name
        path.write_bytes((private + name).encode())
        files[path] = path.read_bytes()
    external = tmp_path / "external.db"
    external.write_bytes(b"synthetic external database must never be opened")
    files[external] = external.read_bytes()
    home = tmp_path / "synthetic-home"
    (home / ".slm_educator").mkdir(parents=True)
    key_file = home / ".slm_educator" / "encryption.key"
    key_file.write_bytes(b"synthetic private key must never be read")
    files[key_file] = key_file.read_bytes()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("SLM_DB_PATH", str(external))
    monkeypatch.setenv("SLM_CONFIG_FILE", str(project / "env.properties"))
    monkeypatch.setenv("SLM_TEST_MODE", "1")
    monkeypatch.setenv("SLM_WEB_DIR", str(tmp_path / "private-web"))
    output = builder.build_package(project, tmp_path / "package")
    assert {path: path.read_bytes() for path in files} == files
    assert not (project / "logs").exists()
    assert len(read_users(output / "slm_educator.db")) == 1
    assert "Generated Password:" in capfd.readouterr().out
    for path in output.rglob("*"):
        if path.is_file():
            assert private.encode() not in path.read_bytes()
    config = (output / "env.properties").read_text()
    assert "default_provider = ollama" in config
    assert "openrouter.api_key = \n" in config
    assert not list(output.glob("*.db-*"))
    assert len(fake_freezer) == 3
    assert all(not cwd.exists() for _, cwd in fake_freezer)


def test_fresh_builds_get_distinct_usable_admin_passwords(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    capfd: pytest.CaptureFixture[str],
) -> None:
    from src.core.security import verify_password

    passwords = []
    for name in ("first", "second"):
        output = builder.build_package(project, tmp_path / name)
        password_match = re.search(r"Generated Password: (\S+)", capfd.readouterr().out)
        assert password_match is not None
        password = password_match.group(1)
        username, email, password_hash = read_users(output / "slm_educator.db")[0]
        assert (username, email) == ("admin", "admin@example.invalid")
        assert len(password) == 20
        assert verify_password(password, password_hash)
        passwords.append(password)
    assert passwords[0] != passwords[1]


def test_production_honors_explicit_bootstrap_password_without_bundling_it(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    from src.core.security import verify_password

    password = "SyntheticPackagePass123!"
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", password)
    output = builder.build_package(project, tmp_path / "package")
    assert verify_password(password, read_users(output / "slm_educator.db")[0][2])
    assert password not in capfd.readouterr().out
    assert all(
        password.encode() not in path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    )


def test_invalid_bootstrap_fails_without_freezing_or_publishing(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", "short")
    with pytest.raises(subprocess.CalledProcessError):
        builder.build_package(project, tmp_path / "package")
    assert not (tmp_path / "package").exists()
    assert len(fake_freezer) == 2
    assert all(not cwd.exists() for _, cwd in fake_freezer)
    assert "at least 12 characters" in capfd.readouterr().out


@pytest.fixture
def live_database(tmp_path: Path) -> Iterator[tuple[Path, sqlite3.Connection]]:
    path = tmp_path / "live.sqlite3"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE records (value TEXT)")
        connection.commit()
        connection.execute("INSERT INTO records VALUES ('synthetic committed WAL row')")
        connection.commit()
        assert Path(str(path) + "-wal").stat().st_size > 0
        connection.execute(
            "INSERT INTO records VALUES ('uncommitted must be excluded')"
        )
        yield path, connection
        connection.rollback()


def test_test_package_is_consistent_standalone_wal_snapshot_without_seeding(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    live_database: tuple[Path, sqlite3.Connection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, writer = live_database
    before = writer.execute("SELECT * FROM records").fetchall()
    monkeypatch.setenv("SLM_INITIAL_ADMIN_PASSWORD", "short")
    output = builder.build_package(project, tmp_path / "test-package", database=source)
    with closing(sqlite3.connect(output / "slm_educator.db")) as snapshot:
        assert snapshot.execute("SELECT * FROM records").fetchall() == [
            ("synthetic committed WAL row",)
        ]
        assert snapshot.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert snapshot.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert (
            snapshot.execute(
                "SELECT name FROM sqlite_master WHERE name='users'"
            ).fetchall()
            == []
        )
    assert writer.execute("SELECT * FROM records").fetchall() == before
    assert not list(output.glob("*.db-*"))
    assert len(fake_freezer) == 2  # config + freezer; no seeder


def test_existing_package_is_never_overwritten(
    project: Path, tmp_path: Path, fake_freezer: list[Any]
) -> None:
    output = tmp_path / "installed-package"
    output.mkdir()
    database = output / "slm_educator.db"
    database.write_bytes(b"synthetic installed user data")
    with pytest.raises(FileExistsError, match="Output already exists"):
        builder.build_package(project, output)
    assert database.read_bytes() == b"synthetic installed user data"
    assert not fake_freezer


def test_freezer_failure_keeps_source_and_prior_outputs(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_or_fake = builder.subprocess.run

    def fail_freezer(command: list[str], **kwargs: Any) -> Any:
        if command[1:3] == ["-m", "PyInstaller"]:
            raise subprocess.CalledProcessError(1, command)
        return real_or_fake(command, **kwargs)

    monkeypatch.setattr(builder.subprocess, "run", fail_freezer)
    database = project / "slm_educator.db"
    database.write_bytes(b"synthetic source unchanged")
    with pytest.raises(subprocess.CalledProcessError):
        builder.build_package(project, tmp_path / "package")
    assert database.read_bytes() == b"synthetic source unchanged"
    assert not (tmp_path / "package").exists()


def test_missing_snapshot_is_not_silently_created(
    project: Path, tmp_path: Path, fake_freezer: list[Any]
) -> None:
    source = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        builder.build_package(project, tmp_path / "package", database=source)
    assert not source.exists()
    assert not (tmp_path / "package").exists()
    assert not fake_freezer


@pytest.mark.parametrize(
    "arguments", [["--test"], ["--prod", "--database", "example.db"], []]
)
def test_modes_require_explicit_database_selection(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        builder.main(arguments)
    assert error.value.code == 2


def test_cli_rejects_non_windows_builds_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_freezer: list[Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A simulated freezer on Linux cannot establish native Windows readiness."""
    monkeypatch.setattr(sys, "platform", "linux")
    output = tmp_path / "not-a-windows-package"
    with pytest.raises(SystemExit) as error:
        builder.main(["--prod", "--output-dir", str(output)])
    assert error.value.code == 2
    assert "Windows packages must be built on Windows" in capsys.readouterr().err
    assert not output.exists()
    assert not fake_freezer


def test_cli_rejects_unbundlable_zipfs_tcl_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A successful freezer exit must not publish a launcher without Tcl/Tk."""
    import tkinter

    class ZipfsTcl:
        def eval(self, expression: str) -> str:
            assert expression == "info library"
            return "//zipfs:/lib/tcl/tcl_library"

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(tkinter, "Tcl", ZipfsTcl)
    output = tmp_path / "unusable-package"
    assert builder.main(["--prod", "--output-dir", str(output)]) == 1
    assert "Tcl/Tk in zipfs" in capsys.readouterr().err
    assert not output.exists()


def test_batch_wrapper_has_no_destructive_legacy_steps() -> None:
    script = (
        (Path(__file__).resolve().parents[1] / "build_package.bat").read_text().lower()
    )
    for forbidden in (
        "taskkill",
        "del /",
        "rmdir",
        "slm_initial_admin_password",
        "copy ",
    ):
        assert forbidden not in script
    assert 'pushd "%~dp0"' in script
    assert "scripts\\build_package.py %*" in script


def test_packaged_first_run_resolves_seeded_database_from_other_directory(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.startup_utils import setup_frozen_working_directory
    from src.core.services.database import DatabaseService
    from src.core.services.settings_config_service import get_config_file_path
    from src.core.services.translation_service import TranslationService
    from src.api.main import _resolve_web_dir

    package = builder.build_package(project, tmp_path / "package")
    other = tmp_path / "unrelated-caller"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(package / "SLMEducator.exe"))
    monkeypatch.delenv("SLM_DB_PATH", raising=False)
    monkeypatch.delenv("SLM_CONFIG_FILE", raising=False)
    setup_frozen_working_directory()
    assert Path.cwd() == package
    assert Path(get_config_file_path()) == package / "env.properties"
    monkeypatch.delenv("SLM_WEB_DIR", raising=False)
    assert _resolve_web_dir() == (package, package / "_internal" / "src" / "web")
    translations = TranslationService()
    assert translations.translations_dir == package / "_internal" / "translations"
    assert translations.load_language("en")
    assert translations.load_language("es")
    assert translations.translations["en"]
    assert translations.translations["es"]
    for directory in ("src/web", "translations", "alembic"):
        for source in (project / directory).rglob("*"):
            if source.is_file() and "__pycache__" not in source.parts:
                packaged = package / "_internal" / source.relative_to(project)
                assert packaged.read_bytes() == source.read_bytes()
    database = DatabaseService()
    try:
        with database.get_session() as session:
            from src.core.models import User

            assert session.query(User).one().username == "admin"
    finally:
        database.close()
    assert not (other / "slm_educator.db").exists()


def test_source_launcher_keeps_callers_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.startup_utils import setup_frozen_working_directory

    monkeypatch.chdir(tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)
    setup_frozen_working_directory()
    assert Path.cwd() == tmp_path


def test_production_does_not_open_or_change_a_live_working_database(
    project: Path,
    tmp_path: Path,
    fake_freezer: list[Any],
    live_database: tuple[Path, sqlite3.Connection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, writer = live_database
    paths = [source, Path(str(source) + "-wal"), Path(str(source) + "-shm")]
    def fingerprint(path: Path) -> bytes | tuple[int, int]:
        """Read live files where Windows SQLite sharing permits it."""
        try:
            return path.read_bytes()
        except PermissionError:
            metadata = path.stat()
            return metadata.st_size, metadata.st_mtime_ns

    before = {path: fingerprint(path) for path in paths}
    monkeypatch.setenv("SLM_DB_PATH", str(source))
    builder.build_package(project, tmp_path / "production")
    assert {path: fingerprint(path) for path in paths} == before
    assert writer.execute("SELECT * FROM records").fetchall() == [
        ("synthetic committed WAL row",),
        ("uncommitted must be excluded",),
    ]


@pytest.mark.parametrize(
    "name",
    [
        "env.properties.bak",
        "slm_educator.db.bak",
        "api.log",
        ".env.backup",
        "encryption.key",
        "jwt.secret",
        "scratch.tmp",
    ],
)
def test_local_backups_logs_and_keys_are_not_package_inputs(
    project: Path, tmp_path: Path, name: str
) -> None:
    local = project / "src" / name
    local.write_text("synthetic private bytes")
    staging = tmp_path / "inputs"
    staging.mkdir()
    builder._copy_inputs(project, staging)
    assert not (staging / "src" / name).exists()
    assert (staging / "src" / "web" / "static" / "css" / "main.css").is_file()


@pytest.mark.parametrize(
    "name", ["src", "alembic.ini", "scripts", "scripts/seed_admin.py"]
)
def test_symlinked_inputs_are_rejected(
    project: Path, tmp_path: Path, name: str
) -> None:
    path = project / name
    directory = path.is_dir()
    target = tmp_path / "outside-input"
    if directory:
        shutil.move(str(path), target)
    else:
        path.replace(target)
    try:
        path.symlink_to(target, target_is_directory=directory)
    except OSError:
        pytest.skip("The test host does not allow symlink creation")
    staging = tmp_path / "staging"
    staging.mkdir()
    with pytest.raises(ValueError, match="Symlinked package input"):
        builder._copy_inputs(project, staging)
