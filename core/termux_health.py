#!/usr/bin/env python3
"""
termux_health.py — Termux system health monitor
Monitors disk, memory, services, and auto-heals issues.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()


def check_disk():
    """Check disk space."""
    st = os.statvfs(str(HOME))
    total_gb = (st.f_blocks * st.f_frsize) / 1e9
    free_gb = (st.f_bavail * st.f_frsize) / 1e9
    used_pct = int(((total_gb - free_gb) / total_gb) * 100) if total_gb > 0 else 0
    return {
        "total_gb": round(total_gb, 1),
        "free_gb": round(free_gb, 1),
        "used_pct": used_pct,
    }


def check_memory():
    """Check RAM usage."""
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split()
            if parts[0] in ("MemTotal:", "MemFree:", "MemAvailable:"):
                mem[parts[0].rstrip(":")] = int(parts[1]) // 1024  # MB
        total = mem.get("MemTotal", 0)
        available = mem.get("MemAvailable", 0)
        used_pct = int(((total - available) / total) * 100) if total > 0 else 0
        return {"total_mb": total, "available_mb": available, "used_pct": used_pct}
    except:
        return {"total_mb": 0, "available_mb": 0, "used_pct": 0}


def check_services():
    """Check running services."""
    services = {}
    for name in ["apex-daemon", "auto_daemon", "space_daemon"]:
        try:
            result = subprocess.run(
                ["pgrep", "-f", name], capture_output=True, text=True
            )
            services[name] = result.returncode == 0
        except:
            services[name] = False
    return services


def check_rclone():
    """Check rclone remotes."""
    try:
        result = subprocess.run(
            ["rclone", "listremotes"], capture_output=True, text=True, timeout=5
        )
        remotes = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return {"count": len(remotes), "remotes": remotes}
    except:
        return {"count": 0, "remotes": []}


def check_git():
    """Check git repos status."""
    repos = []
    for d in [HOME / "CYBERTACK" / "LEAN_CASE", HOME / "apex-cli"]:
        if (d / ".git").exists():
            try:
                result = subprocess.run(
                    ["git", "-C", str(d), "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                changes = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                repos.append({"name": d.name, "changes": changes})
            except:
                repos.append({"name": d.name, "changes": -1})
    return repos


def health_report():
    """Generate full health report."""
    disk = check_disk()
    memory = check_memory()
    services = check_services()
    rclone = check_rclone()
    git = check_git()

    # Determine overall health
    issues = []
    if disk["used_pct"] > 90:
        issues.append(f"Disk: {disk['used_pct']}% used")
    if memory["used_pct"] > 90:
        issues.append(f"Memory: {memory['used_pct']}% used")
    for name, running in services.items():
        if not running:
            issues.append(f"Service not running: {name}")

    return {
        "timestamp": datetime.now().isoformat(),
        "disk": disk,
        "memory": memory,
        "services": services,
        "rclone": rclone,
        "git": git,
        "issues": issues,
        "healthy": len(issues) == 0,
    }


def auto_heal():
    """Auto-heal detected issues."""
    healed = []

    # Restart services if down
    for name in ["apex-daemon", "auto_daemon"]:
        try:
            result = subprocess.run(["pgrep", "-f", name], capture_output=True)
            if result.returncode != 0:
                subprocess.run(
                    [str(HOME / "scripts" / "auto_daemon.py")],
                    capture_output=True,
                    timeout=5,
                )
                healed.append(f"Restarted {name}")
        except:
            pass

    # Clean disk if low
    disk = check_disk()
    if disk["used_pct"] > 85:
        subprocess.run(
            ["python3", str(HOME / "scripts" / "space_daemon.py")],
            capture_output=True,
            timeout=30,
        )
        healed.append("Cleaned disk space")

    return healed


if __name__ == "__main__":
    report = health_report()
    print(json.dumps(report, indent=2))

    if not report["healthy"]:
        print("\nAuto-healing...")
        healed = auto_heal()
        for h in healed:
            print(f"  ✅ {h}")
