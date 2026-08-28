#!/usr/bin/env python3
"""
APEX FS Commander — Termux storage audit, safe purge, Alpha/Omega activation.

Alpha: observation + control-plane validation (non-destructive)
Omega: orchestrator daemon + device shield status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
OMEGA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-omega"
FS_CC = HOME / "APEX_COMMAND_CENTER/FS_COMMANDER"
STATUS_PATH = HOME / ".apex/helix_fs_status.json"
MANIFEST_PATH = (
    HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/FORENSICS/storage_manifest.json"
)

# Safe purge targets (Termux-adapted; never touches MISSIONS evidence)
PURGE_TARGETS: list[tuple[str, str]] = [
    ("Grok upload queue", str(HOME / ".grok/upload_queue")),
    ("NPM cache", str(HOME / ".npm/_cacache")),
    ("Playwright cache", str(HOME / ".cache/ms-playwright-go")),
    ("Prisma cache", str(HOME / ".cache/prisma")),
    ("Mimocode logs", str(HOME / ".local/share/mimocode/log")),
    ("ccache", str(HOME / ".cache/ccache")),
    ("pip cache", str(HOME / ".cache/pip")),
    ("termux tmp", str(HOME / "tmp")),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(
    cmd: list[str] | str, cwd: Path | None = None, timeout: int = 120
) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out.strip()
    except Exception as e:
        return 1, str(e)


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}TB"


def audit_disk() -> dict:
    code, df = run_cmd("df -h . | tail -1")
    partition = df if code == 0 else "unknown"

    heavy: list[dict] = []
    scan_roots = [
        HOME / ".git",
        HOME / ".local/share/mimocode",
        HOME / ".cache",
        HOME / ".npm",
        HOME / "MISSIONS",
        HOME / ".nvm",
        HOME / "android-sdk",
        HOME / ".grok",
    ]
    for root in scan_roots:
        if root.exists():
            heavy.append({"path": str(root), "size": fmt_size(dir_size(root))})

    large_files: list[str] = []
    code, out = run_cmd(
        f'find "{HOME}" -type f -size +200M 2>/dev/null | head -15',
        timeout=90,
    )
    if code == 0 and out:
        large_files = out.splitlines()

    reclaimable = []
    for name, path in PURGE_TARGETS:
        p = Path(path)
        if p.exists():
            reclaimable.append(
                {"name": name, "path": path, "size": fmt_size(dir_size(p))}
            )

    return {
        "at": _now(),
        "partition": partition,
        "heavy_dirs": sorted(heavy, key=lambda x: x["path"]),
        "large_files": large_files,
        "reclaimable": reclaimable,
    }


def safe_purge(dry_run: bool) -> dict:
    results = {"purged": [], "skipped": [], "freed_estimate": 0}
    for name, path in PURGE_TARGETS:
        p = Path(path)
        if not p.exists():
            results["skipped"].append({"name": name, "reason": "missing"})
            continue
        before = dir_size(p)
        if dry_run:
            results["purged"].append(
                {"name": name, "path": path, "size": fmt_size(before), "dry": True}
            )
            results["freed_estimate"] += before
            continue
        try:
            if p.is_file():
                p.unlink()
            else:
                shutil.rmtree(p)
                p.mkdir(parents=True, exist_ok=True)
            results["purged"].append(
                {"name": name, "path": path, "freed": fmt_size(before)}
            )
            results["freed_estimate"] += before
        except OSError as e:
            results["skipped"].append({"name": name, "reason": str(e)})
    return results


def activate_alpha(dry_run: bool) -> dict:
    out: dict = {"strand": "alpha", "steps": []}
    if not ALPHA.is_dir():
        out["error"] = f"Alpha path missing: {ALPHA}"
        return out

    validate = ALPHA / "scripts/apex_control_plane_validate.py"
    if validate.is_file() and not dry_run:
        code, text = run_cmd(["python3", str(validate)], cwd=ALPHA, timeout=60)
        out["steps"].append(
            {
                "control_plane_validate": "ok" if code == 0 else "fail",
                "detail": text[-500:],
            }
        )

    observe = ALPHA / "scripts/apex_observe_files.py"
    report_dir = ALPHA / ".apex/control-plane/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    observe_out = report_dir / "termux_missions_observations.jsonl"
    if observe.is_file() and not dry_run:
        code, text = run_cmd(
            [
                "python3",
                str(observe),
                str(HOME / "MISSIONS"),
                "--source",
                "local_filesystem",
                "--case-tag",
                "1FDV-23-0001009",
                "--max-files",
                "500",
                "--output",
                str(observe_out),
            ],
            cwd=ALPHA,
            timeout=180,
        )
        out["steps"].append(
            {
                "observe_missions": "ok" if code == 0 else "fail",
                "output": str(observe_out),
                "detail": text[-300:],
            }
        )
    elif dry_run:
        out["steps"].append({"observe_missions": "dry_run"})

    out["canonical"] = str(ALPHA)
    out["fs_commander_link"] = str(FS_CC)
    return out


def activate_omega(dry_run: bool) -> dict:
    out: dict = {"strand": "omega", "steps": []}
    if not OMEGA.is_dir():
        out["error"] = f"Omega path missing: {OMEGA}"
        return out

    daemon = OMEGA / "orchestrator_daemon.py"
    status_file = HOME / ".gemini/tmp/orchestrator_status.json"

    if daemon.is_file() and not dry_run:
        code, text = run_cmd(["python3", str(daemon)], cwd=OMEGA, timeout=30)
        out["steps"].append(
            {
                "orchestrator_daemon": "ok" if code == 0 else "warn",
                "detail": text[-400:],
            }
        )
    elif dry_run:
        out["steps"].append({"orchestrator_daemon": "dry_run"})

    if status_file.is_file():
        try:
            out["piston_status"] = json.loads(status_file.read_text())
        except json.JSONDecodeError:
            out["piston_status"] = "invalid_json"

    out["alpha_link"] = str(OMEGA / "ORBIT_ALPHA_CONNECTIONS")
    out["hydra_link"] = str(OMEGA / "HYDRA_SHIELD_ENGINE")
    out["canonical"] = str(OMEGA)
    return out


def write_status(audit: dict, alpha: dict, omega: dict, purge: dict | None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "at": _now(),
        "case": "1FDV-23-0001009",
        "disk": audit,
        "alpha": alpha,
        "omega": omega,
        "purge": purge,
        "paths": {
            "alpha": str(ALPHA),
            "omega": str(OMEGA),
            "command_center": str(FS_CC),
        },
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(audit, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="APEX FS Commander — Termux storage + helix activation"
    )
    parser.add_argument("--audit", action="store_true", help="Disk audit only")
    parser.add_argument("--purge", action="store_true", help="Safe cache/log purge")
    parser.add_argument(
        "--activate", action="store_true", help="Activate Alpha + Omega strands"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true", help="audit + purge + activate")
    args = parser.parse_args()

    if not any([args.audit, args.purge, args.activate, args.all]):
        args.all = True

    print("=" * 50)
    print("  APEX FS COMMANDER — HELIX ALPHA + OMEGA")
    print("=" * 50)

    audit = audit_disk()
    print(f"\n[disk] {audit['partition']}")
    print("\n[heavy]")
    for h in audit["heavy_dirs"]:
        print(f"  {h['size']:>8}  {h['path']}")
    print("\n[reclaimable]")
    for r in audit["reclaimable"]:
        print(f"  {r['size']:>8}  {r['name']} ({r['path']})")

    purge_result = None
    if args.purge or args.all:
        print("\n[purge] safe targets...")
        purge_result = safe_purge(args.dry_run)
        print(f"  freed estimate: {fmt_size(purge_result['freed_estimate'])}")
        for p in purge_result["purged"]:
            print(f"  ✓ {p['name']}: {p.get('freed') or p.get('size')}")

    alpha_result = {}
    omega_result = {}
    if args.activate or args.all:
        print("\n[alpha] activating observation layer...")
        alpha_result = activate_alpha(args.dry_run)
        print(json.dumps(alpha_result, indent=2)[:800])

        print("\n[omega] activating orchestrator + shield...")
        omega_result = activate_omega(args.dry_run)
        print(json.dumps(omega_result, indent=2)[:600])

    if not args.dry_run:
        write_status(audit, alpha_result, omega_result, purge_result)
        print(f"\n[status] {STATUS_PATH}")
        print(f"[manifest] {MANIFEST_PATH}")

    if args.audit and not (args.purge or args.activate or args.all):
        write_status(audit, {}, {}, None)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
