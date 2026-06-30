#!/usr/bin/env python3
"""Distill APEX operating surface — one card, all signal, minimum tokens."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
APEX = HOME / ".apex"
CASE = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
OMEGA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega"

SURFACE_MD = APEX / "OPERATING_SURFACE.md"
SURFACE_JSON = APEX / "OPERATING_SURFACE.json"

SOURCES = {
    "workflow": APEX / "WORKFLOW_ROUTER.json",
    "connectors": APEX / "CONNECTOR_MESH.json",
    "elevation": APEX / "helix_elevation_status.json",
    "file_access": APEX / "file_sources_access_report.json",
    "pointer": APEX / "POINTER_INDEX.json",
    "vault": HOME / ".operator_key_vault/key_manifest.json",
    "omega": APEX / "omega_orchestrator_status.json",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _run(cmd: list[str], timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(HOME))
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _proc_count() -> str:
    try:
        n = len([p for p in os.listdir("/proc") if p.isdigit()])
        return f"{n}/40 raised"
    except OSError:
        return "unknown"


def distill() -> tuple[dict, str]:
    wf = _load(SOURCES["workflow"])
    conn = _load(SOURCES["connectors"])
    elev = _load(SOURCES["elevation"])
    access = _load(SOURCES["file_access"])
    vault = _load(SOURCES["vault"])
    omega = _load(SOURCES["omega"])

    keys = vault.get("total_keys", 156)
    obs = elev.get("alpha", {}).get("observations", 0)
    pistons = omega.get("pistons_online", elev.get("omega", {}).get("pistons_online", 0))
    tokens_saved = 0
    tok_out = _run(["sm-ops", "tokens"])
    for line in tok_out.splitlines():
        if "Tokens saved" in line:
            try:
                tokens_saved = int(line.split("~:")[-1].replace(",", "").strip())
            except ValueError:
                pass

    payload = {
        "at": _now(),
        "profile": "coremaximized",
        "case": "1FDV-23-0001009",
        "identity": "Double Helix — Alpha observation + Omega shield",
        "status": {
            "keys": keys,
            "observations": obs,
            "pistons": pistons,
            "tokens_saved": tokens_saved,
            "file_sources": f"{access.get('hot_paths', {}).get('ok', 0)}/{access.get('hot_paths', {}).get('total', 10)}",
            "processes": _proc_count(),
            "notion": elev.get("alpha", {}).get("notion_online", True),
        },
        "workflow": "boot → plan → execute → verify → save",
        "mcp": {
            "supreme": "colossus-gatekeeper",
            "direct": conn.get("grok_mcp", ["colossus-gatekeeper", "apex-filesystem", "unified-memory"]),
            "gemini_cloud": conn.get("routing", {}).get("cloud_files", "gdrive|dropbox|onedrive"),
        },
        "routing": {
            "filesystem": "gatekeeper safe_read/hash OR apex-filesystem",
            "memory": "sm-ops prime OR unified-memory",
            "storage": "sm-ops fs-commander / helix-elevate",
            "risky_writes": "gatekeeper gate_action → Colossus",
            "legal": "nexus_ingest / digital-law-library-master",
            "notion": str(HOME / ".apex/NOTION_SURFACE.md"),
        },
        "paths": {
            "surface": str(SURFACE_MD),
            "boot": str(APEX / "AGENT_BOOT.md"),
            "live_context": str(HOME / ".supermemory/ops/live-context.md"),
            "alpha": str(ALPHA),
            "omega": str(OMEGA),
            "case": str(CASE),
            "evidence": str(CASE / "EVIDENCE"),
            "journal": str(CASE / "CHATGPT_LIFE_RECORD"),
            "by_actor": str(CASE / "EVIDENCE/BY_ACTOR"),
            "keys": str(HOME / ".operator_key_vault/gatekeeper.env"),
            "grok": str(HOME / ".grok/config.toml"),
        },
        "commands": {
            "prime": 'sm-ops prime "task" --max-tokens 1000',
            "save": 'sm-ops save "outcome" --durable',
            "maximize": "sm-ops maximize",
            "elevate": "sm-ops helix-elevate",
            "health": f"cd {ALPHA} && ./run_apex.sh health",
            "file_test": "python3 ~/scripts/test_file_sources_access.py",
            "surface": "python3 ~/scripts/apex_distill_surface.py",
            "guard": "bash ~/MISSIONS/SUPPORTING_DATA/UNSORTED/scripts/guard_signal9.sh",
        },
        "task_skills": wf.get("task_routing", {}),
        "rules": wf.get("logic_rules", [])[:7],
        "hot_file_sources": [
            {"name": k, "path": v.get("path"), "ok": v.get("ok")}
            for k, v in zip(
                [r["name"] for r in access.get("hot_paths", {}).get("results", [])],
                access.get("hot_paths", {}).get("results", []),
            )
        ] if access.get("hot_paths") else [],
    }

    md = f"""# APEX Operating Surface

