"""Opt-in synthetic packaged first login and password rotation over loopback."""

import argparse
import json
from pathlib import Path
import secrets

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if not args.base_url.startswith("http://127.0.0.1:"):
        raise SystemExit("Synthetic loopback installation only")
    original = args.password_file.read_text(encoding="utf-8-sig").strip()
    rotated = secrets.token_urlsafe(24) + "A1!"
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=10) as client:
        assert client.get("/login.html").status_code == 200
        login = client.post("/api/auth/login", data={"username": "admin", "password": original})
        assert login.status_code == 200
        token = login.json()["access_token"]
        changed = client.post("/api/auth/change-password", headers={"Authorization": "Bearer " + token},
                              json={"current_password": original, "new_password": rotated})
        assert changed.status_code == 200
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401
        assert client.post("/api/auth/login", data={"username": "admin", "password": rotated}).status_code == 200
    args.password_file.with_name("rotated-synthetic-password.txt").write_text(rotated, encoding="utf-8")
    args.receipt.write_text(json.dumps({"login": "pass", "password_rotation": "pass", "old_session_revoked": "pass"}), encoding="utf-8")


if __name__ == "__main__":
    main()
