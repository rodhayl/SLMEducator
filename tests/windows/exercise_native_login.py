"""Opt-in synthetic packaged first login and password rotation over loopback."""

import argparse
import json
import re
import secrets
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def verify_react_delivery(client: httpx.Client) -> None:
    """Verify the compatibility redirect and integrity-tagged React delivery."""
    legacy = client.get("/login.html", follow_redirects=False)
    assert legacy.status_code == 307
    assert legacy.headers.get("location") == "/entrar"
    page = client.get("/entrar", follow_redirects=False)
    assert page.status_code == 200
    assert page.headers.get("content-type", "").startswith("text/html")
    assert page.headers.get("x-content-type-options") == "nosniff"
    assert page.headers.get("etag") == '"' + sha256(page.content).hexdigest() + '"'
    assert 'id="root"' in page.text
    assets = re.findall(r'(?:src|href)="(/assets/[A-Za-z0-9_./-]+)"', page.text)
    assert any(path.endswith(".js") for path in assets), (
        "Verified React entry is missing"
    )
    for path in assets:
        asset = client.get(path, follow_redirects=False)
        assert asset.status_code == 200
        assert (
            asset.headers.get("etag") == '"' + sha256(asset.content).hexdigest() + '"'
        )
        assert not asset.headers.get("content-type", "").startswith("text/html")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = urlsplit(args.base_url)
    if (
        base.scheme != "http"
        or base.hostname != "127.0.0.1"
        or not base.port
        or base.username
        or base.password
        or base.path not in {"", "/"}
        or base.query
        or base.fragment
    ):
        raise SystemExit("Synthetic loopback installation only")
    original = args.password_file.read_text(encoding="utf-8-sig").strip()
    rotated = secrets.token_urlsafe(24) + "A1!"
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=10) as client:
        verify_react_delivery(client)
        login = client.post(
            "/api/auth/login", data={"username": "admin", "password": original}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        changed = client.post(
            "/api/auth/change-password",
            headers={"Authorization": "Bearer " + token},
            json={"current_password": original, "new_password": rotated},
        )
        assert changed.status_code == 200
        assert (
            client.get(
                "/api/auth/me", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login", data={"username": "admin", "password": rotated}
            ).status_code
            == 200
        )
    args.password_file.with_name("rotated-synthetic-password.txt").write_text(
        rotated, encoding="utf-8"
    )
    args.receipt.write_text(
        json.dumps(
            {
                "legacy_redirect": "pass",
                "verified_react_delivery": "pass",
                "login": "pass",
                "password_rotation": "pass",
                "old_session_revoked": "pass",
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
