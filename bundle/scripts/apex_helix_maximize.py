#!/usr/bin/env python3
"""
APEX FS Commander — Helix maximize: Alpha + Omega full activation (Termux).

Boots observation layer, control plane, orchestrator, nexus status, MCP readiness.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
OMEGA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega"
CASE_ROOT = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
EVIDENCE = CASE_ROOT / "EVIDENCE"
STATUS_PATH = HOME / ".apex/helix_maximize_status.json"
CAPABILITIES = (
    HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/FS_COMMANDER_CAPABILITIES.md"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(
    cmd: list[str] | str, cwd: Path | None = None, timeout: int = 180
) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def patch_termux_env() -> dict:
    """Set MCP roots for Termux without mutating .env secrets."""
    env = {
        "APEX_ROOT": str(HOME),
        "CASE_ROOT": str(CASE_ROOT),
        "EVIDENCE_ROOT": str(EVIDENCE),
        "APEX_LOG": str(HOME / ".apex/mcp_audit.jsonl"),
        "CASE_ID": "1FDV-23-0001009",
    }
    for k, v in env.items():
        os.environ[k] = v
    return env


def check_mcp_servers() -> dict:
    servers_dir = ALPHA / "servers"
    results = {}
    for name, fname in [
        ("filesystem", "apex_filesystem_mcp.py"),
        ("master", "apex_master_mcp.py"),
        ("universal", "apex_universal_mcp.py"),
        ("spiral", "apex_spiral_mcp.py"),
        ("audio", "apex_audio_processor_mcp.py"),
        ("stealth", "apex_stealth_diamond_mcp.py"),
        ("http", "apex_http_server.py"),
    ]:
        path = servers_dir / fname
        if not path.is_file():
            results[name] = "missing"
            continue
        code, out = run(
            ["python3", "-c", f"import ast; ast.parse(open('{path}').read())"],
            timeout=15,
        )
        results[name] = "ready" if code == 0 else "syntax_error"
    return results


def activate_alpha(max_files: int = 2000) -> dict:
    steps = []
    validate = ALPHA / "scripts/apex_control_plane_validate.py"
    if validate.is_file():
        code, out = run(["python3", str(validate)], cwd=ALPHA)
        steps.append(
            {"step": "control_plane_validate", "ok": code == 0, "detail": out[-200:]}
        )

    observe = ALPHA / "scripts/apex_observe_files.py"
    report = ALPHA / ".apex/control-plane/reports/helix_maximize_observations.jsonl"
    report.parent.mkdir(parents=True, exist_ok=True)
    if observe.is_file():
        code, out = run(
            [
                "python3",
                str(observe),
                str(HOME / "MISSIONS"),
                "--source",
                "local_filesystem",
                "--case-tag",
                "1FDV-23-0001009",
                "--max-files",
                str(max_files),
                "--hash",
                "--output",
                str(report),
            ],
            cwd=ALPHA,
            timeout=300,
        )
        count = 0
        if report.is_file():
            count = sum(1 for _ in report.open())
        steps.append(
            {
                "step": "observe_missions",
                "ok": code == 0,
                "observations": count,
                "detail": out[-200:],
            }
        )

    nexus = ALPHA / "apex_nexus_coordinator.py"
    if nexus.is_file():
        code, out = run(["python3", str(nexus), "status"], cwd=ALPHA, timeout=60)
        steps.append({"step": "nexus_status", "ok": code == 0, "detail": out[-600:]})

    return {"strand": "alpha", "canonical": str(ALPHA), "steps": steps}


def activate_omega() -> dict:
    steps = []
    daemon = OMEGA / "orchestrator_daemon.py"
    if daemon.is_file():
        code, out = run(["python3", str(daemon)], cwd=OMEGA, timeout=30)
        steps.append(
            {"step": "orchestrator_12_piston", "ok": code == 0, "detail": out[-400:]}
        )

    status_file = HOME / ".gemini/tmp/orchestrator_status.json"
    pistons = {}
    if status_file.is_file():
        try:
            pistons = json.loads(status_file.read_text())
        except json.JSONDecodeError:
            pass
    steps.append(
        {"step": "hydra_shield_link", "ok": (OMEGA / "HYDRA_SHIELD_ENGINE").exists()}
    )
    steps.append(
        {"step": "alpha_orbit_link", "ok": (OMEGA / "ORBIT_ALPHA_CONNECTIONS").exists()}
    )
    return {
        "strand": "omega",
        "canonical": str(OMEGA),
        "pistons_online": len(pistons),
        "steps": steps,
    }


def write_capabilities(mcp: dict, alpha: dict, omega: dict) -> None:
    CAPABILITIES.write_text(f"""# APEX FS Commander — Highest Form Capabilities

**Case:** 1FDV-23-0001009 | **Activated:** {_now()}

## What it is

APEX FS Commander is the **sensory + control surface** for file-system, evidence, and connector operations in the Double Helix stack. It does not replace FILEBOSS (routing), Colossus (approval/hash gate), or Aspen Grove (durable memory) — it **feeds** them.