**Case:** 1FDV-23-0001009 | **Profile:** coremaximized | **Distilled:** {_now()[:19]}Z

## Live status

| Signal | Value |
|--------|-------|
| Keys | {keys} |
| Observations | {obs:,} |
| Omega pistons | {pistons}/12 |
| File sources | {payload['status']['file_sources']} OK |
| Token savings | ~{tokens_saved:,} |
| Processes | {payload['status']['processes']} |
| Notion | {'Online' if payload['status']['notion'] else 'Degraded'} |

## Workflow

`boot → plan → execute → verify → save`

## MCP stack

| Role | Route |
|------|-------|
| Supreme | `colossus-gatekeeper` |
| Filesystem | `apex-filesystem` (12 tools) |
| Memory | `unified-memory` + `sm-ops` |
| Cloud | Gemini: gdrive / dropbox / onedrive |
| Risky writes | `gate_action` first |

## Path index

| Resource | Path |
|----------|------|
| Alpha | `{payload['paths']['alpha']}` |
| Omega | `{payload['paths']['omega']}` |
| Case | `{payload['paths']['case']}` |
| Evidence | `{payload['paths']['evidence']}` |
| Journal | `{payload['paths']['journal']}` |
| By actor | `{payload['paths']['by_actor']}` |
| Keys | `{payload['paths']['keys']}` |

## Commands (copy-paste)

```bash
sm-ops prime "task" --max-tokens 1000
sm-ops save "outcome" --durable
sm-ops maximize && sm-ops helix-elevate
python3 ~/scripts/test_file_sources_access.py
cd {ALPHA} && ./run_apex.sh health
```

## Task → skill

| Task | Skills |
|------|--------|
| coding | helix-pro-code, token-savings |
| memory | sm-ops, memory-connect |
| storage | fs-commander, helix-elevate |
| legal | digital-law-library-master |
| infra | apex-pillars, sovereign-operator |

## Rules

"""
    for rule in payload["rules"]:
        md += f"- {rule}\n"

    md += f"\n*Machine card: `{SURFACE_JSON}`*\n"
    return payload, md


def main() -> int:
    APEX.mkdir(parents=True, exist_ok=True)
    payload, md = distill()
    SURFACE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    SURFACE_MD.write_text(md, encoding="utf-8")

    # Slim boot pointer
    boot = APEX / "AGENT_BOOT.md"
    pointer = f"# APEX Agent Boot\n\n**Read first:** `{SURFACE_MD}` (~compact operating surface)\n\nThen: `~/.supermemory/ops/live-context.md` for primed memory.\n\n*Distilled {_now()[:19]}Z*\n"
    boot.write_text(pointer, encoding="utf-8")

    print(f"[surface] {SURFACE_MD}")
    print(f"[json]    {SURFACE_JSON}")
    print(f"[boot]    {boot} → points to surface")
    print(md[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())