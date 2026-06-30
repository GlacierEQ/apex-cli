#!/usr/bin/env python3
"""
APEX Chron Automation Daemon
============================
A robust, background scheduling system that runs periodic tasks in Termux
without relying on system cron (crontab).

Tasks scheduled:
1. Hourly: Run memory sync bridge (`mimo_apex_sync.py`)
2. Daily (00:00): Run Reality log check & optimization, and rotate `/FORENSIC_AUDIT/` hashes.
3. Every 6 Hours: Run legal documents scan (`apex_nexus_coordinator.py execute --protocol CATACLYSM`)
4. Every 12 Hours: Refresh operating surfaces (`OPERATING_SURFACE.md`, `NOTION_SURFACE.md`)

Logs actions to `~/.apex/chron_daemon.log`.
PID file at `~/.apex/chron_daemon.pid`.
"""

import os
import sys
import time
import subprocess
import signal
import logging
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
CHRON_LOG = HOME / ".apex/chron_daemon.log"
PID_FILE = HOME / ".apex/chron_daemon.pid"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [APEX-CHRON] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(CHRON_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)

running = True

def handle_exit(signum, frame):
    global running
    logging.info(f"Signal {signum} received. Halting Chron Daemon cleanly.")
    running = False
    if PID_FILE.exists():
        PID_FILE.unlink()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def run_job(cmd: list[str] | str, cwd: Path | str = HOME) -> bool:
    try:
        logging.info(f"Triggering job: {cmd}")
        res = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=1800 # 30 min max
        )
        if res.returncode == 0:
            logging.info(f"Job completed successfully: {cmd}")
            return True
        else:
            logging.error(f"Job failed (code={res.returncode}): {res.stdout} {res.stderr}")
            return False
    except Exception as e:
        logging.error(f"Exception executing job: {e}")
        return False

def daemon_loop():
    logging.info("Starting APEX Chron Automation Loop...")
    
    # Track the last execution times (timestamps)
    last_hourly = 0
    last_6hourly = 0
    last_12hourly = 0
    last_daily = 0

    while running:
        now = time.time()
        
        # 1. Hourly check (3600 sec): Memory Sync Bridge
        if now - last_hourly >= 3600:
            logging.info("Running Hourly Memory Sync Bridge...")
            run_job(["python3", str(HOME / "scripts/mimo_apex_sync.py")])
            last_hourly = now

        # 2. 6-Hour check (21600 sec): CATACLYSM Scan
        if now - last_6hourly >= 21600:
            logging.info("Running 6-Hourly CATACLYSM Legal Scan...")
            alpha_dir = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
            run_job(["python3", "apex_nexus_coordinator.py", "execute", "--protocol", "CATACLYSM"], cwd=alpha_dir)
            last_6hourly = now

        # 3. 12-Hour check (43200 sec): Surface Refresh
        if now - last_12hourly >= 43200:
            logging.info("Running 12-Hourly Surface Refresher...")
            run_job(f"python3 {HOME}/scripts/apex_distill_surface.py && python3 {HOME}/scripts/apex_distill_notion.py")
            last_12hourly = now

        # 4. Daily check (86400 sec): Audit Log Rotation & Hash Seals
        if now - last_daily >= 86400:
            logging.info("Running Daily Audit log Maintenance...")
            run_job(f"python3 {HOME}/scripts/apex_helix_maximize.py && python3 {HOME}/scripts/apex_agentic_maximize.py")
            last_daily = now

        # Sleep for 10 seconds between clock polls to keep CPU overhead zero
        time.sleep(10)

def main():
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            os.kill(old_pid, 0)
            logging.warning(f"Chron Daemon is already running with PID {old_pid}.")
            sys.exit(0)
        except (ValueError, OSError):
            logging.info("Stale PID file detected. Proceeding...")
            PID_FILE.unlink()

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    
    try:
        daemon_loop()
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()

if __name__ == "__main__":
    main()
