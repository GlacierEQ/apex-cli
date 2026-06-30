#!/usr/bin/env python3
"""Distill Notion operating surface — DBs, routes, commands, live API health."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
CASE = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
NOTION_MD = HOME / ".apex/NOTION_SURFACE.md"
NOTION_JSON = HOME / ".apex/NOTION_SURFACE.json"
WORKERS_MESH = HOME / ".apex/NOTION_WORKERS_MESH.json"
CONSOLIDATE = HOME / "MISSIONS/APEX_INFRASTRUCTURE/apex-github-worker/.apex-notion-consolidate.json"

ACTORS_DB = "71bc7918de324a5dbaf29e2a5f7c1e13"
INTERACTIONS_DB = "e4f961a16ad340b09b99bacee8a3f134"
ACTORS_DS = "94d05d07-79c3-4cab-bc4c-c6358d55ff7e"
INTERACTIONS_DS = "30493940-496a-4521-aabb-9e3384bf6574"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env() -> None:
    for path in (
        HOME / ".operator_key_vault/gatekeeper.env",
        HOME / ".gemini_keys",
        ALPHA / ".env",
    ):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:
                os.environ[k] = v


def _token() -> str:
    return os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY") or ""


def _load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _probe_db(db_id: str) -> dict:
    token = _token()
    if not token:
        return {"ok": False, "error": "no_token"}
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    try:
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        title = "".join(x.get("plain_text", "") for x in data.get("title", []))
        props = list(data.get("properties", {}).keys())
        return {"ok": True, "title": title, "properties": props, "property_count": len(props)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"http_{e.code}", "detail": e.read().decode("utf-8", errors="replace")[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def distill() -> tuple[dict, str]:
    _load_env()
    token = _token()
    actors_probe = _probe_db(ACTORS_DB)
    interactions_probe = _probe_db(INTERACTIONS_DB)
    api_live = actors_probe.get("ok") and interactions_probe.get("ok")

    payload = {
        "at": _now(),
        "case": "1FDV-23-0001009",
        "role": "Control plane OS — actors registry + interactions log + journal import surface",
        "status": {
            "token_present": bool(token),
            "api_live": api_live,
            "module": str(ALPHA / "integrations/notion_sync.py"),
            "nexus": str(ALPHA / "apex_nexus_coordinator.py"),
        },
        "databases": {
            "actors_registry": {
                "id": ACTORS_DB,
                "data_source_id": ACTORS_DS,
                "purpose": "Upsert actors by name (idempotent)",
                "probe": actors_probe,
            },
            "interactions_log": {
                "id": INTERACTIONS_DB,
                "data_source_id": INTERACTIONS_DS,
                "purpose": "Append-only predicate acts / events",
                "probe": interactions_probe,
            },
        },
        "api_surface": {
            "push_actor": "integrations.notion_sync.push_actor",
            "push_interaction": "integrations.notion_sync.push_interaction",
            "push_batch": "integrations.notion_sync.push_extraction_result",
            "nexus_ingest": "apex_nexus_coordinator.py ingest --file <path>",
            "nexus_execute": "apex_nexus_coordinator.py execute --protocol CATACLYSM",
        },
        "actor_fields": [
            "name", "archetype", "role", "organization", "threat_level",
            "section_1983", "rico_nexus", "shadow_faultline", "status",
        ],
        "interaction_fields": [
            "summary", "event_date", "event_type", "constitutional_hook",
            "priority", "confidence_score", "verified", "actionable", "file_name",
            "linked_actor", "actors_involved", "source", "delivery_id", "sha256", "statute_cited",
        ],
        "routing": {
            "legal_ingest": "nexus ingest → notion_sync push",
            "dropbox_watch": "dropbox_watcher → extract → notion push",
            "journal": "CHATGPT_LIFE_RECORD/MONTHLY → manual Notion import (not API zip)",
            "case_os": "Notion = control plane; local CASE_STRUCTURE = canon",
        },
        "paths": {
            "sync_module": str(ALPHA / "integrations/notion_sync.py"),
            "nexus": str(ALPHA / "apex_nexus_coordinator.py"),
            "journal_toolkit": str(CASE / "CHATGPT_LIFE_RECORD/NOTION_AI_TOOLKIT.md"),
            "monthly_index": str(CASE / "CHATGPT_LIFE_RECORD/MONTHLY"),
            "legal_docs": str(ALPHA / "legal_documents"),
            "keys_alpha_env": str(ALPHA / ".env"),
            "keys_gatekeeper": str(HOME / ".operator_key_vault/gatekeeper.env"),
        },
        "workers": {
            "daemon": str(HOME / "scripts/notion_workers_daemon.py"),
            "status": str(HOME / ".apex/notion_workers_status.json"),
            "queue": str(HOME / ".apex/notion_push_queue.jsonl"),
            "local_mesh": ["dropbox", "queue", "legal", "actors"],
            "cloud_waves": _load_json(WORKERS_MESH, {}).get("waves", []),
            "cloud_deploy": str(HOME / "MISSIONS/APEX_INFRASTRUCTURE/notion-workers-mesh/scripts/deploy_waves.py"),
            "github_webhook": _load_json(WORKERS_MESH, {}).get("github_webhook"),
            "consolidate": _load_json(CONSOLIDATE, {}),
        },
        "commands": {
            "status": f"cd {ALPHA} && python3 apex_nexus_coordinator.py status",
            "ingest": f"cd {ALPHA} && python3 apex_nexus_coordinator.py ingest --file <doc>",
            "cataclysm": f"cd {ALPHA} && python3 apex_nexus_coordinator.py execute --protocol CATACLYSM",
            "watch": f"cd {ALPHA} && python3 apex_nexus_coordinator.py watch",
            "distill": "sm-ops notion-distill",
            "workers": "sm-ops notion-workers --daemon",
            "smoke": f"cd {ALPHA} && python3 integrations/notion_sync.py",
        },
        "fix_if_401": [
            "Regenerate integration token at https://www.notion.so/my-integrations",
            "Share Actors + Interactions DBs with the integration",
            "Update NOTION_TOKEN in apex-fs-commander-alpha/.env",
            "Mirror to gatekeeper.env as NOTION_API_KEY",
            "Re-run: sm-ops notion-distill",
        ],
    }

    api_label = "LIVE" if api_live else ("TOKEN SET / API 401" if token else "NO TOKEN")
    md = f"""# Notion Operating Surface

