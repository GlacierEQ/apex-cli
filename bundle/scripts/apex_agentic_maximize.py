#!/usr/bin/env python3
"""
APEX Agentic Maximize — one-shot boot for maximum capability + minimum tokens.

Outputs compact pointer index + agent boot card (~500t) so agents skip history reload.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
APEX_DIR = HOME / ".apex"
POINTER_PATH = APEX_DIR / "POINTER_INDEX.json"
BOOT_MD = APEX_DIR / "AGENT_BOOT.md"
BOOT_JSON = APEX_DIR / "AGENT_BOOT.json"
STATUS_PATH = APEX_DIR / "agentic_maximize_status.json"
HELIX_STATUS = APEX_DIR / "helix_maximize_status.json"
SKILLS_ROUTER = APEX_DIR / "SKILLS_ROUTER.json"
CONNECTOR_MESH = APEX_DIR / "CONNECTOR_MESH.json"
MEMORY_STATUS = APEX_DIR / "memory_layer_status.json"
WORKFLOW_ROUTER = APEX_DIR / "WORKFLOW_ROUTER.json"
VAULT_MANIFEST = HOME / ".operator_key_vault/key_manifest.json"
LIVE_CONTEXT = HOME / ".supermemory/ops/live-context.md"
GROK_SKILLS = HOME / ".grok/skills"
GEMINI_SKILLS = HOME / ".gemini/skills"
AGENTS_SKILLS = HOME / ".agents/skills"
GLACIER_SKILLS = HOME / "MISSIONS/SUPPORTING_DATA/Glacier-Skillset/skills"
GATEKEEPER_ENV = HOME / ".operator_key_vault/gatekeeper.env"

PRIORITY_GROK_SYMLINKS = [
    "token-savings",
    "memory-connect",
    "apex-pillars",
    "sovereign-operator",
    "universal-connector",
    "mcp",
    "apex-aspen-grove-bootup",
    "sequential-thinking",
    "hyper-efficiency-flow",
    "unified-memory-connect",
]

CASE_ROOT = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
OMEGA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega"

DEFAULT_PRIME_QUERY = "apex agentic maximize token savings MCP routing"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str] | str, timeout: int = 180) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
            cwd=str(HOME),
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def patch_env() -> dict[str, str]:
    env = {
        "APEX_PROFILE": "coremaximized",
        "APEX_ROOT": str(HOME),
        "CASE_ROOT": str(CASE_ROOT),
        "EVIDENCE_ROOT": str(CASE_ROOT / "EVIDENCE"),
        "CASE_ID": "1FDV-23-0001009",
        "APEX_TOKEN_MODE": "v2",
        "APEX_NO_ACK_THEATER": "1",
    }
    for k, v in env.items():
        os.environ[k] = v
    return env


def build_workflow_router() -> dict:
    """Compact execution logic — phases, skill/connector routing, gates."""
    return {
        "at": _now(),
        "profile": "coremaximized",
        "phases": [
            {
                "id": "boot",
                "actions": [
                    "read AGENT_BOOT.md",
                    "sm-ops prime",
                    "gatekeeper agent_boot",
                ],
                "parallel": False,
            },
            {
                "id": "plan",
                "actions": [
                    "gap analysis",
                    "read POINTER_INDEX",
                    "skills_router for task type",
                ],
                "parallel": True,
            },
            {
                "id": "execute",
                "actions": [
                    "batch tool calls",
                    "colossus gate before risky writes",
                    "helix one-big-push",
                ],
                "parallel": True,
            },
            {
                "id": "verify",
                "actions": [
                    "read back changes",
                    "guard_signal9 if spawning procs",
                    "token_stats",
                ],
                "parallel": True,
            },
            {
                "id": "save",
                "actions": ["sm-ops save --durable", "memory_layer_status"],
                "parallel": False,
            },
        ],
        "task_routing": {
            "coding": ["helix-pro-code", "token-savings", "hyper-efficiency-flow"],
            "memory": ["memory-connect", "unified-memory-connect", "supermemory-cli"],
            "storage": ["apex-fs-commander", "fs-commander via sm-ops"],
            "connectors": ["mcp", "universal-connector", "colossus-gatekeeper"],
            "legal": ["digital-law-library-master"],
            "infra": ["apex-pillars", "sovereign-operator", "deployments-cicd"],
        },
        "mcp_combo": {
            "supreme": "colossus-gatekeeper",
            "direct": ["apex-filesystem", "unified-memory"],
            "gemini_cloud": ["gdrive", "dropbox", "onedrive", "github"],
            "route_before_spawn": "check phantom limit ≤40 raised",
        },
        "logic_rules": [
            "Prime once per task; never reload full chat history",
            "Read before write; POINTER_INDEX before directory scans",
            "Parallelize independent reads/searches",
            "gate_action before delete/move/share/publish",
            "Mem0 episodic + Supermemory knowledge; durable_save both",
            "Tables over prose; no acknowledgment theater",
            "Single coherent commit per logical chunk",
        ],
        "hooks": {
            "session_start": "~/.grok/hooks/memory-prime.json → memory_prime_hook.sh",
            "session_end": "memory_save_hook.sh",
            "grok_config": str(HOME / ".grok/config.toml"),
        },
    }


def build_pointer_index() -> dict:
    return {
        "at": _now(),
        "mantra": "Two strands. One sovereign DNA.",
        "boot_order": [
            "~/.apex/AGENT_BOOT.md",
            "~/.supermemory/ops/live-context.md",
            "Pro_Code/CODER-SKILL.md",
        ],
        "mcp_routing": {
            "filesystem": "colossus-gatekeeper → safe_read/safe_hash OR apex-filesystem",
            "memory": "colossus-gatekeeper → memory_route OR unified-memory",
            "keys": "colossus-gatekeeper → key_power_status (names only)",
            "case_ingest": "colossus-gatekeeper → nexus_ingest",
            "helix": "colossus-gatekeeper → helix_activate",
            "risky_writes": "colossus-gatekeeper → gate_action first",
        },
        "paths": {
            "alpha": str(ALPHA),
            "omega": str(OMEGA),
            "case_root": str(CASE_ROOT),
            "journal": str(CASE_ROOT / "CHATGPT_LIFE_RECORD"),
            "by_actor": str(CASE_ROOT / "EVIDENCE/BY_ACTOR"),
            "keep_registry": str(HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep"),
            "gatekeeper_env": str(HOME / ".operator_key_vault/gatekeeper.env"),
            "ag_cli_index": str(
                HOME
                / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/ag_cli_environment/AG_CLI_ENVIRONMENT_INDEX.md"
            ),
            "app_catalog": str(HOME / "MISSIONS/APP_CATALOG/MANIFEST.md"),
            "grok_config": str(HOME / ".grok/config.toml"),
        },
        "skills_router": str(SKILLS_ROUTER),
        "connector_mesh": str(CONNECTOR_MESH),
        "workflow_router": str(WORKFLOW_ROUTER),
        "commands": {
            "prime": 'sm-ops prime "task" --max-tokens 1000',
            "save": 'sm-ops save "outcome" --durable',
            "maximize": "sm-ops maximize --quick",
            "helix": "sm-ops helix-maximize",
            "keys": "sm-ops prime-keys",
            "skills": "gatekeeper → skills_router",
            "connectors": "gatekeeper → connector_mesh",
            "workflow": "gatekeeper → workflow_router",
        },
        "token_discipline": [
            "Read POINTER_INDEX before directory scans",
            "Use line ranges on file reads",
            "Batch parallel tool calls",
            "Tables over prose; no acknowledgment theater",
            "Prime once per task; cache TTL 300s",
        ],
    }


def _helix_summary() -> dict:
    if not HELIX_STATUS.is_file():
        return {"loaded": False}
    try:
        data = json.loads(HELIX_STATUS.read_text())
        alpha_ok = sum(1 for s in data.get("alpha", {}).get("steps", []) if s.get("ok"))
        alpha_total = len(data.get("alpha", {}).get("steps", []))
        return {
            "loaded": True,
            "at": data.get("at", "")[:19],
            "alpha_ok": f"{alpha_ok}/{alpha_total}",
            "omega_pistons": data.get("omega", {}).get("pistons_online", 0),
            "mcp_ready": sum(1 for v in data.get("mcp", {}).values() if v == "ready"),
        }
    except json.JSONDecodeError:
        return {"loaded": False}


def _vault_summary() -> dict:
    if not VAULT_MANIFEST.is_file():
        return {"keys": 0}
    try:
        data = json.loads(VAULT_MANIFEST.read_text())
        return {"keys": data.get("total_keys", 0), "at": data.get("at", "")[:19]}
    except json.JSONDecodeError:
        return {"keys": 0}


def build_agent_boot(
    pointer: dict, helix: dict, vault: dict, prime_used: int = 0
) -> tuple[dict, str]:
    payload = {
        "at": _now(),
        "profile": "coremaximized",
        "case": os.environ.get("CASE_ID"),
        "vault_keys": vault.get("keys", 0),
        "helix": helix,
        "mcp_mesh": ["colossus-gatekeeper", "apex-filesystem", "unified-memory"],
        "prime_budget": {"default": 1000, "last_used": prime_used},
        "routing": pointer["mcp_routing"],
        "hot_paths": pointer["paths"],
        "token_rules": pointer["token_discipline"],
    }

    lines = [
        "# APEX Agent Boot (compact — do not reload full history)",
        "",
        f"**Profile:** coremaximized | **Case:** {payload['case']} | **Keys:** {payload['vault_keys']}",
        "",
        "## MCP routing",
        "",
        "| Need | Route |",
        "|------|-------|",
    ]
    for need, route in pointer["mcp_routing"].items():
        lines.append(f"| {need} | {route} |")

    lines.extend(
        [
            "",
            "## Hot paths",
            "",
            "| Resource | Path |",
            "|----------|------|",
        ]
    )
    for name, path in pointer["paths"].items():
        lines.append(f"| {name} | `{path}` |")

    lines.extend(
        [
            "",
            "## Token discipline",
            "",
        ]
    )
    for rule in pointer["token_discipline"]:
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "## Workflow (5 phases)",
            "",
            "boot → plan → execute → verify → save",
            "",
            f"Full router: `{WORKFLOW_ROUTER}`",
            "",
            "## Commands",
            "",
            "```bash",
            'sm-ops prime "current task" --max-tokens 1000',
            'sm-ops save "outcome" --durable',
            "sm-ops maximize",
            "sm-ops fs-commander --activate",
            "```",
            "",
            f"*Generated {_now()[:19]}Z*",
        ]
    )

    return payload, "\n".join(lines) + "\n"


def prime_context(query: str, max_tokens: int = 1000) -> tuple[int, str, int]:
    code, out = _run(
        ["sm-ops", "prime", query, "--max-tokens", str(max_tokens), "--no-cache"],
        timeout=90,
    )
    used = 0
    if "<!-- memory-prime tokens=" in out:
        try:
            frag = out.split("tokens=")[1].split("-->")[0]
            used = int(frag.split("/")[0])
        except (IndexError, ValueError):
            pass
    if out and "<!-- memory-prime" in out:
        LIVE_CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        LIVE_CONTEXT.write_text(out)
    return code, out, used


def _discover_skills() -> list[dict]:
    roots = [
        (GEMINI_SKILLS, "gemini"),
        (AGENTS_SKILLS, "agents"),
        (GROK_SKILLS, "grok"),
        (GLACIER_SKILLS, "glacier"),
    ]
    found: dict[str, dict] = {}
    for root, source in roots:
        if not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            if "__pycache__" in str(skill_md):
                continue
            name = skill_md.parent.name
            key = name.replace("-", "_")
            entry = {
                "name": name,
                "path": str(skill_md),
                "source": source,
                "primary": skill_md.parent.parent == root,
            }
            if key not in found or (entry["primary"] and not found[key].get("primary")):
                found[key] = entry
    return sorted(found.values(), key=lambda x: (not x["primary"], x["name"]))


def maximize_skills() -> dict:
    """Index skills + symlink priority Gemini skills into Grok."""
    GROK_SKILLS.mkdir(parents=True, exist_ok=True)
    linked = []
    for name in PRIORITY_GROK_SYMLINKS:
        src = GEMINI_SKILLS / name
        if not src.is_dir():
            src = GLACIER_SKILLS / name
        if not src.is_dir():
            continue
        dest = GROK_SKILLS / name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() and dest.resolve() == src.resolve():
                linked.append({"name": name, "status": "ok"})
            else:
                linked.append({"name": name, "status": "exists"})
            continue
        try:
            dest.symlink_to(src)
            linked.append({"name": name, "status": "linked"})
        except OSError as e:
            linked.append({"name": name, "status": f"error:{e}"})

    skills = _discover_skills()
    router = {
        "at": _now(),
        "total": len(skills),
        "primary_gemini": sum(
            1 for s in skills if s["source"] == "gemini" and s["primary"]
        ),
        "routing": {
            "token_savings": "token-savings",
            "memory_ops": "memory-connect | unified-memory-connect | sm-ops",
            "coding": "helix-pro-code | apex-pillars",
            "connectors": "mcp | universal-connector",
            "legal": "digital-law-library-master",
        },
        "skills": skills[:80],
    }
    SKILLS_ROUTER.write_text(json.dumps(router, indent=2) + "\n")

    # Refresh gemini index if script present
    idx_script = GEMINI_SKILLS / "update_index.py"
    if idx_script.is_file():
        _run(["python3", str(idx_script)], timeout=30)

    return {"total": len(skills), "symlinks": linked, "router": str(SKILLS_ROUTER)}


def _grok_mcps_from_config() -> list[str]:
    """Parse [mcp_servers.*] from Grok config.toml (source of truth)."""
    cfg = HOME / ".grok/config.toml"
    if not cfg.is_file():
        return []
    names: list[str] = []
    for line in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^\[mcp_servers\.([^\]]+)\]", line.strip())
        if m:
            names.append(m.group(1))
    return sorted(set(names))


def _grok_mcps_from_cli() -> list[str]:
    """Best-effort parse of `grok mcp list` output."""
    code, out = _run(["grok", "mcp", "list"], timeout=30)
    if code != 0:
        return []
    names: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        if ":" in line:
            name = line.split(":")[0].strip()
            if name and name not in names:
                names.append(name)
    return names


def maximize_connectors() -> dict:
    """Audit MCP mesh — Grok + Gemini connector names (no secrets)."""
    grok_config = _grok_mcps_from_config()
    grok_cli = _grok_mcps_from_cli()
    grok_mcps = sorted(set(grok_config) | set(grok_cli))

    gemini_mcps = []
    settings = HOME / ".gemini/settings.json"
    if settings.is_file():
        try:
            data = json.loads(settings.read_text())
            gemini_mcps = list(data.get("mcpServers", {}).keys())
        except json.JSONDecodeError:
            pass

    mesh = {
        "at": _now(),
        "grok_mcp": grok_mcps,
        "grok_config": grok_config,
        "grok_cli": grok_cli,
        "gemini_mcp": gemini_mcps,
        "routing": {
            "supreme": "colossus-gatekeeper",
            "filesystem": "apex-filesystem",
            "memory": "unified-memory",
            "cloud_files": "gemini:gdrive|dropbox|onedrive",
            "dev": "gemini:github",
        },
        "env_source": str(GATEKEEPER_ENV) if GATEKEEPER_ENV.is_file() else "",
    }
    CONNECTOR_MESH.write_text(json.dumps(mesh, indent=2) + "\n")
    ok = len(grok_mcps) >= 3 and len(gemini_mcps) >= 1
    return {
        "grok": len(grok_mcps),
        "gemini": len(gemini_mcps),
        "ok": ok,
        "mesh": str(CONNECTOR_MESH),
    }


def maximize_memory(query: str, max_tokens: int) -> dict:
    """Prime dual-memory + verify layers."""
    result: dict = {"layers": {}}

    if GATEKEEPER_ENV.is_file():
        env_text = GATEKEEPER_ENV.read_text(encoding="utf-8", errors="ignore")
        result["layers"]["mem0_key"] = "MEM0_API_KEY=" in env_text
        result["layers"]["supermemory_key"] = "SUPERMEMORY_API_KEY=" in env_text

    pcode, pout, used = prime_context(query, max_tokens)
    prime_ok = "<!-- memory-prime" in pout
    result["prime"] = {"ok": prime_ok, "tokens": used, "path": str(LIVE_CONTEXT)}

    # Token stats
    tcode, tout = _run(["sm-ops", "tokens", "--format", "json"], timeout=30)
    if tcode == 0 and tout.strip().startswith("{"):
        try:
            result["token_stats"] = json.loads(tout)
        except json.JSONDecodeError:
            pass

    # Unified memory cache
    cache = HOME / ".apex_cache/memory_hits.json"
    result["layers"]["apex_cache"] = cache.is_file()
    result["layers"]["live_context"] = LIVE_CONTEXT.is_file()

    MEMORY_STATUS.write_text(json.dumps({**result, "at": _now()}, indent=2) + "\n")
    return result


def patch_grok_config() -> dict:
    """Ensure Grok loads all skill roots."""
    cfg_path = HOME / ".grok/config.toml"
    if not cfg_path.is_file():
        return {"skipped": True}
    text = cfg_path.read_text()
    desired = [
        str(AGENTS_SKILLS),
        str(GLACIER_SKILLS),
        str(GEMINI_SKILLS),
        str(GROK_SKILLS),
    ]
    block = (
        "[skills]\npaths = [\n"
        + "\n".join(f'  "{p}",' for p in desired)
        + "\n]\ndisabled = []"
    )
    changed = False
    if "[skills]" in text:
        new_text = re.sub(
            r"\[skills\]\npaths = \[.*?\]\ndisabled = \[\]",
            block,
            text,
            count=1,
            flags=re.DOTALL,
        )
        if new_text != text:
            cfg_path.write_text(new_text)
            changed = True
    return {"updated": changed, "paths": len(desired)}


def run_optimizer_scan() -> dict:
    opt = HOME / ".gemini/skills/token-savings/apex_optimizer.py"
    if not opt.is_file():
        return {"skipped": True, "reason": "apex_optimizer missing"}
    code, out = _run(["python3", str(opt), "--scan-only"], timeout=60)
    if code != 0:
        # optimizer may not support --scan-only; run lightweight import check
        code2, _ = _run(
            ["python3", "-c", f"import ast; ast.parse(open('{opt}').read())"],
            timeout=15,
        )
        return {"ok": code2 == 0, "mode": "syntax_check"}
    return {"ok": code == 0, "detail": out[-300:]}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="APEX agentic + token savings maximize")
    ap.add_argument(
        "--quick", action="store_true", help="Skip helix boot (keys + prime only)"
    )
    ap.add_argument(
        "--query", default=DEFAULT_PRIME_QUERY, help="Prime query for live-context"
    )
    ap.add_argument(
        "--max-tokens", type=int, default=1000, help="Prime budget (default 1000)"
    )
    ap.add_argument("--skip-keys", action="store_true", help="Skip prime-keys")
    ap.add_argument("--skip-prime", action="store_true", help="Skip sm-ops prime")
    ap.add_argument(
        "--skip-skills", action="store_true", help="Skip skills index + symlinks"
    )
    ap.add_argument(
        "--skip-connectors", action="store_true", help="Skip connector mesh audit"
    )
    args = ap.parse_args()

    print("=" * 56)
    print("  APEX MAXIMIZE — SKILLS · TOKENS · MEMORY · CONNECTORS")
    print("=" * 56)

    patch_env()
    steps: list[dict] = []

    if not args.skip_keys:
        print("\n[keys] consolidating vault...")
        code, out = _run(
            ["python3", str(HOME / "scripts/consolidate_operator_keys.py")], timeout=120
        )
        steps.append({"step": "prime_keys", "ok": code == 0})
        print(
            f"  {'OK' if code == 0 else 'WARN'}: {out.splitlines()[-1] if out else 'no output'}"
        )

    if not args.quick:
        print("\n[helix] alpha+omega maximize...")
        code, out = _run(
            ["python3", str(HOME / "scripts/apex_helix_maximize.py")], timeout=300
        )
        steps.append({"step": "helix_maximize", "ok": code == 0})
        print(f"  {'OK' if code == 0 else 'WARN'}: helix boot")
    else:
        steps.append({"step": "helix_maximize", "ok": True, "skipped": True})

    if not args.skip_skills:
        print("\n[skills] index + Grok symlinks...")
        sk = maximize_skills()
        steps.append({"step": "skills", "ok": sk["total"] > 0, "count": sk["total"]})
        print(f"  OK: {sk['total']} skills → {SKILLS_ROUTER}")
        gcfg = patch_grok_config()
        if gcfg.get("updated"):
            print(f"  OK: grok config paths → {gcfg['paths']} roots")

    if not args.skip_connectors:
        print("\n[connectors] MCP mesh audit...")
        conn = maximize_connectors()
        steps.append(
            {
                "step": "connectors",
                "ok": conn.get("ok", False),
                "grok": conn["grok"],
                "gemini": conn["gemini"],
            }
        )
        tag = "OK" if conn.get("ok") else "WARN"
        print(
            f"  {tag}: grok={conn['grok']} gemini={conn['gemini']} → {CONNECTOR_MESH}"
        )

    print("\n[workflow] building execution router...")
    workflow = build_workflow_router()
    WORKFLOW_ROUTER.write_text(json.dumps(workflow, indent=2) + "\n")
    steps.append({"step": "workflow", "ok": WORKFLOW_ROUTER.is_file()})
    print(f"  OK: 5-phase router → {WORKFLOW_ROUTER}")

    print("\n[pointer] building compact boot index...")
    pointer = build_pointer_index()
    APEX_DIR.mkdir(parents=True, exist_ok=True)
    POINTER_PATH.write_text(json.dumps(pointer, indent=2) + "\n")

    helix = _helix_summary()
    vault = _vault_summary()

    prime_used = 0
    mem_result: dict = {}
    if not args.skip_prime:
        print(f"\n[memory] prime + layer verify ({args.max_tokens}t)...")
        mem_result = maximize_memory(args.query, args.max_tokens)
        prime_used = mem_result.get("prime", {}).get("tokens", 0)
        mem_ok = mem_result.get("prime", {}).get("ok", False)
        steps.append({"step": "memory", "ok": mem_ok, "tokens": prime_used})
        layers = mem_result.get("layers", {})
        print(
            f"  {'OK' if mem_ok else 'WARN'}: {prime_used}t | mem0={layers.get('mem0_key')} sm={layers.get('supermemory_key')}"
        )

    boot_json, boot_md = build_agent_boot(pointer, helix, vault, prime_used)
    BOOT_JSON.write_text(json.dumps(boot_json, indent=2) + "\n")
    BOOT_MD.write_text(boot_md)

    print("\n[optimizer] skill/connectors...")
    opt_result = run_optimizer_scan()
    steps.append(
        {
            "step": "optimizer",
            "ok": opt_result.get("ok", opt_result.get("skipped", False)),
        }
    )

    status = {
        "at": _now(),
        "profile": "coremaximized",
        "quick": args.quick,
        "steps": steps,
        "outputs": {
            "pointer_index": str(POINTER_PATH),
            "agent_boot_md": str(BOOT_MD),
            "agent_boot_json": str(BOOT_JSON),
            "live_context": str(LIVE_CONTEXT),
        },
        "vault": vault,
        "helix": helix,
        "prime_tokens": prime_used,
        "memory": mem_result,
        "skills_router": str(SKILLS_ROUTER) if SKILLS_ROUTER.is_file() else "",
        "connector_mesh": str(CONNECTOR_MESH) if CONNECTOR_MESH.is_file() else "",
        "optimizer": opt_result,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n")

    print(f"\n[boot]   {BOOT_MD}")
    print(f"[index]  {POINTER_PATH}")
    print(f"[status] {STATUS_PATH}")
    print("\nAgentic maximize complete.")
    return 0 if all(s.get("ok") for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
