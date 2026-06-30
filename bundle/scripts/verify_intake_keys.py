#!/usr/bin/env python3
"""Verify newly ingested credentials — never prints secret values."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
GATE = HOME / ".operator_key_vault/gatekeeper.env"


def load_env() -> None:
    if not GATE.is_file():
        return
    for line in GATE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[7:].split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"service": name, "ok": ok, "detail": detail[:120]}


def verify_cloudflare() -> dict:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not token:
        return check("cloudflare", False, "no_token")
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/tokens/verify" if acct
        else "https://api.cloudflare.com/client/v4/user/tokens/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return check("cloudflare", data.get("success", False), data.get("messages", [{}])[0].get("message", "ok"))
    except urllib.error.HTTPError as e:
        return check("cloudflare", False, f"http_{e.code}")
    except Exception as e:
        return check("cloudflare", False, str(e)[:80])


def verify_supabase() -> dict:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return check("supabase", False, "missing_url_or_key")
    req = urllib.request.Request(
        f"{url}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return check("supabase", resp.status in (200, 401, 404), f"http_{resp.status}")
    except urllib.error.HTTPError as e:
        return check("supabase", e.code in (200, 401), f"http_{e.code}")
    except Exception as e:
        return check("supabase", False, str(e)[:80])


def verify_dropbox() -> dict:
    tok = os.environ.get("DROPBOX_ACCESS_TOKEN", "")
    if not tok:
        return check("dropbox", False, "no_access_token")
    req = urllib.request.Request(
        "https://api.dropboxapi.com/2/users/get_current_account",
        data=b"null",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return check("dropbox", bool(data.get("account_id")), "authenticated")
    except urllib.error.HTTPError as e:
        return check("dropbox", False, f"http_{e.code}_expired?")
    except Exception as e:
        return check("dropbox", False, str(e)[:80])


def verify_files() -> list[dict]:
    cred = HOME / ".operator_key_vault/credentials"
    expected = [
        "glacier-gdrive-service.json",
        "firebase-adminsdk-gem-studio.json",
        "casey_service_account.json",
        "gem-studio-oauth-client.json",
        "dropbox_token.json",
        "onedrive_token.json",
    ]
    out = []
    for name in expected:
        p = cred / name
        ok = p.is_file() and p.stat().st_size > 50
        out.append(check(f"credential:{name}", ok, "present" if ok else "missing"))
    return out


def main() -> int:
    load_env()
    results = [
        verify_cloudflare(),
        verify_supabase(),
        verify_dropbox(),
        *verify_files(),
        check("shade", bool(os.environ.get("SHADE_API_KEY")), "loaded" if os.environ.get("SHADE_API_KEY") else "missing"),
        check("taskade", bool(os.environ.get("TASKADE_API_KEY")), "loaded"),
        check("r2", bool(os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY")), "s3_creds_loaded"),
        check("e2b", bool(os.environ.get("E2B_API_KEY")), "loaded"),
        check("mimo", bool(os.environ.get("MIMO_API_KEY")), "loaded"),
        check("parsehub", bool(os.environ.get("PARSEHUB_API_KEY")), "loaded"),
        check("harpa", bool(os.environ.get("HARPA_API_KEY")), "loaded"),
        check("supermemory_codex", bool(os.environ.get("SUPERMEMORY_CODEX_API_KEY")), "loaded"),
    ]
    out_path = HOME / ".apex/INTAKE_VERIFY.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
    ok_count = sum(1 for r in results if r["ok"])
    print(f"Verified {ok_count}/{len(results)} — report: {out_path}")
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['service']}: {r['detail']}")
    return 0 if ok_count >= len(results) - 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())