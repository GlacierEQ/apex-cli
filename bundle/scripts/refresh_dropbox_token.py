#!/usr/bin/env python3
"""Refresh Dropbox OAuth token and update gatekeeper + credentials JSON."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
GATE = HOME / ".operator_key_vault/gatekeeper.env"
TOKEN_PATH = HOME / ".operator_key_vault/credentials/dropbox_token.json"
OAUTH_URL = "https://api.dropbox.com/oauth2/token"


def _load_env() -> None:
    if not GATE.is_file():
        return
    for line in GATE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("export ") or "=" not in line:
            continue
        k, v = line[7:].split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _refresh(client_id: str, client_secret: str, refresh_token: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()
    req = urllib.request.Request(
        OAUTH_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _verify(access_token: str) -> dict:
    req = urllib.request.Request(
        "https://api.dropboxapi.com/2/users/get_current_account",
        data=b"null",
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _update_gatekeeper(access_token: str) -> None:
    text = GATE.read_text(encoding="utf-8")
    if 'export DROPBOX_ACCESS_TOKEN="' in text:
        text = re.sub(
            r'export DROPBOX_ACCESS_TOKEN="[^"]*"',
            f'export DROPBOX_ACCESS_TOKEN="{access_token}"',
            text,
            count=1,
        )
    else:
        text += f'\nexport DROPBOX_ACCESS_TOKEN="{access_token}"\n'
    GATE.write_text(text, encoding="utf-8")


def _from_rclone() -> dict | None:
    try:
        proc = __import__("subprocess").run(
            ["rclone", "config", "show", "dropbox"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            if line.strip().startswith("token = "):
                raw = line.split("=", 1)[1].strip()
                return json.loads(raw)
    except Exception:
        return None
    return None


def main() -> int:
    import sys

    _load_env()
    if "--from-rclone" in sys.argv:
        blob = _from_rclone()
        if not blob or not blob.get("access_token"):
            print(json.dumps({"ok": False, "error": "rclone_dropbox_token_missing"}))
            return 1
        access = blob["access_token"]
        payload = {
            "access_token": access,
            "token_type": blob.get("token_type", "bearer"),
            "refresh_token": blob.get("refresh_token", ""),
            "expires_in": blob.get("expires_in", 14400),
            "expiry": blob.get("expiry", ""),
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "source": "rclone",
        }
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _update_gatekeeper(access)
        if blob.get("refresh_token"):
            text = GATE.read_text(encoding="utf-8")
            text = re.sub(
                r'export DROPBOX_REFRESH_TOKEN="[^"]*"',
                f'export DROPBOX_REFRESH_TOKEN="{blob["refresh_token"]}"',
                text,
                count=1,
            )
            GATE.write_text(text, encoding="utf-8")
        account = _verify(access)
        print(
            json.dumps(
                {
                    "ok": True,
                    "source": "rclone",
                    "account": account.get("email", "unknown"),
                    "expires_in": payload["expires_in"],
                }
            )
        )
        return 0

    client_id = os.environ.get("DROPBOX_APP_KEY") or os.environ.get("DROPBOX_KEY", "")
    client_secret = os.environ.get("DROPBOX_APP_SECRET") or os.environ.get(
        "DROPBOX_SECRET", ""
    )
    refresh = os.environ.get("DROPBOX_REFRESH_TOKEN", "")

    if TOKEN_PATH.is_file():
        try:
            saved = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            refresh = refresh or saved.get("refresh_token", "")
        except json.JSONDecodeError:
            pass

    if not all([client_id, client_secret, refresh]):
        print(json.dumps({"ok": False, "error": "missing_dropbox_oauth_credentials"}))
        return 1

    try:
        tokens = _refresh(client_id, client_secret, refresh)
    except Exception:
        blob = _from_rclone()
        if blob and blob.get("access_token"):
            sys.argv.append("--from-rclone")
            return main()
        print(
            json.dumps({"ok": False, "error": "refresh_failed_and_no_rclone_fallback"})
        )
        return 1

    access = tokens.get("access_token", "")
    if not access:
        print(json.dumps({"ok": False, "error": "no_access_token_in_response"}))
        return 1

    payload = {
        "access_token": access,
        "token_type": tokens.get("token_type", "bearer"),
        "refresh_token": tokens.get("refresh_token", refresh),
        "expires_in": tokens.get("expires_in", 14400),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _update_gatekeeper(access)

    try:
        account = _verify(access)
        email = account.get("email", "unknown")
        name = account.get("name", {}).get("display_name", "")
        print(
            json.dumps(
                {
                    "ok": True,
                    "account": email,
                    "display_name": name,
                    "token_path": str(TOKEN_PATH),
                    "expires_in": payload["expires_in"],
                }
            )
        )
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"verify_failed: {str(e)[:200]}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
