#!/usr/bin/env python3
"""
Notion worker mesh — deployable daemons for all Notion ingest routes.

Workers:
  dropbox   — poll dropbox/ and extract → Notion (or queue on 401)
  queue     — flush ~/.apex/notion_push_queue.jsonl when API live
  legal     — periodic CATACLYSM scan of legal_documents/
  actors    — batch push BY_ACTOR manifest names → Actors Registry

Modes:
  --daemon   Run all workers (default for crash_protect)
  --once     Run one cycle and exit
  --status   Print status JSON
  --worker X Run single worker once (dropbox|queue|legal|actors)
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
ALPHA = HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha"
CASE = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE"
STATUS_PATH = HOME / ".apex/notion_workers_status.json"
PID_PATH = HOME / ".apex/notion_workers.pid"
LOG_PATH = HOME / ".apex/notion_workers.log"

DROPBOX_INTERVAL = int(os.environ.get("NOTION_DROPBOX_SEC", "30"))
QUEUE_INTERVAL = int(os.environ.get("NOTION_QUEUE_SEC", "60"))
LEGAL_INTERVAL = int(os.environ.get("NOTION_LEGAL_SEC", "21600"))  # 6h
ACTORS_INTERVAL = int(os.environ.get("NOTION_ACTORS_SEC", "86400"))  # 24h

_running = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    line = f"[{_now()}] {msg}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
    if sys.stdout.isatty():
        print(msg)


def _load_env() -> None:
    for path in (
        HOME / ".operator_key_vault/gatekeeper.env",
        HOME / ".gemini_keys",
        ALPHA / ".env",
    ):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k or not v:
                continue
            # Gatekeeper wins for auth tokens (avoid stale shell/.env overrides).
            if path.name == "gatekeeper.env" and k in {
                "NOTION_API_TOKEN",
                "NOTION_TOKEN",
                "NOTION_API_KEY",
                "DROPBOX_ACCESS_TOKEN",
                "GITHUB_TOKEN",
            }:
                os.environ[k] = v
            elif k not in os.environ:
                os.environ[k] = v


def _alpha_path() -> None:
    sys.path.insert(0, str(ALPHA))
    os.chdir(ALPHA)


def _handle_signal(signum, _frame):
    global _running
    _log(f"Signal {signum} — stopping notion workers")
    _running = False


def worker_dropbox() -> dict:
    _alpha_path()
    from integrations.dropbox_watcher import scan_dropbox

    scan_dropbox()
    return {"worker": "dropbox", "ok": True}


def worker_queue() -> dict:
    _alpha_path()
    from integrations.notion_queue import flush_queue, queue_depth

    before = queue_depth()
    result = flush_queue()
    result["worker"] = "queue"
    result["before"] = before
    return result


def worker_legal() -> dict:
    _alpha_path()
    from apex_nexus_coordinator import ApexNexus

    nexus = ApexNexus()
    nexus.execute_protocol("CATACLYSM")
    return {"worker": "legal", "ok": True}


def _archetype_from_name(name: str) -> str:
    low = name.lower()
    if "judge" in low:
        return "Judicial Officer"
    if "clerk" in low:
        return "Judicial Officer"
    if "agency" in low or "department" in low or "cws" in low or "csea" in low:
        return "Regulatory Node (DLIR/Agency)"
    if "doe" in low:
        return "Adverse Party"
    return "Witness"


def worker_actors() -> dict:
    _alpha_path()
    from integrations.notion_sync import probe_api, push_actor
    from integrations.notion_queue import enqueue

    manifest = CASE / "EVIDENCE/BY_ACTOR/MANIFEST.md"
    if not manifest.is_file():
        return {"worker": "actors", "pushed": 0, "error": "no_manifest"}

    api_live = probe_api().get("ok", False)
    pushed = 0
    queued = 0

    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "---" in line or "Actor" in line:
            continue
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) < 4 or not parts[0] or parts[0].startswith("_"):
            continue
        actor = {
            "name": parts[0],
            "archetype": _archetype_from_name(parts[0]),
            "role": f"BY_ACTOR canon ({parts[1]} mem / {parts[3]} ev)",
            "status": "Active",
            "source_verified": True,
        }
        if api_live:
            try:
                if push_actor(actor):
                    pushed += 1
            except Exception as e:
                enqueue({"actors": [actor], "interactions": []}, source="actors_batch")
                queued += 1
                _log(f"actors: queued {parts[0]} — {e}")
        else:
            enqueue({"actors": [actor], "interactions": []}, source="actors_batch")
            queued += 1

    return {
        "worker": "actors",
        "pushed": pushed,
        "queued": queued,
        "api_live": api_live,
    }


def build_status(cycle: int, last: dict) -> dict:
    _alpha_path()
    from integrations.notion_sync import probe_api
    from integrations.notion_queue import queue_depth

    probe = probe_api()
    return {
        "at": _now(),
        "cycle": cycle,
        "api_live": probe.get("ok", False),
        "api_detail": probe.get("error") or probe.get("title"),
        "queue_depth": queue_depth(),
        "workers": ["dropbox", "queue", "legal", "actors"],
        "intervals_sec": {
            "dropbox": DROPBOX_INTERVAL,
            "queue": QUEUE_INTERVAL,
            "legal": LEGAL_INTERVAL,
            "actors": ACTORS_INTERVAL,
        },
        "last": last,
        "alpha": str(ALPHA),
    }


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_once() -> int:
    _load_env()
    last = {}
    for fn in (worker_dropbox, worker_queue, worker_actors):
        try:
            last[fn.__name__.replace("worker_", "")] = fn()
        except Exception as e:
            last[fn.__name__.replace("worker_", "")] = {"error": str(e)[:200]}
            _log(f"{fn.__name__} error: {e}")
    write_status(build_status(0, last))
    return 0


def run_daemon() -> int:
    global _running
    _load_env()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    _log("Notion workers daemon started")

    cycle = 0
    last_legal = 0.0
    last_actors = 0.0
    last: dict = {}

    try:
        while _running:
            cycle += 1
            now = time.time()

            try:
                last["dropbox"] = worker_dropbox()
            except Exception as e:
                last["dropbox"] = {"error": str(e)[:200]}
                _log(f"dropbox error: {e}")

            try:
                last["queue"] = worker_queue()
            except Exception as e:
                last["queue"] = {"error": str(e)[:200]}

            if now - last_legal >= LEGAL_INTERVAL:
                try:
                    last["legal"] = worker_legal()
                    last_legal = now
                except Exception as e:
                    last["legal"] = {"error": str(e)[:200]}
                    last_legal = now

            if now - last_actors >= ACTORS_INTERVAL or cycle == 1:
                try:
                    last["actors"] = worker_actors()
                    last_actors = now
                except Exception as e:
                    last["actors"] = {"error": str(e)[:200]}
                    last_actors = now

            write_status(build_status(cycle, last))

            for _ in range(DROPBOX_INTERVAL):
                if not _running:
                    break
                time.sleep(1)
    finally:
        PID_PATH.unlink(missing_ok=True)
        _log("Notion workers daemon stopped")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Notion worker mesh")
    parser.add_argument("--daemon", action="store_true", help="Run persistent daemon")
    parser.add_argument("--once", action="store_true", help="One cycle and exit")
    parser.add_argument("--status", action="store_true", help="Print status JSON")
    parser.add_argument("--worker", choices=["dropbox", "queue", "legal", "actors"])
    args = parser.parse_args()

    if args.status:
        if STATUS_PATH.is_file():
            print(STATUS_PATH.read_text(encoding="utf-8"))
        else:
            _load_env()
            print(json.dumps(build_status(0, {}), indent=2))
        return 0

    if args.worker:
        _load_env()
        fn = {
            "dropbox": worker_dropbox,
            "queue": worker_queue,
            "legal": worker_legal,
            "actors": worker_actors,
        }[args.worker]
        print(json.dumps(fn(), indent=2))
        return 0

    if args.once:
        return run_once()

    return run_daemon()


if __name__ == "__main__":
    raise SystemExit(main())
