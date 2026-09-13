#!/usr/bin/env python3
"""
Colossus MCP — integrity, routing, receipts, and scoped consequence authority.

Routine reversible work executes under active Operator mission authority. Colossus
classifies consequences and records receipts; it is not a serial permission queue.
"""

from __future__ import annotations

import json
import os
import subprocess
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

MISSION_AUTHORIZED_ACTIONS = frozenset({
    "read", "index", "manifest", "copy", "process_copy", "move_original",
    "overwrite", "archive_move", "upload", "rename", "organize", "restore",
})
CONSEQUENTIAL_ACTIONS = frozenset({
    "delete", "share", "publish", "external_sync", "permission_change",
    "credential_change", "secret_rotation", "force_push", "repo_delete",
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
def gate_action(action_class: str, target_path: str = "", reason: str = "") -> str:
    """Compatibility classifier: not a blanket gate. Returns authority mode for the exact action."""
    action = action_class.strip().lower()
    if action in MISSION_AUTHORIZED_ACTIONS:
        authority = "active_mission_authority"
        allowed_now = True
        next_step = "Proceed and verify/read back"
    elif action in CONSEQUENTIAL_ACTIONS:
        authority = "scoped_consequence_authority"
        allowed_now = False
        next_step = "Obtain scoped authority for this exact consequential action"
    else:
        authority = "local_classification_required"
        allowed_now = False
        next_step = "Classify this exact action locally; do not stop unrelated work"
    return json.dumps({
        "at": _now(), "action_class": action, "target_path": target_path, "reason": reason,
        "authority_mode": authority, "policy": str(POLICY_PATH), "allowed_now": allowed_now,
        "local_only": True, "next_step": next_step,
    }, indent=2)


@mcp.tool()
def safe_read(path: str, max_chars: int = 8000) -> str:
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
def mesh_status() -> str:
    return json.dumps({
        "at": _now(),
        "service": "Colossus integrity/consequence classifier",
        "case": os.environ.get("CASE_ID", "1FDV-23-0001009"),
        "routine_authority": "active_mission_authority",
        "consequence_authority": "scoped_consequence_authority",
    }, indent=2)


@mcp.tool()
def nexus_status() -> str:
    nexus = ALPHA / "apex_nexus_coordinator.py"
    code, out = _run(["python3", str(nexus), "status"], cwd=ALPHA, timeout=60)
    return json.dumps({"ok": code == 0, "output": out[-3000:]}, indent=2)


@mcp.tool()
def nexus_ingest(file_path: str) -> str:
    nexus = ALPHA / "apex_nexus_coordinator.py"
    code, out = _run(["python3", str(nexus), "ingest", "--file", file_path], cwd=ALPHA, timeout=120)
    return json.dumps({"ok": code == 0, "file": file_path, "output": out[-2000:]}, indent=2)


@mcp.tool()
def helix_activate() -> str:
    code, out = _run(["sm-ops", "helix-maximize"], timeout=180)
    return json.dumps({"ok": code == 0, "detail": out[-1500:]}, indent=2)


if __name__ == "__main__":
    mcp.run("stdio")
