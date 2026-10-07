"""Maintained installer-recipe contracts for the minimal Inno Setup wrapper.

These tests pin the recipe and the build orchestration. They do not freeze a
PyInstaller payload or compile a real installer; the native Windows build and a
packaged install/login smoke test remain separate evidence.
"""

from pathlib import Path
import subprocess

import pytest

from scripts import build_installer


@pytest.fixture
def recipe() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "installer" / "SLMEducator.iss").read_text(encoding="utf-8")


def test_recipe_installs_per_user_without_administrator_rights(recipe: str) -> None:
    """A per-user LOCALAPPDATA install must not require elevation."""
    assert "PrivilegesRequired=lowest" in recipe
    assert "{localappdata}" in recipe
    assert "PrivilegesRequiredOverridesAllowed=" in recipe


def test_recipe_keeps_database_and_configuration_as_user_data(recipe: str) -> None:
    """A reinstall must never overwrite the stored database or configuration."""
    assert "onlyifdoesntexist" in recipe
    assert "uninsneveruninstall" in recipe
    assert 'Excludes: "slm_educator.db,env.properties' in recipe
    assert 'Source: "{#MyPayloadDir}\\slm_educator.db"' in recipe
    assert 'Source: "{#MyPayloadDir}\\env.properties"' in recipe


def test_recipe_has_no_wildcard_uninstall_or_forced_process_kill(recipe: str) -> None:
    """Uninstall keeps user data and never force-closes unrelated processes."""
    assert "[UninstallDelete]" not in recipe
    assert "[UninstallRun]" not in recipe
    directives = "\n".join(
        line for line in recipe.splitlines() if not line.lstrip().startswith(";")
    ).lower()
    assert "taskkill" not in directives
    assert "dontcopy" not in directives
    assert "external" not in directives


def test_recipe_has_no_external_calls_and_blocks_in_place_updates(recipe: str) -> None:
    """No network access during install; existing installs are refused clearly."""
    assert "http://" not in recipe
    assert "https://" not in recipe
    assert "RegQueryStringValue" in recipe
    assert "InitializeSetup" in recipe
    assert "ExistingInstallBlocked" in recipe
    # /SUPPRESSMSGBOXES must dismiss the block box in silent installs.
    assert "SuppressibleMsgBox" in recipe


def test_recipe_asks_to_close_locked_applications_without_restarting_them(
    recipe: str,
) -> None:
    """Locked files prompt the user instead of a generic background kill."""
    assert "CloseApplications=yes" in recipe
    assert "RestartApplications=no" in recipe


def test_recipe_carries_traceable_identity_and_new_output(recipe: str) -> None:
    """Identity, version build id and output selection are explicit defines."""
    assert "AppId={{40301115-8D29-4D37-A067-F025278BCDC0}" in recipe
    assert "OutputDir={#MyOutputDir}" in recipe
    assert "OutputBaseFilename={#MyOutputBaseFilename}" in recipe
    assert "build {#MyBuildId}" in recipe
    assert "ArchitecturesAllowed=x64compatible" in recipe


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("2.0.0", "2.0.0.0"),
        ("1", "1.0.0.0"),
        ("3.4.5.6.7", "3.4.5.6"),
    ],
)
def test_numeric_version_is_four_numeric_parts(version: str, expected: str) -> None:
    assert build_installer.numeric_version(version) == expected


def test_iscc_command_supplies_every_recipe_define(tmp_path: Path) -> None:
    command = build_installer.iscc_command(
        Path("ISCC.exe"),
        Path("SLMEducator.iss"),
        payload_dir=tmp_path / "payload",
        output_dir=tmp_path / "out",
        version="2.0.0",
        build_id="abc123",
        base_filename="SLMEducator-Setup-2.0.0-abc123",
    )
    joined = "\n".join(command)
    for key in (
        "MyPayloadDir",
        "MyAppVersion",
        "MyNumericVersion",
        "MyBuildId",
        "MyOutputDir",
        "MyOutputBaseFilename",
    ):
        assert f"/D{key}=" in joined
    assert command[-1] == "SLMEducator.iss"
    assert command[0] == "ISCC.exe"


