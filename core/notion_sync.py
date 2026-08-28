#!/usr/bin/env python3
"""
notion_sync.py — Notion automation connector
Syncs case data to Notion, monitors databases, auto-creates pages.
"""

import os
import json
import requests
from pathlib import Path

NOTION_TOKEN = os.environ.get(
    "NOTION_API_KEY", "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"
)
NOTION_VERSION = "2022-06-28"


def get_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def test_connection():
    """Test Notion API connection."""
    resp = requests.get(
        "https://api.notion.com/v1/users/me", headers=get_headers(), timeout=10
    )
    if resp.status_code == 200:
        return {"status": "connected", "workspace": resp.json().get("name", "Unknown")}
    return {"status": "error", "code": resp.status_code}


def list_databases():
    """List all Notion databases."""
    resp = requests.post(
        "https://api.notion.com/v1/search",
        headers=get_headers(),
        json={"filter": {"value": "database", "property": "object"}, "page_size": 100},
    )
    if resp.status_code == 200:
        dbs = resp.json().get("results", [])
        return [
            {
                "id": db["id"],
                "title": db.get("title", [{}])[0].get("plain_text", "Untitled"),
            }
            for db in dbs
        ]
    return []


def create_page(database_id, properties):
    """Create a page in a Notion database."""
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=get_headers(),
        json={"parent": {"database_id": database_id}, "properties": properties},
    )
    return resp.status_code == 200


def sync_case_to_notion(case_dir):
    """Sync case files to Notion database."""
    # Find or create case database
    dbs = list_databases()
    case_db = None
    for db in dbs:
        if "1FDV" in db["title"] or "Case" in db["title"]:
            case_db = db["id"]
            break

    if not case_db:
        print("No case database found — create one first")
        return 0

    # Sync files
    synced = 0
    for f in Path(case_dir).rglob("*.md"):
        props = {
            "Name": {"title": [{"text": {"content": f.stem.replace("_", " ")[:100]}}]},
            "Type": {"select": {"name": categorize(f.name)}},
            "Status": {"select": {"name": "Synced"}},
            "File Path": {
                "rich_text": [
                    {"text": {"content": str(f.relative_to(case_dir))[:2000]}}
                ]
            },
        }
        if create_page(case_db, props):
            synced += 1

    return synced


def categorize(filename):
    upper = filename.upper()
    if "MOTION" in upper:
        return "Motion"
    if "EVIDENCE" in upper:
        return "Evidence"
    if "FORENSIC" in upper:
        return "Forensic"
    if "DEFENDANT" in upper or "SMASH" in upper:
        return "Defendant"
    if "TIMELINE" in upper:
        return "Timeline"
    if "DAMAGE" in upper:
        return "Damages"
    return "Filing"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print(json.dumps(test_connection(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        dbs = list_databases()
        for db in dbs:
            print(f"  {db['title']} — {db['id'][:12]}...")
    elif len(sys.argv) > 2 and sys.argv[1] == "sync":
        count = sync_case_to_notion(sys.argv[2])
        print(f"Synced {count} pages to Notion")
    else:
        print("Usage: python3 notion_sync.py [test|list|sync <path>]")
