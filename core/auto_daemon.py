#!/usr/bin/env python3
"""
auto_daemon.py — Recursive automatic actions daemon
Runs continuously, detects changes, organizes, pushes, heals.
"""

import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

HOME = Path.home()
CYBERTACK = HOME / "CYBERTACK"
LOG_FILE = HOME / ".local" / "share" / "tmp" / "auto_daemon.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check_drives():
    """Check health of all drives."""
    status = {}
    for name, remote in [("Google Drive", "gdrive:"), ("OneDrive", "onedrive:")]:
        try:
            result = subprocess.run(
                ["rclone", "ls", f"{remote}0_CASE_MASTER/", "--max-age", "1d"],
                capture_output=True, text=True, timeout=10
            )
            files = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
            status[name] = {"files": files, "ok": True}
        except:
            status[name] = {"files": 0, "ok": False}
    return status

def auto_organize():
    """Auto-organize any new files."""
    try:
        result = subprocess.run(
            ["python3", str(HOME / "scripts" / "auto_organize.py")],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except:
        return "auto_organize failed"

def check_space():
    """Check disk space and clean if needed."""
    try:
        st = os.statvfs(str(HOME))
        free_gb = (st.f_bavail * st.f_frsize) / 1e9
        if free_gb < 5:
            log(f"⚠️ Low space: {free_gb:.1f}GB free — running cleanup")
            subprocess.run(["python3", str(HOME / "scripts" / "space_daemon.py")], timeout=30)
            return {"cleaned": True, "free_gb": free_gb}
        return {"cleaned": False, "free_gb": free_gb}
    except:
        return {"cleaned": False, "free_gb": 0}

def push_to_github():
    """Push case file to GitHub if changed."""
    try:
        result = subprocess.run(
            ["git", "-C", str(CYBERTACK / "LEAN_CASE"), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            subprocess.run(["git", "-C", str(CYBERTACK / "LEAN_CASE"), "add", "-A"], timeout=10)
            subprocess.run(
                ["git", "-C", str(CYBERTACK / "LEAN_CASE"), "commit", "-m", f"Auto-sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["git", "-C", str(CYBERTACK / "LEAN_CASE"), "push"],
                capture_output=True, timeout=30
            )
            return "pushed"
        return "no changes"
    except:
        return "push failed"

def run_cycle():
    """Run one automation cycle."""
    log("=== AUTO CYCLE ===")
    
    # 1. Check space
    space = check_space()
    if space["cleaned"]:
        log(f"Space cleaned: {space['free_gb']:.1f}GB free")
    
    # 2. Auto-organize
    org_result = auto_organize()
    log(f"Organize: {org_result.strip()[:100]}")
    
    # 3. Check drives
    drives = check_drives()
    for name, info in drives.items():
        log(f"{name}: {info['files']} files, {'✅' if info['ok'] else '❌'}")
    
    # 4. Push to GitHub
    gh_result = push_to_github()
    log(f"GitHub: {gh_result}")
    
    return {"space": space, "drives": drives, "github": gh_result}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        log("Auto-daemon started")
        while True:
            try:
                run_cycle()
            except Exception as e:
                log(f"Error: {e}")
            time.sleep(3600)  # Run every hour
    else:
        run_cycle()