def test_build_reuses_the_maintained_production_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installer payload must come from build_package.py --prod."""
    monkeypatch.setattr(build_installer.sys, "platform", "win32")
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        commands.append(list(command))
        if "build_package.py" in str(command[1]):
            target = Path(command[command.index("--output-dir") + 1])
            target.mkdir(parents=True)
            for name in (
                build_installer.PAYLOAD_EXECUTABLE,
                *build_installer.USER_DATA_FILES,
            ):
                (target / name).write_text("synthetic")
        return subprocess.CompletedProcess(command, 0)

    iscc = tmp_path / "ISCC.exe"
    iscc.write_text("synthetic compiler stub")
    monkeypatch.setattr(build_installer.subprocess, "run", fake_run)
    payload = tmp_path / "payload"
    code = build_installer.main(
        [
            "--payload-dir",
            str(payload),
            "--output-dir",
            str(tmp_path / "out"),
            "--iscc",
            str(iscc),
            "--build-id",
            "abc123",
        ]
    )
    payload_command = next(c for c in commands if "build_package.py" in str(c[1]))
    compile_command = next(c for c in commands if str(c[0]) == str(iscc))
    assert payload_command[1].endswith("build_package.py")
    assert payload_command[2:] == ["--prod", "--output-dir", str(payload)]
    assert f"/DMyPayloadDir={payload}" in compile_command
    assert "/DMyBuildId=abc123" in compile_command
    # The stubbed compiler produced no installer file, so the build fails clearly.
    assert code == 1


def test_existing_payload_or_output_directory_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(build_installer.sys, "platform", "win32")
    existing = tmp_path / "already-there"
    existing.mkdir()
    assert (
        build_installer.main(
            [
                "--payload-dir",
                str(existing),
                "--output-dir",
                str(tmp_path / "new-out"),
                "--iscc",
                str(Path("ISCC.exe")),
            ]
        )
        == 1
    )
    assert (
        build_installer.main(
            [
                "--payload-dir",
                str(tmp_path / "new-payload"),
                "--output-dir",
                str(existing),
                "--iscc",
                str(Path("ISCC.exe")),
            ]
        )
        == 1
    )


def test_success_explains_configured_or_generated_credentials_without_a_handoff_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(build_installer.sys, "platform", "win32")
    payload = tmp_path / "payload"
    output = tmp_path / "out"
    iscc = tmp_path / "ISCC.exe"
    iscc.write_text("synthetic compiler stub")

    def fake_payload(project_root: Path, payload_dir: Path) -> int:
        payload_dir.mkdir()
        for name in (build_installer.PAYLOAD_EXECUTABLE, *build_installer.USER_DATA_FILES):
            (payload_dir / name).write_text("synthetic")
        return 0

    def fake_compile(command, **kwargs):  # type: ignore[no-untyped-def]
        assert command[0] == str(iscc)
        filename = next(value.split("=", 1)[1] for value in command if value.startswith("/DMyOutputBaseFilename="))
        output.mkdir()
        (output / f"{filename}.exe").write_text("synthetic, never executable")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_installer, "build_payload", fake_payload)
    monkeypatch.setattr(build_installer.subprocess, "run", fake_compile)
    assert build_installer.main([
        "--payload-dir", str(payload), "--output-dir", str(output),
        "--iscc", str(iscc), "--build-id", "synthetic",
    ]) == 0
    message = capsys.readouterr().out
    assert "SLM_INITIAL_ADMIN_PASSWORD" in message
    assert "one-time generated password printed by the seeder" in message
    assert "No plaintext credential file is created" in message
    assert "private handoff location" not in message


def test_missing_inno_compiler_reports_a_clear_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(build_installer.sys, "platform", "win32")
    code = build_installer.main(
        [
            "--payload-dir",
            str(tmp_path / "payload"),
            "--output-dir",
            str(tmp_path / "out"),
            "--iscc",
            str(tmp_path / "not-installed" / "ISCC.exe"),
        ]
    )
    assert code == 1
    assert not (tmp_path / "payload").exists()


def test_non_windows_compilation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(build_installer.sys, "platform", "linux")
    with pytest.raises(SystemExit) as error:
        build_installer.main(
            [
                "--payload-dir",
                str(tmp_path / "payload"),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
    assert error.value.code == 2
    assert not (tmp_path / "payload").exists()


def test_batch_wrapper_has_no_destructive_legacy_steps() -> None:
    script = (
        (Path(__file__).resolve().parents[1] / "build_installer.bat").read_text(
            encoding="utf-8"
        )
    ).lower()
    for forbidden in ("taskkill", "del /", "rmdir", "slm_initial_admin_password", "copy "):
        assert forbidden not in script
    assert 'pushd "%~dp0"' in script
    assert "scripts\\build_installer.py %*" in script
