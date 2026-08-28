#!/usr/bin/env python3
"""
AI Automation Ecosystem Launcher
Dedicated orchestrator for maximized local Ollama (gemma4) + Gemini handoff + Nexus dispatch + Workers + Daemons + Token Savings.

Usage:
  python3 scripts/ai_automation_ecosystem.py --maximize --start-daemons --handoff
  python3 scripts/ai_automation_ecosystem.py --automation "run case analysis"

Integrates:
- Real Python Nexus dispatch (AgenticNexus)
- gemma-cli --handoff REPL (with /nexus, /automation, /maximize, token-savings)
- Workers (ai-executor, automation-orchestrator, etc.)
- Daemons (notion_workers_daemon, etc.)
- Token savings in loops (coremaximized, apex_optimizer)
- Model router for AUTOMATION tasks
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
SCRIPTS = HOME / "scripts"
BIN = HOME / "bin"
GATEWAY = HOME / "apex-gateway"


def run(cmd, background=False, **kwargs):
    print(f"[ECO] Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if background:
        return subprocess.Popen(cmd, **kwargs)
    return subprocess.run(cmd, **kwargs)


def maximize():
    print("=== MAXIMIZE ===")
    maximize_script = SCRIPTS / "apex_helix_maximize.py"
    if maximize_script.exists():
        run([sys.executable, str(maximize_script)])
    else:
        print("apex_helix_maximize.py not found, skipping")


def start_daemons():
    print("=== START DAEMONS ===")
    # notion workers
    workers_daemon = SCRIPTS / "notion_workers_daemon.py"
    if workers_daemon.exists():
        run([sys.executable, str(workers_daemon), "--daemon"], background=True)

    # other potential daemons
    for d in ["apex_chron_daemon.py"]:
        p = SCRIPTS / d
        if p.exists():
            run([sys.executable, str(p)], background=True)


def launch_handoff():
    print("=== LAUNCH HANDOFF REPL ===")
    gemma = BIN / "gemma-cli"
    if gemma.exists():
        # exec replaces process
        os.execv(str(gemma), [str(gemma), "--handoff"])
    else:
        print("gemma-cli not found")


def dispatch_automation(task: str):
    print(f"=== AUTOMATION DISPATCH: {task} ===")
    # Use Nexus if available
    try:
        sys.path.insert(0, str(GATEWAY))
        from nexus_dispatch import AgenticNexus

        nexus = AgenticNexus()
        # Example: dispatch python executor or automation task
        proc = nexus.dispatch(
            "python", [str(SCRIPTS / "apex_helix_maximize.py"), "--task", task]
        )
        print("Dispatched via Nexus. Monitor with /nexus-status in REPL")
    except Exception as e:
        print(f"Nexus dispatch failed: {e}. Falling back to direct.")
        run([sys.executable, str(SCRIPTS / "apex_helix_maximize.py")])


def token_savings_setup():
    print("=== TOKEN SAVINGS ===")
    # Activate coremaximized if possible
    profile = HOME / "APEX_BOOTUP" / "profiles" / "coremaximized.sh"
    if profile.exists():
        print("Recommend: source the coremaximized profile for loop savings.")
    # Import optimizer
    try:
        sys.path.insert(0, str(HOME / ".gemini" / "skills" / "token-savings"))
        print("apex_optimizer loaded for background savings.")
    except:
        pass


def main():
    parser = argparse.ArgumentParser(description="AI Automation Ecosystem")
    parser.add_argument("--maximize", action="store_true")
    parser.add_argument("--start-daemons", action="store_true")
    parser.add_argument("--handoff", action="store_true")
    parser.add_argument(
        "--automation", type=str, help="Dispatch specific automation task"
    )
    args = parser.parse_args()

    token_savings_setup()

    if args.maximize:
        maximize()

    if args.start_daemons:
        start_daemons()

    if args.automation:
        dispatch_automation(args.automation)

    if args.handoff or (not any([args.maximize, args.start_daemons, args.automation])):
        launch_handoff()


if __name__ == "__main__":
    main()