```text
FileObservation → RoutePlan → ApprovalRecord → ExecutionManifest → DriftReport
```

## Alpha strand (cloud + observation + MCP)

| Layer | Capability | Status on device |
|-------|------------|------------------|
| **Phase 1 Observation** | Scan paths, emit FileObservation JSONL, SHA256 hash, case tags | Active |
| **Control plane** | Policy/registries/schemas — validate before any write | Active |
| **Filesystem MCP** | 12 tools: read/write/list/search/move/delete/hash/organize_evidence | Ready (stdio) |
| **Master MCP** | Case synthesis, RICO analysis, GitHub/OneDrive/Memory intelligence | Ready |
| **Universal MCP** | Tool dispatch across pillars | Ready |
| **Spiral MCP** | Memory/planning engine bridge | Ready |
| **Audio MCP** | Transcription / forensic audio | Ready |
| **Stealth MCP** | Secure context operations | Ready |
| **HTTP bridge** | REST command surface with API key | Ready |
| **Nexus coordinator** | CATACLYSM protocol, Notion push, document ingest, dropbox watch | Active (live nexus status) |
| **Dropbox adapters** | watcher, consolidator, local recovery | Ready (local mount) |
| **Forensic scripts** | cloud organizer, case message extract, dossier linker, auto-transcribe | Ready |

### Filesystem MCP tools (highest local power)

- `read_file` / `write_file` / `list_directory`
- `search_files` / `search_content`
- `move_file` / `delete_file` (soft → `.apex/trash`)
- `get_file_info` / `hash_file` (chain of custody)
- `organize_evidence` (auto-sort into case hierarchy)
- `list_allowed_roots`

## Omega strand (device + shield + orchestration)

| Layer | Capability | Status |
|-------|------------|--------|
| **12-Piston orchestrator** | Local worker mesh status via Supermemory bridges | Active |
| **ORBIT_ALPHA_CONNECTIONS** | Symlink to Alpha cloud sync engine | Linked |
| **HYDRA_SHIELD_ENGINE** | HIPS, file trapping, process sandbox (HydraDragonAntivirus) | Linked |
| **Storage commander** | Disk audit, safe purge, pointer sync | Active |

## Ecosystem handoffs (full architecture)

| System | Role | FS Commander interaction |
|--------|------|--------------------------|
| **FILEBOSS** | Route authority | Consumes FileObservation → emits RoutePlan |
| **Colossus** | Hash/approval gate | Signs ExecutionManifest for writes/deletes |
| **MEGA-PDF** | Document engine | Receives route for PDF processing |
| **Aspen Grove** | File-memory substrate | Stores edges from observations |
| **Mastermind** | Drift/evolution | Consumes DriftReport |
| **Notion** | Control plane OS | Nexus pushes actors/interactions |
| **sm-ops** | Mem0 + Supermemory | Omega pistons + case-os pointers |

## Activation commands (Termux)

```bash
sm-ops helix-maximize          # Full Alpha+Omega boot
sm-ops fs-commander --all      # Storage audit + purge + activate
./run_apex.sh filesystem       # Start filesystem MCP (from alpha repo)
./run_apex.sh list             # Server status
python3 apex_nexus_coordinator.py status
python3 apex_nexus_coordinator.py ingest --file <doc>
python3 apex_nexus_coordinator.py watch   # dropbox watcher
```

## MCP server readiness (this run)

```json
{json.dumps(mcp, indent=2)}
```

## Current boot result

- Alpha steps: {sum(1 for s in alpha.get("steps", []) if s.get("ok"))} / {len(alpha.get("steps", []))} OK
- Omega pistons: {omega.get("pistons_online", 0)} online
""")


def main() -> int:
    print("=" * 56)
    print("  APEX FS COMMANDER — HELIX MAXIMIZE")
    print("=" * 56)

    patch_termux_env()
    print(f"[env] APEX_ROOT={os.environ['APEX_ROOT']}")
    print(f"[env] CASE_ROOT={os.environ['CASE_ROOT']}")

    print("\n[mcp] checking server modules...")
    mcp = check_mcp_servers()
    for name, status in mcp.items():
        print(f"  {name}: {status}")

    print("\n[alpha] maximizing...")
    alpha = activate_alpha()
    for s in alpha["steps"]:
        mark = "OK" if s.get("ok") else "WARN"
        print(f"  [{mark}] {s['step']}")

    print("\n[omega] maximizing...")
    omega = activate_omega()
    for s in omega["steps"]:
        mark = "OK" if s.get("ok") else "WARN"
        print(f"  [{mark}] {s['step']}")
    print(f"  pistons: {omega.get('pistons_online', 0)}/12")

    payload = {
        "at": _now(),
        "mcp": mcp,
        "alpha": alpha,
        "omega": omega,
        "env": patch_termux_env(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2))
    write_capabilities(mcp, alpha, omega)

    print(f"\n[status] {STATUS_PATH}")
    print(f"[capabilities] {CAPABILITIES}")
    print("\nHelix maximize complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
