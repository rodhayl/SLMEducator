#!/usr/bin/env python3
"""Build the minimal maintained Windows installer from a fresh --prod payload.

This script reuses the existing ``scripts/build_package.py --prod`` builder to
create a pristine PyInstaller ``onedir`` payload in a new, absolute directory.
It then compiles ``installer/SLMEducator.iss`` with the Inno Setup command-line
compiler, passing the payload path, version, build id and a new output directory
as compiler defines.

Safety boundaries:

* Both the payload directory and the installer output directory must be new.
* Only new, disposable staging and output directories are written.
* The working database, local configuration and existing installations are not
  read, changed or packaged. The seeded database comes from the maintained
  create-only seeder.
* The initial administrator password is never printed here. Set
  ``SLM_INITIAL_ADMIN_PASSWORD`` in the build process environment (or keep the
  one-time generated value from the seeder) and store it privately.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

APP_NAME = "SLMEducator"
PAYLOAD_EXECUTABLE = "SLMEducator.exe"
# Files inside the payload that are user data, not program files.
USER_DATA_FILES = ("slm_educator.db", "env.properties")


def default_iscc() -> Path | None:
    """Return the first Inno Setup 6 command-line compiler found, if any."""
    candidates = []
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    program_files = os.environ.get("ProgramFiles")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if program_files_x86:
        candidates.append(Path(program_files_x86) / "Inno Setup 6" / "ISCC.exe")
    if program_files:
        candidates.append(Path(program_files) / "Inno Setup 6" / "ISCC.exe")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def git_build_id(project_root: Path) -> str:
    """Return a short commit identifier, or ``unknown`` without a checkout."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def numeric_version(version: str) -> str:
    """Return a four-part numeric version for Windows file properties."""
    parts = re.findall(r"\d+", version)[:4]
    parts.extend(["0"] * (4 - len(parts)))
    return ".".join(parts)


def iscc_command(
    iscc: Path,
    script: Path,
    *,
    payload_dir: Path,
    output_dir: Path,
    version: str,
    build_id: str,
    base_filename: str,
) -> list[str]:
    """Build the Inno Setup compiler command with explicit payload defines."""
    defines = {
        "MyPayloadDir": str(payload_dir),
        "MyAppVersion": version,
        "MyNumericVersion": numeric_version(version),
        "MyBuildId": build_id,
        "MyOutputDir": str(output_dir),
        "MyOutputBaseFilename": base_filename,
    }
    command = [str(iscc)]
    for key, value in defines.items():
        command.append(f"/D{key}={value}")
    command.append(str(script))
    return command


def build_payload(project_root: Path, payload_dir: Path) -> int:
    """Run the maintained production builder into a new payload directory."""
    command = [
        sys.executable,
        str(project_root / "scripts" / "build_package.py"),
        "--prod",
        "--output-dir",
        str(payload_dir),
    ]
    return subprocess.run(command, cwd=str(project_root)).returncode


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, build a pristine payload and compile the installer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--payload-dir",
        type=Path,
        required=True,
        help="New absolute directory for the fresh --prod payload",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New absolute directory for the compiled Setup executable",
    )
    parser.add_argument(
        "--version",
        default="2.0.0",
        help="Application version recorded in the installer",
    )
    parser.add_argument(
        "--build-id",
        default=None,
        help="Build identifier; defaults to the current short source commit",
    )
    parser.add_argument(
        "--iscc",
        type=Path,
        default=None,
        help="Path to Inno Setup 6 ISCC.exe; auto-detected when omitted",
    )
    parser.add_argument(
        "--name",
        default="SLMEducator-Setup",
        help="Installer file base name",
    )
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        parser.error("Windows installers must be built on Windows")

    project_root = Path(__file__).resolve().parent.parent
    payload_dir = args.payload_dir.absolute()
    output_dir = args.output_dir.absolute()
    for path in (payload_dir, output_dir):
        if path.exists() or path.is_symlink():
            print(
                f"[ERROR] Refusing to reuse an existing path: {path}. "
                "Choose a new absolute directory.",
                file=sys.stderr,
            )
            return 1

    iscc = args.iscc or default_iscc()
    if iscc is None or not Path(iscc).is_file():
        print(
            "[ERROR] Inno Setup 6 command-line compiler (ISCC.exe) was not found. "
            "Install Inno Setup 6 or pass --iscc.",
            file=sys.stderr,
        )
        return 1

    script = project_root / "installer" / "SLMEducator.iss"
    if not script.is_file():
        print(f"[ERROR] Installer script not found: {script}", file=sys.stderr)
        return 1

    build_id = args.build_id or git_build_id(project_root)
    base_filename = f"{args.name}-{args.version}-{build_id}"

    print(f"[..] Building production payload: {payload_dir}")
    if build_payload(project_root, payload_dir) != 0:
        print("[ERROR] Payload build failed; installer was not compiled.", file=sys.stderr)
        return 1
    if not (payload_dir / PAYLOAD_EXECUTABLE).is_file():
        print(
            f"[ERROR] Payload is missing {PAYLOAD_EXECUTABLE}; installer not compiled.",
            file=sys.stderr,
        )
        return 1
    for name in USER_DATA_FILES:
        if not (payload_dir / name).is_file():
            print(
                f"[ERROR] Payload is missing {name}; installer not compiled.",
                file=sys.stderr,
            )
            return 1

    command = iscc_command(
        Path(iscc),
        script,
        payload_dir=payload_dir,
        output_dir=output_dir,
        version=args.version,
        build_id=build_id,
        base_filename=base_filename,
    )
    print(f"[..] Compiling installer into: {output_dir}")
    if subprocess.run(command, cwd=str(project_root)).returncode != 0:
        print("[ERROR] Inno Setup compilation failed.", file=sys.stderr)
        return 1
    setup = output_dir / f"{base_filename}.exe"
    if not setup.is_file():
        print(f"[ERROR] Compiled installer not found: {setup}", file=sys.stderr)
        return 1
    print(f"[OK] Installer created: {setup}")
    print(
        "The initial admin password is deliberately not printed here. "
        "Consult the private handoff location."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
