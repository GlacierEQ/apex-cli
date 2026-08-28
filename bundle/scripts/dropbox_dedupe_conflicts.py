#!/usr/bin/env python3
"""Remove empty Dropbox view-only conflict folders (safe dedupe)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
REPORT = HOME / ".apex/dropbox_conflict_dedupe.json"
DRY = "--dry-run" in sys.argv

CONFLICTS = [
    "dropbox:000_START_HERE (view-only conflicts 2026-06-16)",
    "dropbox:01_APEX_CASE_MATRIX_MIRROR (view-only conflicts 2026-06-10 1)",
    "dropbox:01_APEX_CASE_MATRIX_MIRROR (view-only conflicts 2026-06-10)",
    "dropbox:01_APEX_CASE_MATRIX_MIRROR (view-only conflicts 2026-06-11 1)",
    "dropbox:01_APEX_CASE_MATRIX_MIRROR (view-only conflicts 2026-06-11 2)",
    "dropbox:01_APEX_CASE_MATRIX_MIRROR (view-only conflicts 2026-06-11)",
    "dropbox:02_TEAM_ADMIN_RESOURCES (view-only conflicts 2026-06-01)",
]
MAX_BYTES = 1024  # only delete near-empty conflict dirs


def folder_size(remote: str) -> dict:
    proc = subprocess.run(
        ["rclone", "size", remote, "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    return json.loads(proc.stdout)


def purge(remote: str) -> bool:
    cmd = ["rclone", "purge", remote]
    if DRY:
        cmd.insert(1, "--dry-run")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.returncode == 0


def main() -> int:
    results = []
    removed = 0
    for remote in CONFLICTS:
        info = folder_size(remote)
        bytes_ = int(info.get("bytes") or 0)
        count = int(info.get("count") or 0)
        action = "skip"
        ok = None
        if "error" not in info and bytes_ <= MAX_BYTES and count <= 5:
            ok = purge(remote)
            action = "purged" if ok else "purge_failed"
            if ok and not DRY:
                removed += 1
        results.append(
            {
                "remote": remote,
                "count": count,
                "bytes": bytes_,
                "action": action,
                "ok": ok,
            }
        )
        print(f"{action:12} {count:3} files {bytes_:5} B  {remote}")

    report = {
        "at": datetime.now(timezone.utc).isoformat(),
        "dry_run": DRY,
        "removed": removed,
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"removed": removed, "report": str(REPORT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
