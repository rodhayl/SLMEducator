"""Source/build binding and source-free runtime checks using synthetic inputs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import build_package as builder
from src.frontend_delivery import frontend_source_digest, validate_frontend_dist
from tests.fixtures.frontend_artifact import make_frontend


@pytest.mark.parametrize("name", ["index.html", "package.json", "tsconfig.json", "vite.config.ts", "scripts/build.mjs",
                                  "src/main.tsx", "src/styles.css", "public/logo.svg"])
def test_changed_build_input_rejects_previously_valid_dist(tmp_path: Path, name: str) -> None:
    dist = make_frontend(tmp_path)
    assert validate_frontend_dist(dist, source_root=dist.parent)
    changed = dist.parent / name
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("changed build input\n")
    with pytest.raises(ValueError, match="does not match current source inputs"):
        validate_frontend_dist(dist, source_root=dist.parent)
    # Runtime verifies the packaged bytes and embedded identity, without sources.
    assert validate_frontend_dist(dist)


def test_excluded_build_outputs_and_dependencies_do_not_change_source_identity(tmp_path: Path) -> None:
    dist = make_frontend(tmp_path)
    expected = frontend_source_digest(dist.parent)
    for name in ("dist/unused.bin", "node_modules/ignored.js", "README.md", "CONTRACTS.md", ".env.production"):
        file = dist.parent / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("not a production source input")
    assert frontend_source_digest(dist.parent) == expected


@pytest.mark.parametrize("name", ["src/main.tsx", "src", "scripts", "public"])
def test_source_links_are_rejected_without_traversal(tmp_path: Path, name: str) -> None:
    dist = make_frontend(tmp_path)
    file = dist.parent / name
    target = tmp_path / "outside"
    if file.exists():
        shutil.move(str(file), target)
    else:
        target.mkdir()
    file.symlink_to(target, target_is_directory=target.is_dir())
    with pytest.raises(ValueError, match="Symlinked frontend source"):
        frontend_source_digest(dist.parent)


def test_node_and_python_source_identity_use_identical_bytes_and_order(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed only to exercise the build-side implementation")
    dist = make_frontend(tmp_path)
    for name in ("src/á.tsx", "src/😀.css", "src/Ａ.css", "public/icon.svg"):
        file = dist.parent / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"first\r\nsecond\n\0binary")
    module = Path(__file__).resolve().parents[1] / "src/frontend/scripts/source-identity.mjs"
    result = subprocess.run([node, "--input-type=module", "-e",
                             f"import {{ frontendSourceDigest }} from {json.dumps(module.as_uri())};"
                             "console.log(await frontendSourceDigest(process.argv[1]));", str(dist.parent)],
                            check=True, text=True, capture_output=True)
    assert result.stdout.strip() == frontend_source_digest(dist.parent)


def test_manifest_tool_cannot_reseal_old_output_by_itself(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed only to exercise the build command")
    dist = make_frontend(tmp_path)
    manifest = (dist / "build-manifest.json").read_bytes()
    module = Path(__file__).resolve().parents[1] / "src/frontend/scripts/build-manifest.mjs"
    result = subprocess.run([node, str(module)], cwd=dist.parent, text=True, capture_output=True)
    assert result.returncode != 0
    assert "Use npm run build" in result.stderr
    assert (dist / "build-manifest.json").read_bytes() == manifest


def test_staged_frontend_serves_after_source_removed_without_node(tmp_path: Path) -> None:
    project = tmp_path / "checkout"
    dist = make_frontend(project)
    package = tmp_path / "package"
    bundle = package / "_internal"
    target = bundle / "src/frontend/dist"
    shutil.copytree(dist, target)
    (bundle / "src/__init__.py").write_text("")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "src/frontend_delivery.py", bundle / "src/frontend_delivery.py")
    shutil.rmtree(project)
    environment = {**os.environ, "PATH": "", "PYTHONPATH": str(bundle)}
    environment.pop("SLM_FRONTEND_DIR", None)
    environment.pop("SLM_WEB_DIR", None)
    probe = """
