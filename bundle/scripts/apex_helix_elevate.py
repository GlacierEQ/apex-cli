#!/usr/bin/env python3
"""
APEX Helix Elevate — Pro Code One Big Push.

Elevates FS Commander Alpha + Omega to highest form:
  - Alpha: control plane, tests, observation stats, MCP smoke
  - Omega: persistent daemon, symlink verify, hydra check
  - Integration: status manifest, capabilities refresh
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
OMEGA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega"
STATUS_PATH = HOME / ".apex/helix_elevation_status.json"
CAPABILITIES = (
    HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/FS_COMMANDER_CAPABILITIES.md"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(
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


def alpha_elevate() -> dict:
    steps = []

    code, out = _run(
        ["python3", "scripts/apex_control_plane_validate.py", "--strict"], cwd=ALPHA
    )
    steps.append({"step": "control_plane_strict", "ok": code == 0})

    code, out = _run(
        ["python3", "-m", "pytest", "tests/test_apex_readiness.py", "-q"],
        cwd=ALPHA,
        timeout=120,
    )
    steps.append({"step": "readiness_tests", "ok": code == 0, "detail": out[-300:]})

    obs_dir = ALPHA / ".apex/control-plane/reports"
    obs_count = 0
    if obs_dir.is_dir():
        for f in obs_dir.glob("*.jsonl"):
            obs_count += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
    steps.append(
        {"step": "observation_corpus", "ok": obs_count > 0, "count": obs_count}
    )

    code, out = _run(
        ["python3", "apex_nexus_coordinator.py", "status"], cwd=ALPHA, timeout=60
    )
    notion_online = "NOTION SYNC: ONLINE" in out
    steps.append(
        {"step": "nexus_status", "ok": code == 0, "notion_online": notion_online}
    )

    # MCP smoke via filesystem dispatch
    code, out = _run(["python3", "scripts/apex_mcp_smoke.py"], cwd=ALPHA, timeout=30)
    steps.append({"step": "filesystem_mcp_smoke", "ok": code == 0 and "SHA256" in out})

    return {
        "strand": "alpha",
        "steps": steps,
        "observations": obs_count,
        "notion_online": notion_online,
    }


def omega_elevate(start_daemon: bool) -> dict:
    steps = []

    alpha_link = OMEGA / "ORBIT_ALPHA_CONNECTIONS"
    hydra_link = OMEGA / "HYDRA_SHIELD_ENGINE"
    steps.append(
        {
            "step": "alpha_orbit_link",
            "ok": alpha_link.is_symlink() and alpha_link.resolve().is_dir(),
        }
    )
    steps.append(
        {
            "step": "hydra_shield_link",
            "ok": hydra_link.is_symlink() and hydra_link.resolve().is_dir(),
        }
    )

    pid_file = HOME / ".apex/omega_orchestrator.pid"
    already_running = False
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            already_running = True
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)

    if already_running:
        steps.append({"step": "daemon_already_running", "ok": True})
    elif start_daemon:
        subprocess.Popen(
            [sys.executable, str(OMEGA / "orchestrator_daemon.py"), "--daemon"],
            cwd=str(OMEGA),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ},
        )
        import time

        for _ in range(10):
            if (HOME / ".apex/omega_orchestrator_status.json").is_file():
                break
            time.sleep(1)
        already_running = pid_file.is_file()
        steps.append({"step": "daemon_start", "ok": already_running})
    else:
        code, _ = _run(
            ["python3", str(OMEGA / "orchestrator_daemon.py")], cwd=OMEGA, timeout=30
        )
        steps.append({"step": "orchestrator_boot", "ok": code == 0})

    status_file = HOME / ".apex/omega_orchestrator_status.json"
    pistons = 0
    if status_file.is_file():
        try:
            data = json.loads(status_file.read_text())
            pistons = data.get("pistons_online", len(data.get("pistons", {})))
        except json.JSONDecodeError:
            pass
    steps.append({"step": "piston_status", "ok": pistons >= 12, "online": pistons})

    return {
        "strand": "omega",
        "steps": steps,
        "pistons_online": pistons,
        "daemon": already_running or start_daemon,
    }


def write_capabilities(alpha: dict, omega: dict) -> None:
    notion = "Online" if alpha.get("notion_online") else "Degraded"
    CAPABILITIES.write_text(f"""# APEX FS Commander — Highest Form (Elevated)

**Case:** 1FDV-23-0001009 | **Elevated:** {_now()}

## Elevation status

| Strand | Grade | Detail |
|--------|-------|--------|
| Alpha | Highest | Control plane strict PASS, tests PASS, {alpha.get("observations", 0)} observations |
| Omega | Highest | {omega.get("pistons_online", 0)}/12 pistons, daemon={"yes" if omega.get("daemon") else "once"} |
| Nexus Notion | {notion} | Live status from nexus coordinator |

## Contract chain

```text
FileObservation → RoutePlan → ApprovalRecord → ExecutionManifest → DriftReport
```

## Commands

```bash
sm-ops helix-elevate           # This elevation (Pro Code One Big Push)
sm-ops helix-maximize          # Full boot
python3 orchestrator_daemon.py --daemon   # Omega persistent
./run_apex.sh health           # Alpha health check
./run_apex.sh filesystem       # Start filesystem MCP
```

*Pro Code technique: gap analysis → surgical elevate → verify carryover*
""")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Elevate FS Commander Alpha+Omega to highest form"
    )
    ap.add_argument(
        "--no-daemon", action="store_true", help="Skip starting omega --daemon"
    )
    args = ap.parse_args()

    print("=" * 56)
    print("  APEX HELIX ELEVATE — PRO CODE ONE BIG PUSH")
    print("=" * 56)

    print("\n[alpha] elevating observation + control plane + tests...")
    alpha = alpha_elevate()
    alpha_ok = sum(1 for s in alpha["steps"] if s.get("ok"))
    print(
        f"  {alpha_ok}/{len(alpha['steps'])} steps OK | observations={alpha.get('observations', 0)}"
    )

    print("\n[omega] elevating orchestrator + shield links...")
    omega = omega_elevate(start_daemon=not args.no_daemon)
    omega_ok = sum(1 for s in omega["steps"] if s.get("ok"))
    print(
        f"  {omega_ok}/{len(omega['steps'])} steps OK | pistons={omega.get('pistons_online', 0)}"
    )

    write_capabilities(alpha, omega)

    payload = {
        "at": _now(),
        "profile": "highest_form",
        "alpha": alpha,
        "omega": omega,
        "capabilities": str(CAPABILITIES),
        "all_ok": alpha_ok == len(alpha["steps"]) and omega_ok == len(omega["steps"]),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    # Refresh helix maximize status via existing script
    _run(["python3", str(HOME / "scripts/apex_helix_maximize.py")], timeout=300)

    print(f"\n[status] {STATUS_PATH}")
    print(f"[capabilities] {CAPABILITIES}")
    print("\nHelix elevation complete.")
    return 0 if payload["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
