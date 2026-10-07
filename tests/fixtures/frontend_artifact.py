"""Tiny synthetic Vite artifact, independent of Node and generated checkout output."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from src.frontend_delivery import frontend_source_digest


def make_frontend(root: Path) -> Path:
    """Create a consistent synthetic lockfile and built frontend under root."""
    frontend = root / "src/frontend"
    dist = frontend / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / ".vite").mkdir()
    (frontend / "src").mkdir()
    (frontend / "scripts").mkdir()
    for name in ("index.html", "package.json", "tsconfig.json", "vite.config.ts", "src/main.tsx", "src/styles.css", "scripts/build.mjs"):
        (frontend / name).write_text("synthetic build input\n", encoding="utf-8")
    (frontend / "package-lock.json").write_text('{"name":"synthetic-frontend","lockfileVersion":3}\n', encoding="utf-8")
    (dist / "index.html").write_text(
        '<!doctype html><html><head><link rel="stylesheet" href="/assets/index-12345678.css">'
        '</head><body><div id="root"></div><script type="module" src="/assets/index-12345678.js"></script></body></html>',
        encoding="utf-8",
    )
    (dist / "assets/index-12345678.js").write_text('document.title = "Synthetic SLM";\n', encoding="utf-8")
    (dist / "assets/index-12345678.css").write_text('body { color: #111; }\n', encoding="utf-8")
    (dist / ".vite/manifest.json").write_text(json.dumps({"index.html": {
        "file": "assets/index-12345678.js", "isEntry": True, "css": ["assets/index-12345678.css"]
    }}), encoding="utf-8")
    (dist / "third-party-notices.json").write_text('{"packages": []}\n', encoding="utf-8")
    refresh_manifest(dist)
    return dist


def refresh_manifest(dist: Path) -> dict[str, Any]:
    """Regenerate hashes after a test intentionally changes synthetic contents."""
    previous = json.loads((dist / "build-manifest.json").read_text()) if (dist / "build-manifest.json").exists() else {}
    manifest = {
        "schema_version": 2,
        "source_identity_version": 1,
        "source_sha256": previous.get("source_sha256") or frontend_source_digest(dist.parent),
        "frontend": "slm-educator",
        "lockfile_sha256": sha256((dist.parent / "package-lock.json").read_bytes()).hexdigest(),
        "assets": [
            {"path": path.relative_to(dist).as_posix(), "size": path.stat().st_size,
             "sha256": sha256(path.read_bytes()).hexdigest()}
            for path in sorted(dist.rglob("*")) if path.is_file() and path.name != "build-manifest.json"
        ],
    }
    (dist / "build-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest
