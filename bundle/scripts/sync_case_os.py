#!/usr/bin/env python3
"""
Unify Case OS layers: local canon → Supermemory pointers + Mem0 episodic facts.

Does NOT duplicate raw chats. Pushes summaries with canon: paths for agents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
CASE_ROOT = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
JOURNAL = CASE_ROOT / "CHATGPT_LIFE_RECORD"
BY_ACTOR = CASE_ROOT / "EVIDENCE/BY_ACTOR"
ACTORS = CASE_ROOT / "ACTORS"
STATE_PATH = HOME / ".supermemory/ops/case-os-state.json"
MANIFEST_PATH = CASE_ROOT / "CASE_OS_MANIFEST.json"
NOTION_MANIFEST = CASE_ROOT / "NOTION_PUSH_MANIFEST.json"
SM_TAG = "apex-case"
MEM0_AGENT = "apex-grok"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text())
    return {"synced": {}, "at": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["at"] = _now()
    STATE_PATH.write_text(json.dumps(state, indent=2))


def read_stats() -> dict:
    p = JOURNAL / "stats.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def read_manifest_table() -> list[dict]:
    manifest = BY_ACTOR / "MANIFEST.md"
    if not manifest.is_file():
        return []
    rows = []
    for line in manifest.read_text().splitlines():
        if not line.startswith("|") or "---" in line or "Actor" in line:
            continue
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) >= 4 and parts[0] and not parts[0].startswith("_"):
            rows.append(
                {
                    "actor": parts[0],
                    "memories": int(parts[1]) if parts[1].isdigit() else 0,
                    "plans": int(parts[2]) if parts[2].isdigit() else 0,
                    "evidence": int(parts[3]) if parts[3].isdigit() else 0,
                }
            )
    return rows


def month_summary(month: str) -> str:
    """Compact pointer — under 800 chars for Supermemory token budget."""
    hits = JOURNAL / "MONTHLY" / month / "LITIGATION_HITS.md"
    index = JOURNAL / "MONTHLY" / month / "INDEX.md"
    conv_count, lit_count = "?", "?"
    if index.is_file():
        for line in index.read_text().splitlines()[:6]:
            if "Conversations:" in line:
                conv_count = line.split(":", 1)[1].strip().strip("*")
            if "Litigation-tagged:" in line:
                lit_count = line.split(":", 1)[1].strip().strip("*")
    hit_count = 0
    top_titles: list[str] = []
    if hits.is_file():
        for hl in hits.read_text().splitlines():
            if hl.startswith("|") and "---" not in hl and "Date" not in hl:
                hit_count += 1
                parts = [p.strip() for p in hl.strip("|").split("|")]
                if len(parts) > 1 and parts[1] and len(top_titles) < 5:
                    top_titles.append(parts[1][:60])
    titles = "; ".join(top_titles) if top_titles else "see LITIGATION_HITS.md"
    return (
        f"[CASE-OS] Journal {month} | 1FDV-23-0001009 | "
        f"{conv_count} convos, {lit_count} litigation, {hit_count} hits. "
        f"Top: {titles}. "
        f"canon:CHATGPT_LIFE_RECORD/MONTHLY/{month}/ "
        f"exhibit:EXH-J-{month}"
    )[:780]


def build_manifest() -> dict:
    stats = read_stats()
    months = (
        sorted((JOURNAL / "MONTHLY").iterdir())
        if (JOURNAL / "MONTHLY").is_dir()
        else []
    )
    month_ids = [m.name for m in months if m.is_dir()]
    actors = read_manifest_table()
    return {
        "at": _now(),
        "case": "1FDV-23-0001009",
        "layers": {
            "notion": {
                "role": "control_plane",
                "status": "zip_unpacked_no",
                "api_key": "expired_401",
                "journal_parent": "Contemporaneous Journal — 1FDV-23-0001009",
                "dbs": "APEX_COMMAND_CENTER/notion_consolidator/config.py",
            },
            "local_raw": {
                "canon": str(stats.get("input", "")),
                "size_class": "672MB",
            },
            "local_journal": {
                "canon_views": str(JOURNAL),
                "months": month_ids,
                "total": stats.get("total", 0),
                "litigation": stats.get("litigation", 0),
            },
            "local_actors": {
                "canon": str(BY_ACTOR),
                "plans_canon": str(ACTORS),
                "actors": actors,
            },
            "supermemory": {"tag": SM_TAG, "role": "semantic_index"},
            "mem0": {"agent": MEM0_AGENT, "role": "episodic"},
        },
        "dedup": {
            "raw_chats": "conversations.json only",
            "jsonl": "derived_regenerable",
            "notion": "INDEX+LITIGATION_HITS views only",
        },
    }


def sm_add(text: str, doc_id: str, dry_run: bool) -> bool:
    key = _hash(text)
    if dry_run:
        print(f"  [dry] supermemory add id={doc_id} hash={key}")
        return True
    try:
        r = subprocess.run(
            ["supermemory", "add", text, "--tag", SM_TAG, "--id", doc_id],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(HOME),
        )
        if r.returncode != 0:
            print(f"  supermemory FAIL: {r.stderr[:120]}", file=sys.stderr)
            return False
        print(f"  supermemory OK: {doc_id}")
        return True
    except Exception as e:
        print(f"  supermemory ERROR: {e}", file=sys.stderr)
        return False


def mem0_add(text: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry] mem0 add ({len(text)} chars)")
        return True
    sys.path.insert(0, str(HOME / ".agents/skills/supermemory-cli/scripts"))
    try:
        from mem0_ops import add as m0_add  # type: ignore

        m0_add(
            text,
            agent_id=MEM0_AGENT,
            metadata={"source": "case-os", "case": "1FDV-23-0001009"},
        )
        print("  mem0 OK: case-os summary")
        return True
    except Exception as e:
        print(f"  mem0 ERROR: {e}", file=sys.stderr)
        return False


def sync_pointers(dry_run: bool) -> dict:
    state = load_state()
    synced = state.setdefault("synced", {})
    results = {"supermemory": 0, "mem0": 0, "skipped": 0, "failed": 0}

    # Case-wide routing doc
    manifest = build_manifest()
    routing = (
        f"[CASE-OS] 1FDV-23-0001009 unified layout. "
        f"Journal: {manifest['layers']['local_journal']['total']} entries, "
        f"{manifest['layers']['local_journal']['litigation']} litigation-tagged. "
        f"Months: {', '.join(manifest['layers']['local_journal']['months'])}. "
        f"canon:CASE_STRUCTURE/CASE_OS_LAYOUT.md "
        f"actors: {len(manifest['layers']['local_actors']['actors'])} routed."
    )
    rid = "case-os-routing-v1"
    if synced.get(rid) != _hash(routing):
        if sm_add(routing, rid, dry_run):
            synced[rid] = _hash(routing)
            results["supermemory"] += 1
        else:
            results["failed"] += 1
    else:
        results["skipped"] += 1

    # Monthly summaries (litigation hits preview only)
    monthly_dir = JOURNAL / "MONTHLY"
    if monthly_dir.is_dir():
        for month in sorted(monthly_dir.iterdir()):
            if not month.is_dir():
                continue
            text = month_summary(month.name)
            mid = f"journal-{month.name}"
            if synced.get(mid) == _hash(text):
                results["skipped"] += 1
                continue
            if sm_add(text, mid, dry_run):
                synced[mid] = _hash(text)
                results["supermemory"] += 1
            else:
                results["failed"] += 1

    # Actor pointer rows
    for row in manifest["layers"]["local_actors"]["actors"]:
        slug = row["actor"].replace(" ", "")
        for name in (slug, row["actor"]):
            folder = BY_ACTOR / name
            if folder.is_dir():
                slug = name
                break
        text = (
            f"[CASE-OS] Actor {row['actor']}: "
            f"{row['memories']} memories, {row['plans']} plans, {row['evidence']} evidence. "
            f"canon:EVIDENCE/BY_ACTOR/{slug}/ACTOR_INDEX.md "
            f"plans:ACTORS/"
        )
        aid = f"actor-{slug.lower()}"
        if synced.get(aid) == _hash(text):
            results["skipped"] += 1
            continue
        if sm_add(text, aid, dry_run):
            synced[aid] = _hash(text)
            results["supermemory"] += 1
        else:
            results["failed"] += 1

    # One Mem0 episodic summary (not per-month — avoids Mem0 bloat)
    m0_text = (
        f"Case OS synced {_now()}: journal organized locally at CHATGPT_LIFE_RECORD, "
        f"{manifest['layers']['local_journal']['litigation']} litigation chats, "
        f"Notion zip not unpacked (API 401). Use sm-ops prime for context."
    )
    if not dry_run and synced.get("mem0-case-os") != _hash(m0_text):
        if mem0_add(m0_text, dry_run):
            synced["mem0-case-os"] = _hash(m0_text)
            results["mem0"] += 1

    if not dry_run:
        save_state(state)
    return results


def build_notion_push_manifest() -> dict:
    months = []
    monthly = JOURNAL / "MONTHLY"
    if monthly.is_dir():
        for m in sorted(monthly.iterdir()):
            if not m.is_dir():
                continue
            files = []
            for doc in ("INDEX.md", "LITIGATION_HITS.md"):
                p = m / doc
                if p.is_file():
                    files.append(
                        {
                            "file": str(p),
                            "title": f"Journal {m.name} — {doc.replace('.md', '')}",
                        }
                    )
            months.append({"month": m.name, "pages": files})
    out = {
        "at": _now(),
        "parent_page_title": "Contemporaneous Journal — 1FDV-23-0001009",
        "cover": str(JOURNAL / "ADMISSIBILITY_FRAME.md"),
        "months": months,
        "command": "sm-ops notion-push --parent <PAGE_ID>",
        "note": "Push views only — never jsonl or zip",
    }
    NOTION_MANIFEST.write_text(json.dumps(out, indent=2))
    return out


def notion_push(parent_id: str, month: str | None, all_months: bool) -> int:
    script = HOME / "scripts/push_chatgpt_to_notion.py"
    args = ["python3", str(script), "--parent", parent_id]
    if all_months:
        args.append("--all")
    elif month:
        args.extend(["--month", month])
    else:
        print("Specify --month YYYY-MM or --all", file=sys.stderr)
        return 1
    r = subprocess.run(args, cwd=str(HOME))
    return r.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Case OS pointers across memory layers"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--notion-push", action="store_true")
    parser.add_argument("--parent", help="Notion parent page ID for push")
    parser.add_argument("--month", help="YYYY-MM for single-month Notion push")
    parser.add_argument("--all", action="store_true", dest="all_months")
    args = parser.parse_args()

    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest → {MANIFEST_PATH}")

    notion_m = build_notion_push_manifest()
    print(f"Notion push plan → {NOTION_MANIFEST} ({len(notion_m['months'])} months)")

    if args.notion_push:
        if not args.parent:
            print("NOTION_API_KEY push requires --parent PAGE_ID", file=sys.stderr)
            print("Refresh key at notion.so/my-integrations first.", file=sys.stderr)
            return 1
        return notion_push(args.parent, args.month, args.all_months)

    print("Syncing pointers to Supermemory + Mem0...")
    results = sync_pointers(args.dry_run)
    print(json.dumps(results, indent=2))
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
