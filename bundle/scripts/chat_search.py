#!/usr/bin/env python3
"""Search ChatGPT monthly life-record indexes (no runtime needed for Notion AI mirror)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path("/data/data/com.termux/files/home/MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/MONTHLY")


def search(query: str, limit: int = 15) -> list[dict]:
    q = query.lower()
    hits = []
    if not ROOT.is_dir():
        return hits
    for month_dir in sorted(ROOT.iterdir()):
        if not month_dir.is_dir():
            continue
        for name in ("LITIGATION_HITS.md", "INDEX.md"):
            path = month_dir / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if q not in text.lower():
                continue
            for line in text.splitlines():
                if q in line.lower() and ("|" in line or line.startswith("##")):
                    hits.append({"month": month_dir.name, "file": name, "line": line.strip()[:300]})
                    if len(hits) >= limit:
                        return hits
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()
    results = search(args.query, args.limit)
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"[{r['month']}] {r['line']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())