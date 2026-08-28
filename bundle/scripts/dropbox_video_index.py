#!/usr/bin/env python3
"""Metadata-only index of UNIFIED_FORENSIC_LIBRARY/03_VIDEOS (no downloads)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
REMOTE = "dropbox:UNIFIED_FORENSIC_LIBRARY/03_VIDEOS"
OUT = HOME / ".apex/dropbox_video_index.jsonl"
SUMMARY = HOME / ".apex/dropbox_video_index_summary.json"
QUEUE = HOME / ".apex/notion_push_queue.jsonl"


def parse_cloud_pl(name: str) -> dict:
    m = re.search(
        r"(\d{4}-\d{2}-\d{2}).*CLOUD_PL_(\d{4}-\d{2}-\d{2})\s+(\d{2}\.\d{2}\.\d{2})",
        name,
    )
    if not m:
        return {}
    return {
        "captured_date": m.group(1),
        "cloud_pl_date": m.group(2),
        "cloud_pl_time": m.group(3),
    }


def main() -> int:
    print(f"Listing {REMOTE} (metadata only) …")
    proc = subprocess.run(
        ["rclone", "lsjson", REMOTE, "--recursive", "--files-only"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return 1

    entries = json.loads(proc.stdout or "[]")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    by_ext: dict[str, int] = {}
    rows: list[dict] = []

    with OUT.open("w", encoding="utf-8") as f:
        for e in entries:
            path = e.get("Path", "")
            size = int(e.get("Size") or 0)
            ext = Path(path).suffix.lower().lstrip(".") or "none"
            total_bytes += size
            by_ext[ext] = by_ext.get(ext, 0) + 1
            meta = {
                "path": path,
                "name": Path(path).name,
                "size_bytes": size,
                "size_gb": round(size / 1e9, 3),
                "mtime": e.get("ModTime"),
                "id": e.get("ID"),
                "is_dir": e.get("IsDir", False),
                **parse_cloud_pl(path),
            }
            rows.append(meta)
            f.write(json.dumps(meta) + "\n")

    rows.sort(key=lambda r: r["size_bytes"], reverse=True)
    summary = {
        "at": datetime.now(timezone.utc).isoformat(),
        "remote": REMOTE,
        "count": len(rows),
        "total_gb": round(total_bytes / 1e9, 2),
        "by_ext": by_ext,
        "top_10": rows[:10],
        "index_path": str(OUT),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Queue lightweight interaction stubs for Notion flush worker
    with QUEUE.open("a", encoding="utf-8") as q:
        for r in rows[:50]:
            q.write(
                json.dumps(
                    {
                        "source": "dropbox_video_index",
                        "interactions": [
                            {
                                "title": r["name"],
                                "type": "Video Asset",
                                "date": r.get("captured_date")
                                or (r.get("mtime") or "")[:10],
                                "summary": f"{r['size_gb']} GB — {r['path']}",
                                "source_file": r["path"],
                            }
                        ],
                        "actors": [],
                    }
                )
                + "\n"
            )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
