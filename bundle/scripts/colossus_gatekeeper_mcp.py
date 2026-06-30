#!/usr/bin/env python3
"""
Colossus GateKeeper — supreme light MCP orchestrating the APEX mesh.

One entry point: routes to filesystem, memory, nexus, helix — gates risky actions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
CASE_ROOT = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
VAULT_MANIFEST = HOME / ".operator_key_vault/key_manifest.json"
POLICY_PATH = ALPHA / ".apex/control-plane/policies/file_action_safety.yaml"

mcp = FastMCP(
    "ColossusGateKeeper",
    dependencies=["mcp", "aiohttp", "python-dotenv"],
)

MCP_MESH = {
    "colossus-gatekeeper": {
        "role": "supreme_orchestrator",
        "description": "This server — routes, gates, primes keys",
        "transport": "stdio",
    },
    "apex-filesystem": {
        "role": "filesystem_forensics",
        "description": "12 forensic FS tools, SHA256, evidence organize",
        "transport": "stdio",
        "grok_name": "apex-filesystem",
    },
    "unified-memory": {
        "role": "memory_router",
        "description": "Mem0 + Supermemory + MemoryPlugin + Pinecone + Qdrant + Context7",
        "transport": "stdio",
        "grok_name": "unified-memory",
    },
    "colossus-remote": {
        "role": "trust_gate",
        "description": "Railway Colossus hash/approval authority",
        "transport": "http",
        "url_env": "COLOSSUS_MCP_URL",
    },
}

RISKY_ACTIONS = frozenset({
    "move_original", "overwrite", "delete", "share", "publish",
    "external_sync", "archive_move",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ},
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


@mcp.tool()
def mesh_status() -> str:
    """List the full MCP mesh — child servers, roles, and Grok config names."""
    keys_loaded = 0
    if VAULT_MANIFEST.is_file():
        try:
            keys_loaded = json.loads(VAULT_MANIFEST.read_text()).get("total_keys", 0)
        except json.JSONDecodeError:
            pass
    return json.dumps({
        "at": _now(),
        "gatekeeper": "ColossusGateKeeper v1",
        "case": os.environ.get("CASE_ID", "1FDV-23-0001009"),
        "keys_in_vault": keys_loaded,
        "mesh": MCP_MESH,
        "routing_guide": {
            "filesystem_ops": "use apex-filesystem MCP or gatekeeper safe_read/safe_hash",
            "memory_search": "use unified-memory MCP or gatekeeper memory_route",
            "case_protocols": "use gatekeeper nexus_status / nexus_ingest",
            "high_risk_writes": "must pass gate_action first — Colossus approval required",
        },
    }, indent=2)


@mcp.tool()
def key_power_status() -> str:
    """Report which API services have keys loaded (names only, never values)."""
    if not VAULT_MANIFEST.is_file():
        return json.dumps({"error": "Run prime_key_vault first", "manifest": str(VAULT_MANIFEST)})
    data = json.loads(VAULT_MANIFEST.read_text())
    return json.dumps({
        "at": data.get("at"),
        "total": data.get("total_keys"),
        "note": data.get("note"),
        "services": [s["env_var"] for s in data.get("services", [])],
        "historical_sources": [
            s["env_var"] for s in data.get("services", []) if s.get("historical_source")
        ],
    }, indent=2)


@mcp.tool()
def prime_key_vault() -> str:
    """Consolidate keys from Keep, operator audit, gemini_keys, apex_vault into gatekeeper.env."""
    script = HOME / "scripts/consolidate_operator_keys.py"
    code, out = _run(["python3", str(script)])
    return json.dumps({"ok": code == 0, "detail": out[-500:]}, indent=2)


@mcp.tool()
def gate_action(action_class: str, target_path: str = "", reason: str = "") -> str:
    """
    Colossus gate check before high-risk file operations.
    action_class: read|index|copy|move_original|overwrite|delete|share|publish|external_sync
    """
    action = action_class.strip().lower()
    if action in ("read", "index", "manifest", "copy", "process_copy"):
        approval = "auto"
    elif action in RISKY_ACTIONS:
        approval = "colossus_review_required"
    else:
        approval = "unknown_review_required"

    return json.dumps({
        "at": _now(),
        "action_class": action,
        "target_path": target_path,
        "reason": reason,
        "approval": approval,
        "policy": str(POLICY_PATH),
        "allowed_now": approval == "auto",
        "next_step": "Proceed" if approval == "auto" else "Obtain Colossus ApprovalRecord before execution",
    }, indent=2)


@mcp.tool()
def memory_route(query: str, user_id: str = "operator") -> str:
    """Route query through unified memory (Mem0/Pinecone router)."""
    script = HOME / "scripts/unified_memory_mcp.py"
    # Inline via sm-ops prime for token efficiency
    code, out = _run(["sm-ops", "prime", query, "--format", "json"], timeout=60)
    if code == 0 and out:
        return out[:8000]
    return json.dumps({"error": "memory_route failed", "detail": out[-300:]})


@mcp.tool()
def safe_read(path: str, max_chars: int = 8000) -> str:
    """Gatekeeper-gated read — auto-approved, sandboxed to APEX_ROOT."""
    root = Path(os.environ.get("APEX_ROOT", str(HOME))).resolve()
    p = Path(path).expanduser().resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return json.dumps({"error": "path outside APEX_ROOT", "root": str(root)})
    if not p.is_file():
        return json.dumps({"error": "not a file", "path": str(p)})
    text = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return json.dumps({"path": str(p), "chars": len(text), "content": text})


@mcp.tool()
def safe_hash(path: str) -> str:
    """SHA256 chain-of-custody hash — auto-approved."""
    import hashlib
    root = Path(os.environ.get("APEX_ROOT", str(HOME))).resolve()
    p = Path(path).expanduser().resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return json.dumps({"error": "path outside APEX_ROOT"})
    if not p.is_file():
        return json.dumps({"error": "not a file"})
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return json.dumps({"path": str(p), "sha256": h.hexdigest(), "size": p.stat().st_size})


@mcp.tool()
def nexus_status() -> str:
    """APEX Nexus coordinator status — legal weapons + active protocols."""
    nexus = ALPHA / "apex_nexus_coordinator.py"
    code, out = _run(["python3", str(nexus), "status"], cwd=ALPHA, timeout=60)
    return json.dumps({"ok": code == 0, "output": out[-3000:]}, indent=2)


@mcp.tool()
def nexus_ingest(file_path: str) -> str:
    """Ingest document through Nexus (extraction + Notion push if API valid)."""
    nexus = ALPHA / "apex_nexus_coordinator.py"
    code, out = _run(["python3", str(nexus), "ingest", "--file", file_path], cwd=ALPHA, timeout=120)
    return json.dumps({"ok": code == 0, "file": file_path, "output": out[-2000:]}, indent=2)


@mcp.tool()
def helix_activate() -> str:
    """Boot Alpha+Omega FS Commander helix maximize."""
    code, out = _run(["sm-ops", "helix-maximize"], timeout=180)
    return json.dumps({"ok": code == 0, "detail": out[-1500:]}, indent=2)


@mcp.tool()
def agent_boot() -> str:
    """Compact boot card (~450t) — MCP routing, hot paths, token rules. No secrets."""
    boot_json = HOME / ".apex/AGENT_BOOT.json"
    boot_md = HOME / ".apex/AGENT_BOOT.md"
    if boot_json.is_file():
        try:
            data = json.loads(boot_json.read_text())
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            pass
    if boot_md.is_file():
        return boot_md.read_text(encoding="utf-8", errors="replace")[:6000]
    code, out = _run(["python3", str(HOME / "scripts/apex_agentic_maximize.py"), "--quick", "--skip-prime"])
    if boot_json.is_file():
        return boot_json.read_text()
    return json.dumps({"ok": code == 0, "detail": out[-500:]}, indent=2)


@mcp.tool()
def prime_context(query: str, max_tokens: int = 1000) -> str:
    """Prime dual-memory context (Mem0+Supermemory) within token budget."""
    code, out = _run(
        ["sm-ops", "prime", query, "--max-tokens", str(max_tokens), "--format", "json"],
        timeout=90,
    )
    if code == 0 and out:
        return out[:8000]
    return json.dumps({"error": "prime failed", "detail": out[-400:]}, indent=2)


@mcp.tool()
def token_stats() -> str:
    """Token savings stats — prime calls, estimated tokens saved, cache size."""
    code, out = _run(["sm-ops", "tokens", "--format", "json"], timeout=30)
    if code == 0 and out.strip().startswith("{"):
        return out
    code2, out2 = _run(["sm-ops", "tokens"], timeout=30)
    return json.dumps({"ok": code2 == 0, "detail": out2}, indent=2)


@mcp.tool()
def maximize_agentic(quick: bool = True) -> str:
    """One-shot maximize: keys + optional helix + pointer index + agent boot + prime."""
    cmd = ["python3", str(HOME / "scripts/apex_agentic_maximize.py")]
    if quick:
        cmd.append("--quick")
    code, out = _run(cmd, timeout=300)
    status = HOME / ".apex/agentic_maximize_status.json"
    payload = {"ok": code == 0, "detail": out[-1200:]}
    if status.is_file():
        try:
            payload["status"] = json.loads(status.read_text())
        except json.JSONDecodeError:
            pass
    return json.dumps(payload, indent=2)


@mcp.tool()
def skills_router() -> str:
    """Compact skills index — names, paths, routing hints (~low tokens)."""
    path = HOME / ".apex/SKILLS_ROUTER.json"
    if not path.is_file():
        code, _ = _run(["python3", str(HOME / "scripts/apex_agentic_maximize.py"), "--quick", "--skip-prime", "--skip-connectors"])
        if not path.is_file():
            return json.dumps({"error": "skills router not built", "ok": code == 0})
    return path.read_text(encoding="utf-8", errors="replace")[:12000]


@mcp.tool()
def connector_mesh() -> str:
    """MCP connector mesh — Grok + Gemini server names, routing (no secrets)."""
    path = HOME / ".apex/CONNECTOR_MESH.json"
    if not path.is_file():
        _run(["python3", str(HOME / "scripts/apex_agentic_maximize.py"), "--quick", "--skip-prime", "--skip-skills"])
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return json.dumps({"error": "connector mesh not built"}, indent=2)


@mcp.tool()
def notion_surface() -> str:
    """Distilled Notion surface — DBs, ingest routes, API health."""
    path = HOME / ".apex/NOTION_SURFACE.json"
    if not path.is_file():
        _run(["python3", str(HOME / "scripts/apex_distill_notion.py")], timeout=30)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")[:10000]
    return json.dumps({"error": "run sm-ops notion-distill first"}, indent=2)


@mcp.tool()
def operating_surface() -> str:
    """Distilled operating surface — status, paths, commands, routing (~low tokens)."""
    path = HOME / ".apex/OPERATING_SURFACE.json"
    if not path.is_file():
        _run(["python3", str(HOME / "scripts/apex_distill_surface.py")], timeout=30)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")[:10000]
    md = HOME / ".apex/OPERATING_SURFACE.md"
    if md.is_file():
        return md.read_text(encoding="utf-8", errors="replace")[:8000]
    return json.dumps({"error": "run sm-ops surface first"}, indent=2)


@mcp.tool()
def workflow_router() -> str:
    """Execution workflow — 5 phases, task routing, MCP combo, logic rules (~low tokens)."""
    path = HOME / ".apex/WORKFLOW_ROUTER.json"
    if not path.is_file():
        _run(["python3", str(HOME / "scripts/apex_agentic_maximize.py"), "--quick", "--skip-prime", "--skip-keys"])
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")[:10000]
    return json.dumps({"error": "workflow router not built"}, indent=2)


@mcp.tool()
def memory_layer_status() -> str:
    """Memory layer health — Mem0/Supermemory keys loaded, cache, prime stats."""
    path = HOME / ".apex/memory_layer_status.json"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    code, out = _run(["python3", str(HOME / "scripts/unified_memory_mcp.py"), "health"], timeout=90)
    if code == 0 and out.strip().startswith("{"):
        return out
    code, out = _run(["sm-ops", "tokens", "--format", "json"], timeout=30)
    return out if code == 0 else json.dumps({"error": out[-300:]}, indent=2)


@mcp.tool()
def memory_route(query: str, layers: str = "") -> str:
    """Route query across unified memory mesh (7 layers). No secrets."""
    cmd = ["python3", str(HOME / "scripts/memory_connect_core.py"), "route", query]
    if layers:
        cmd.extend(["--layers", layers])
    code, out = _run(cmd, timeout=90)
    return out if code == 0 else json.dumps({"error": out[-500:]}, indent=2)


@mcp.tool()
def list_case_roots() -> str:
    """Canonical paths for case filesystem operations."""
    return json.dumps({
        "APEX_ROOT": os.environ.get("APEX_ROOT", str(HOME)),
        "CASE_ROOT": os.environ.get("CASE_ROOT", str(CASE_ROOT)),
        "EVIDENCE_ROOT": os.environ.get("EVIDENCE_ROOT", str(CASE_ROOT / "EVIDENCE")),
        "alpha_repo": str(ALPHA),
        "app_catalog": str(HOME / "MISSIONS/APP_CATALOG/MANIFEST.md"),
        "by_actor": str(CASE_ROOT / "EVIDENCE/BY_ACTOR"),
        "journal": str(CASE_ROOT / "CHATGPT_LIFE_RECORD"),
    }, indent=2)


if __name__ == "__main__":
    mcp.run("stdio")