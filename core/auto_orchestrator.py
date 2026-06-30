#!/usr/bin/env python3
"""
auto_orchestrator.py — Master automation orchestrator
Connects all systems: drives, Notion, ClickUp, Termux, GitHub.
Runs on startup and hourly.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
SCRIPTS = HOME / "scripts"

def run_script(name, args=None):
    """Run a script and capture output."""
    try:
        cmd = ["python3", str(SCRIPTS / name)] + (args or [])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {"status": "ok", "output": result.stdout.strip()[:500]}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def orchestrator_cycle():
    """Run one full orchestration cycle."""
    print(f"=== ORCHESTRATOR CYCLE {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    results = {}
    
    # 1. Health check
    print("1. Health check...")
    health = run_script("termux_health.py")
    results["health"] = health
    print(f"   {health['status']}")
    
    # 2. Auto-organize
    print("2. Auto-organize...")
    org = run_script("auto_organize.py")
    results["organize"] = org
    print(f"   {org['status']}")
    
    # 3. Notion sync
    print("3. Notion sync...")
    notion = run_script("notion_sync.py", ["test"])
    results["notion"] = notion
    print(f"   {notion['status']}")
    
    # 4. ClickUp sync
    print("4. ClickUp sync...")
    clickup = run_script("clickup_sync.py", ["test"])
    results["clickup"] = clickup
    print(f"   {clickup['status']}")
    
    # 5. Space check
    print("5. Space check...")
    space = run_script("space_daemon.py")
    results["space"] = space
    print(f"   {space['status']}")
    
    # 6. GitHub push
    print("6. GitHub push...")
    try:
        result = subprocess.run(
            ["git", "-C", str(HOME / "CYBERTACK" / "LEAN_CASE"), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            subprocess.run(["git", "-C", str(HOME / "CYBERTACK" / "LEAN_CASE"), "add", "-A"], timeout=10)
            subprocess.run(["git", "-C", str(HOME / "CYBERTACK" / "LEAN_CASE"), "commit", "-m", f"Auto: {datetime.now().strftime('%Y-%m-%d %H:%M')}"], 
                          capture_output=True, timeout=10)
            results["github"] = {"status": "pushed"}
            print("   pushed")
        else:
            results["github"] = {"status": "no changes"}
            print("   no changes")
    except:
        results["github"] = {"status": "error"}
        print("   error")
    
    print("\n=== CYCLE COMPLETE ===")
    return results

if __name__ == "__main__":
    orchestrator_cycle()
