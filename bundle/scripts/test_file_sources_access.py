#!/usr/bin/env python3
"""Test file source access across FS Commander allowed roots and hot paths."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
CASE = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
OUT = HOME / ".apex/file_sources_access_report.json"

HOT_PATHS = {
    "alpha": ALPHA,
    "omega": HOME
    / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega",
    "case_root": CASE,
    "journal": CASE / "CHATGPT_LIFE_RECORD",
    "by_actor": CASE / "EVIDENCE/BY_ACTOR",
    "keep_registry": HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep",
    "gatekeeper_env": HOME / ".operator_key_vault/gatekeeper.env",
    "app_catalog": HOME / "MISSIONS/APP_CATALOG/MANIFEST.md",
    "apex_gateway": HOME / "apex-gateway",
    "agent_boot": HOME / ".apex/AGENT_BOOT.md",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe_path(name: str, path: Path) -> dict:
    p = path.expanduser()
    if not p.exists():
        return {"name": name, "path": str(p), "ok": False, "error": "missing"}
    if p.is_file():
        try:
            st = p.stat()
            readable = os.access(p, os.R_OK)
            return {
                "name": name,
                "path": str(p),
                "type": "file",
                "ok": readable,
                "size_bytes": st.st_size,
                "readable": readable,
            }
        except OSError as e:
            return {"name": name, "path": str(p), "ok": False, "error": str(e)}
    try:
        entries = list(p.iterdir())
        readable = os.access(p, os.R_OK | os.X_OK)
        return {
            "name": name,
            "path": str(p),
            "type": "dir",
            "ok": readable,
            "entries_count": len(entries),
            "readable": readable,
            "sample": sorted(x.name for x in entries[:5]),
        }
    except OSError as e:
        return {"name": name, "path": str(p), "ok": False, "error": str(e)}


async def test_filesystem_mcp() -> list[dict]:
    sys.path.insert(0, str(ALPHA / "servers"))
    import apex_filesystem_mcp as mcp

    tests = []
    for name, args, expect in [
        ("list_allowed_roots", {}, "Allowed roots"),
        ("list_directory", {"path": str(HOME / "apex-gateway")}, "[FILE]"),
        ("hash_file", {"path": str(HOME / ".apex/AGENT_BOOT.md")}, "SHA256"),
        ("read_file", {"path": str(HOME / ".apex/POINTER_INDEX.json")}, "mcp_routing"),
        (
            "search_files",
            {"root": str(CASE), "pattern": "EVIDENCE", "max_depth": 3},
            "Found",
        ),
    ]:
        try:
            out = await mcp._dispatch(name, args)
            ok = expect in str(out)
            tests.append({"tool": name, "ok": ok, "preview": str(out)[:100]})
        except Exception as e:
            tests.append({"tool": name, "ok": False, "error": str(e)})
    return tests


def test_gatekeeper() -> list[dict]:
    sys.path.insert(0, str(HOME / "scripts"))
    os.environ.setdefault("APEX_ROOT", str(HOME))
    import colossus_gatekeeper_mcp as gk

    results = []
    try:
        boot = json.loads(gk.safe_read(str(HOME / ".apex/AGENT_BOOT.md"), 800))
        results.append({"tool": "gatekeeper_safe_read", "ok": boot.get("chars", 0) > 0})
    except Exception as e:
        results.append({"tool": "gatekeeper_safe_read", "ok": False, "error": str(e)})

    try:
        h = json.loads(gk.safe_hash(str(HOME / ".apex/POINTER_INDEX.json")))
        results.append(
            {"tool": "gatekeeper_safe_hash", "ok": len(h.get("sha256", "")) == 64}
        )
    except Exception as e:
        results.append({"tool": "gatekeeper_safe_hash", "ok": False, "error": str(e)})

    try:
        roots = json.loads(gk.list_case_roots())
        results.append(
            {
                "tool": "gatekeeper_case_roots",
                "ok": all(
                    k in roots for k in ("CASE_ROOT", "EVIDENCE_ROOT", "journal")
                ),
            }
        )
    except Exception as e:
        results.append({"tool": "gatekeeper_case_roots", "ok": False, "error": str(e)})

    try:
        outside = json.loads(gk.safe_read("/etc/passwd", 100))
        results.append({"tool": "gatekeeper_sandbox_deny", "ok": "error" in outside})
    except Exception:
        results.append({"tool": "gatekeeper_sandbox_deny", "ok": True})

    return results


def test_master_fs() -> list[dict]:
    sys.path.insert(0, str(ALPHA))
    from servers.apex_master_mcp import fs_list_directory, fs_read_file

    results = []
    for name, path in [
        ("master_list_alpha", str(ALPHA)),
        ("master_list_case", str(CASE)),
        ("master_read_boot", str(HOME / ".apex/AGENT_BOOT.md")),
    ]:
        try:
            if "read" in name:
                r = fs_read_file(path)
                ok = "content" in r or "error" not in r
            else:
                r = fs_list_directory(path)
                ok = r.get("entries_count", 0) > 0
            results.append(
                {
                    "tool": name,
                    "ok": ok,
                    "detail": r.get("entries_count") or r.get("size_bytes"),
                }
            )
        except Exception as e:
            results.append({"tool": name, "ok": False, "error": str(e)})
    return results


def test_connector_sources() -> list[dict]:
    checks = []
    candidates = [
        ("dropbox_watcher", ALPHA / "integrations/dropbox_watcher.py"),
        ("dropbox_consolidator", ALPHA / "services/apex_dropbox_consolidator.py"),
        ("dropbox_recovery", ALPHA / "dropbox"),
        ("onedrive_intel", ALPHA / "services/apex_onedrive_intelligence.py"),
        ("observe_script", ALPHA / "scripts/apex_observe_files.py"),
    ]
    for name, path in candidates:
        checks.append(
            {
                "source": name,
                "path": str(path),
                "ok": path.exists(),
                "type": "file"
                if path.is_file()
                else "dir"
                if path.is_dir()
                else "missing",
            }
        )
    return checks


def main() -> int:
    print("=" * 56)
    print("  FILE SOURCES ACCESS TEST")
    print("=" * 56)

    hot = [probe_path(k, v) for k, v in HOT_PATHS.items()]
    hot_ok = sum(1 for h in hot if h.get("ok"))

    print(f"\n[hot_paths] {hot_ok}/{len(hot)} accessible")
    for h in hot:
        mark = "OK" if h.get("ok") else "FAIL"
        extra = h.get("entries_count") or h.get("size_bytes") or h.get("error", "")
        print(f"  [{mark}] {h['name']}: {extra}")

    print("\n[filesystem_mcp]")
    mcp = asyncio.run(test_filesystem_mcp())
    mcp_ok = sum(1 for t in mcp if t.get("ok"))
    for t in mcp:
        print(f"  [{'OK' if t.get('ok') else 'FAIL'}] {t['tool']}")

    print("\n[gatekeeper]")
    gk = test_gatekeeper()
    for t in gk:
        print(f"  [{'OK' if t.get('ok') else 'FAIL'}] {t['tool']}")

    print("\n[master_mcp_fs]")
    master = test_master_fs()
    for t in master:
        print(f"  [{'OK' if t.get('ok') else 'FAIL'}] {t['tool']}")

    print("\n[connector_sources]")
    conn = test_connector_sources()
    conn_ok = sum(1 for c in conn if c.get("ok"))
    for c in conn:
        print(f"  [{'OK' if c.get('ok') else 'FAIL'}] {c['source']} ({c['type']})")

    report = {
        "at": _now(),
        "hot_paths": {"total": len(hot), "ok": hot_ok, "results": hot},
        "filesystem_mcp": {"total": len(mcp), "ok": mcp_ok, "results": mcp},
        "gatekeeper": gk,
        "master_mcp": master,
        "connector_sources": {"total": len(conn), "ok": conn_ok, "results": conn},
        "all_ok": hot_ok == len(hot)
        and mcp_ok == len(mcp)
        and all(t.get("ok") for t in gk + master),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[report] {OUT}")
    print(f"\nSUMMARY: {'ALL PASS' if report['all_ok'] else 'ISSUES FOUND'}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
