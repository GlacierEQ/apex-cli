#!/usr/bin/env python3
"""
Push monthly ChatGPT indexes to Notion pages (requires valid NOTION_API_KEY).

Usage:
  python3 push_chatgpt_to_notion.py --parent PAGE_ID --month 2025-06
  python3 push_chatgpt_to_notion.py --parent PAGE_ID --all
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

HOME = Path("/data/data/com.termux/files/home")
RECORD = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/MONTHLY"
NOTION_VERSION = "2022-06-28"


def load_key() -> str:
    keys = HOME / ".gemini_keys"
    if keys.is_file():
        for line in keys.read_text().splitlines():
            if line.startswith("export NOTION_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("NOTION_API_KEY", "")
    if not key:
        raise SystemExit(
            "NOTION_API_KEY missing — refresh at notion.so/my-integrations"
        )
    return key


def create_page(token: str, parent_id: str, title: str, markdown: str) -> str:
    # Notion API: split markdown into 2000-char rich_text chunks (simplified)
    children = []
    for i in range(0, len(markdown), 1900):
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": markdown[i : i + 1900]}}
                    ]
                },
            }
        )
        if len(children) >= 90:
            break
    body = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": children[:100],
    }
    r = httpx.post(
        "https://api.notion.com/v1/pages",
        headers={"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION},
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", required=True, help="Notion parent page ID")
    parser.add_argument("--month", help="YYYY-MM month folder")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    token = load_key()
    months = sorted(RECORD.iterdir()) if args.all else [RECORD / args.month]
    for month_dir in months:
        if not month_dir.is_dir():
            continue
        for doc in ("INDEX.md", "LITIGATION_HITS.md"):
            path = month_dir / doc
            if not path.is_file():
                continue
            title = f"ChatGPT {month_dir.name} — {doc.replace('.md', '')}"
            pid = create_page(
                token, args.parent, title, path.read_text(encoding="utf-8")
            )
            print(f"Created {title} -> {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