**Case:** 1FDV-23-0001009 | **Distilled:** {_now()[:19]}Z

## Status

| Signal | Value |
|--------|-------|
| API | **{api_label}** |
| Token | {'present' if token else 'missing'} |
| Module | `integrations/notion_sync.py` |
| Nexus | `apex_nexus_coordinator.py` |

## Databases (APEX control plane)

| DB | ID | Role |
|----|-----|------|
| Actors Registry | `{ACTORS_DB}` | Upsert by name |
| Interactions Log | `{INTERACTIONS_DB}` | Append events |

Data sources: Actors `{ACTORS_DS}` · Interactions `{INTERACTIONS_DS}`

## Push surface

| Function | Behavior |
|----------|----------|
| `push_actor` | Idempotent upsert → Actors DB |
| `push_interaction` | Append → Interactions DB |
| `push_extraction_result` | Batch actors + interactions |

## Ingest routes

```text
legal_documents/ → CATACLYSM execute → Notion push
dropbox_watcher  → extract actors/events → Notion push
nexus ingest     → single file → Notion push
MONTHLY journal  → manual Notion page import (not 5GB zip)
```

## Commands

```bash
cd {ALPHA}
python3 apex_nexus_coordinator.py status
python3 apex_nexus_coordinator.py ingest --file <path>
python3 apex_nexus_coordinator.py execute --protocol CATACLYSM
python3 apex_nexus_coordinator.py watch
sm-ops notion-distill
```

## Actor archetypes (auto-map)

Judge → Judicial Officer · Attorney → Attorney · Agency → Regulatory Node · Witness → Witness · Adverse Party → Adverse Party

## Constitutional hooks (interactions)

§1983 Color of Law · RICO Pattern · 14th Amendment · 1st Amendment Retaliation · Brady · Void Judgment · Parental Rights

## Cloud worker waves (durable)

| Wave | Worker | Tools |
|------|--------|-------|
"""
    waves = _load_json(WORKERS_MESH, {}).get("waves", [])
    for w in waves:
        tools = ", ".join(w.get("tools", w.get("webhooks", [])))
        md += f"| {w.get('wave')} | `{w.get('name')}` | {tools} |\n"
    wh = _load_json(WORKERS_MESH, {}).get("github_webhook", "")
    if wh:
        md += f"\nGitHub webhook: `{wh[:80]}...`\n"
    md += f"\nDeploy: `python3 {HOME}/MISSIONS/APEX_INFRASTRUCTURE/notion-workers-mesh/scripts/deploy_waves.py`\n\n"
    if not api_live and token:
        md += """## Fix (API 401)

1. Regenerate token at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share both DBs with the integration
3. Update `NOTION_TOKEN` in `apex-fs-commander-alpha/.env`
4. `sm-ops notion-distill` to verify

"""
    md += f"*Machine card: `{NOTION_JSON}`*\n"
    return payload, md


def main() -> int:
    HOME.joinpath(".apex").mkdir(parents=True, exist_ok=True)
    payload, md = distill()
    NOTION_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    NOTION_MD.write_text(md, encoding="utf-8")
    print(f"[notion] {NOTION_MD}")
    print(f"[json]   {NOTION_JSON}")
    print(md[:1400])
    return 0 if payload["status"]["api_live"] else 1


if __name__ == "__main__":
    raise SystemExit(main())