from pathlib import Path
import shutil, sys
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.frontend_delivery import register_frontend, resolve_frontend_dir, validate_frontend_dist
assert shutil.which('node') is None and shutil.which('npm') is None
package = Path(sys.argv[1])
sys.frozen = True
sys.executable = str(package / 'SLMEducator.exe')
sys._MEIPASS = str(package / '_internal')
base, dist = resolve_frontend_dir()
assert base == package
assert not (dist.parent / 'src').exists()
assert not (dist.parent / 'package-lock.json').exists()
assert validate_frontend_dist(dist)
app = FastAPI()
register_frontend(app, dist)
with TestClient(app) as client:
    assert client.get('/').status_code == 200
    assert client.get('/cursos/12').status_code == 200
    assert client.get('/assets/index-12345678.js').status_code == 200
print('source-free and Node-free frontend delivery passed')
"""
    result = subprocess.run([sys.executable, "-c", probe, str(package)], cwd=bundle, env=environment,
                            check=True, text=True, capture_output=True)
    assert "source-free and Node-free frontend delivery passed" in result.stdout


def test_packaging_checks_source_again_after_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "checkout"
    make_frontend(project)
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(builder, "RUNTIME_FILES", ())
    monkeypatch.setattr(builder, "RUNTIME_TREES", {})
    original = builder._copy_file

    def copy_and_change_source(root: Path, output: Path, relative: Path) -> None:
        original(root, output, relative)
        if relative.as_posix().endswith("build-manifest.json"):
            (root / "src/frontend/src/main.tsx").write_text("changed while staging")

    monkeypatch.setattr(builder, "_copy_file", copy_and_change_source)
    with pytest.raises(ValueError, match="does not match current source inputs"):
        builder._copy_inputs(project, staging)


def test_build_cannot_seal_sources_changed_during_compilation(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed only to exercise the build-side seal")
    dist = make_frontend(tmp_path)
    lock = {"packages": {"node_modules/tailwindcss": {"dev": True}}}
    (dist.parent / "package-lock.json").write_text(json.dumps(lock))
    before = frontend_source_digest(dist.parent)
    (dist / "build-manifest.json").unlink()
    (dist.parent / "src/styles.css").write_text("changed while compiling")
    module = Path(__file__).resolve().parents[1] / "src/frontend/scripts/build-manifest.mjs"
    result = subprocess.run([node, "--input-type=module", "-e",
                             f"import {{ writeBuildManifest }} from {json.dumps(module.as_uri())};"
                             "await writeBuildManifest(process.argv[1], process.argv[2]);", str(dist.parent), before],
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "sources changed during build" in result.stderr
    assert not (dist / "build-manifest.json").exists()


def test_failed_canonical_build_invalidates_previous_complete_manifest(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed only to exercise the canonical build command")
    dist = make_frontend(tmp_path)
    source = Path(__file__).resolve().parents[1] / "src/frontend/scripts"
    for module in source.glob("*.mjs"):
        shutil.copyfile(module, dist.parent / "scripts" / module.name)
    (dist.parent / "package.json").write_text('{"type":"module"}\n')
    compiler = dist.parent / "node_modules/typescript/bin/tsc"
    compiler.parent.mkdir(parents=True)
    compiler.write_text("console.log(JSON.stringify({key:process.env.VITE_SYNTHETIC_KEY||null, mode:process.env.NODE_ENV}));process.exit(42);\n")
    result = subprocess.run([node, str(dist.parent / "scripts/build.mjs")], cwd=dist.parent,
                            env={**os.environ, "VITE_SYNTHETIC_KEY": "synthetic build input", "NODE_ENV": "development"},
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "Frontend build tool failed: typescript/bin/tsc" in result.stderr
    assert json.loads(result.stdout) == {"key": None, "mode": "production"}
    assert not (dist / "build-manifest.json").exists()
    with pytest.raises(ValueError, match="missing or unreadable"):
        validate_frontend_dist(dist)
