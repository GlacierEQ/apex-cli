#!/usr/bin/env python3
"""
Group home-root apps into MISSIONS categories with symlink-back for compatibility.

Generates MISSIONS/APP_CATALOG/MANIFEST.md + categories.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
CATALOG = HOME / "MISSIONS/APP_CATALOG"
STATE_PATH = HOME / ".supermemory/ops/app-organize-state.json"

# Root anchors — never move
ANCHOR_KEEP = frozenset({
    "AGENTS.md", "MEMORY.md", "GEMINI.md", "APEX_COMMAND_CENTER", "MISSIONS",
    "scripts", "bin", "dev", "projects", "WORKSPACE", "logs", "storage",
    "documents", "downloads", "Desktop", "node_modules", "lib", "dist",
    "package.json", "package-lock.json", "skills-lock.json", "SKILLS_MANIFEST.json",
    "APEX_POINTER_INDEX.json", "APEX_MASTER_LIST.md", "ASPEN_GROVE_CONSTELLATION.json",
    "CHAIN_LINK_BRIDGES.md", "tmp_deploy", "tmp_upgrades", "snapshots", "output",
    "stderr.log", "stdout.log", "audit_summary.txt", "takeout_files.txt",
    "$PREFIX", "__pycache__",
})

# category_id -> (destination under MISSIONS, display name, member names/patterns)
CATEGORIES: dict[str, dict] = {
    "litigation": {
        "dest": "THE_CATACLYSM/APPS",
        "label": "Litigation & Case",
        "items": ["FORENSIC_AUDIT"],
    },
    "infrastructure": {
        "dest": "APEX_INFRASTRUCTURE/APPS",
        "label": "APEX Infrastructure",
        "items": [
            "ai-agent-platform", "apex-files-android", "apex-unified-mcp",
            "cosmic-operator-core", "everything-mcp-server",
        ],
    },
    "colossus": {
        "dest": "APEX_INFRASTRUCTURE/COLOSSUS",
        "label": "Colossus Cluster",
        "items": [
            "xai-colossus-2", "xai-colossus-cooling", "xai-colossus-energy",
            "xai-colossus-nanosphere", "xai-colossus-security",
        ],
    },
    "agents": {
        "dest": "PRO_AGENTS/APPS",
        "label": "AI Agents & Orchestrators",
        "items": ["GlacierEQ_Swarm", "llm-runner-teams"],
    },
    "integrations": {
        "dest": "APEX_INFRASTRUCTURE/INTEGRATIONS",
        "label": "Cloud & Mount Integrations",
        "items": ["dropbox_mount"],
    },
    "forensics": {
        "dest": "FORENSICS/APPS",
        "label": "Forensics Tools",
        "items": [],
    },
    "tools": {
        "dest": "TOOLS_AND_EXTENSIONS",
        "label": "SDK & Extensions",
        "items": ["android-sdk", "jna-5.14.0.aar"],
    },
    "memory": {
        "dest": "SUPPORTING_DATA/MEMORY_OPS",
        "label": "Memory & Knowledge Ops",
        "items": ["mem0_client.py", "mem0_ultimate_master.py", "establish_neural_link.py"],
    },
    "operator_scripts": {
        "dest": "SUPPORTING_DATA/OPERATOR_SCRIPTS",
        "label": "Operator Scripts",
        "items": [
            "FINAL_INTEGRATION.py", "GENESIS_PRIME.py", "fileboss_stream.py",
            "omni_daily_sweep.py", "omni_max_agent.py", "populate_pointers.py",
            "test_dream.py", "transcribe_all_chunk_power.py", "vault_key_audit.py",
        ],
    },
    "secrets_audit": {
        "dest": "SUPPORTING_DATA/SECRETS_AUDIT",
        "label": "Keys & Audit Artifacts",
        "items": [
            "key_audit", "keep", "keep_export",
            "casey_service_account.json", "glacier_service_account.json",
            "operator_code_key_audit.json", "operator_code_key_audit_final.json",
            "vault_key_audit.json",
        ],
    },
}

# Already symlinked at root — catalog only, do not move
SYMLINK_CATALOG = [
    "CASE_STRUCTURE", "CORE_MISSION", "Casebuilder4000", "Pro-AEON-777",
    "Pro-DOCTOR-STRANGE-Orchestrator", "Pro-God-Mind-Bridge", "Pro-apex-fs-commander",
    "Pro-apex-fs-commander-omega", "Pro_Code", "apex-boot-core", "apex-gateway",
    "comet-agent", "pro-code", "pro_code", "intelligence",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text())
    return {"moved": {}, "symlinks": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["at"] = _now()
    STATE_PATH.write_text(json.dumps(state, indent=2))


def item_to_category(name: str) -> str | None:
    for cat_id, spec in CATEGORIES.items():
        if name in spec["items"]:
            return cat_id
    return None


def move_with_symlink(name: str, dest_dir: Path, dry_run: bool) -> dict:
    src = HOME / name
    if not src.exists():
        return {"name": name, "action": "skip", "reason": "missing"}
    if src.is_symlink():
        return {"name": name, "action": "skip", "reason": "already_symlink", "target": str(src.resolve())}

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    if dest.exists():
        return {"name": name, "action": "skip", "reason": "dest_exists", "dest": str(dest)}

    result = {"name": name, "dest": str(dest)}
    if dry_run:
        result["action"] = "would_move+symlink"
        return result

    shutil.move(str(src), str(dest))
    # Symlink back at root for backward compatibility
    src.symlink_to(dest)
    result["action"] = "moved+symlink"
    result["symlink"] = str(src)
    return result


def scan_existing(dest_rel: str) -> list[str]:
    dest = HOME / "MISSIONS" / dest_rel
    if not dest.is_dir():
        return []
    return sorted(
        p.name for p in dest.iterdir()
        if p.name not in (".git", "__pycache__")
    )


def build_catalog(moves: list[dict]) -> dict:
    catalog: dict = {
        "at": _now(),
        "case": "1FDV-23-0001009",
        "categories": {},
    }
    for cat_id, spec in CATEGORIES.items():
        dest_rel = spec["dest"]
        members = scan_existing(dest_rel)
        catalog["categories"][cat_id] = {
            "label": spec["label"],
            "path": str(HOME / "MISSIONS" / dest_rel),
            "members": members,
            "count": len(members),
        }
    catalog["root_symlinks"] = []
    for name in SYMLINK_CATALOG:
        p = HOME / name
        if p.is_symlink():
            catalog["root_symlinks"].append({
                "name": name,
                "target": str(p.resolve()),
            })
    catalog["anchors"] = sorted(ANCHOR_KEEP)
    catalog["last_moves"] = moves
    return catalog


def write_manifest(catalog: dict) -> None:
    CATALOG.mkdir(parents=True, exist_ok=True)
    (CATALOG / "categories.json").write_text(json.dumps(catalog, indent=2))

    lines = [
        "# App Catalog — by Category",
        "",
        f"**Updated:** {catalog['at']}",
        f"**Case:** {catalog['case']}",
        "",
        "## Categories",
        "",
        "| Category | Path | Apps |",
        "|----------|------|------|",
    ]
    for cat_id, info in catalog["categories"].items():
        rel = info["path"].replace(str(HOME) + "/", "~/")
        lines.append(f"| **{info['label']}** | `{rel}` | {info['count']} |")

    lines.extend(["", "## Members by category", ""])
    for cat_id, info in catalog["categories"].items():
        lines.append(f"### {info['label']}")
        lines.append("")
        if info["members"]:
            for m in info["members"]:
                lines.append(f"- `{m}`")
        else:
            lines.append("- *(empty)*")
        lines.append("")

    lines.extend(["## Root symlinks (already routed)", ""])
    for s in catalog["root_symlinks"]:
        tgt = s["target"].replace(str(HOME), "~")
        lines.append(f"- `{s['name']}` → `{tgt}`")

    lines.extend([
        "",
        "## Commands",
        "",
        "```bash",
        "sm-ops apps-organize              # Organize loose root apps",
        "sm-ops apps-organize --dry-run      # Preview",
        "sm-ops apps-organize --catalog-only # Regenerate manifest",
        "```",
    ])
    (CATALOG / "MANIFEST.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize apps by category under MISSIONS")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--catalog-only", action="store_true")
    args = parser.parse_args()

    moves: list[dict] = []
    if not args.catalog_only:
        state = load_state()
        for cat_id, spec in CATEGORIES.items():
            dest_dir = HOME / "MISSIONS" / spec["dest"]
            for name in spec["items"]:
                if name in ANCHOR_KEEP:
                    continue
                src = HOME / name
                if not src.exists() and name not in state.get("moved", {}):
                    continue
                result = move_with_symlink(name, dest_dir, args.dry_run)
                result["category"] = cat_id
                moves.append(result)
                if result.get("action") == "moved+symlink" and not args.dry_run:
                    state["moved"][name] = str(dest_dir / name)
                    state["symlinks"][name] = str(HOME / name)
        if not args.dry_run:
            save_state(state)

    catalog = build_catalog(moves)
    write_manifest(catalog)

    print(f"Catalog → {CATALOG / 'MANIFEST.md'}")
    moved = [m for m in moves if m.get("action") in ("moved+symlink", "would_move+symlink")]
    skipped = [m for m in moves if m.get("action") == "skip"]
    print(f"Processed: {len(moves)} | organized: {len(moved)} | skipped: {len(skipped)}")
    for m in moves:
        if m.get("action") not in ("skip",):
            print(f"  {m.get('action')}: {m['name']} → {m.get('dest', '')}")
        elif m.get("reason") == "dest_exists":
            print(f"  exists: {m['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())