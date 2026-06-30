#!/usr/bin/env python3
"""
clickup_sync.py — ClickUp automation connector
Syncs tasks, creates projects, monitors deadlines.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

CLICKUP_TOKEN = os.environ.get("CLICKUP_API_KEY", "")

def get_headers():
    return {"Authorization": CLICKUP_TOKEN, "Content-Type": "application/json"}

def test_connection():
    """Test ClickUp API connection."""
    if not CLICKUP_TOKEN:
        return {"status": "error", "message": "No CLICKUP_API_KEY set"}
    resp = requests.get("https://api.clickup.com/api/v2/team", headers=get_headers(), timeout=10)
    if resp.status_code == 200:
        teams = resp.json().get("teams", [])
        return {"status": "connected", "teams": len(teams)}
    return {"status": "error", "code": resp.status_code}

def list_spaces():
    """List all workspaces/spaces."""
    resp = requests.get("https://api.clickup.com/api/v2/team", headers=get_headers(), timeout=10)
    if resp.status_code == 200:
        return resp.json().get("teams", [])
    return []

def create_task(space_id, name, description="", due_date=None):
    """Create a task in ClickUp."""
    data = {"name": name, "description": description}
    if due_date:
        data["due_date"] = int(due_date.timestamp() * 1000)
    resp = requests.post(f"https://api.clickup.com/api/v2/list/{space_id}/task", 
                        headers=get_headers(), json=data, timeout=10)
    return resp.status_code == 200

def sync_case_tasks(space_id):
    """Sync case deadlines and tasks to ClickUp."""
    tasks = [
        ("FBI Criminal Referral", "Deliver to FBI Honolulu"),
        ("File Federal Complaint", "File with District Court"),
        ("Serve Defendants", "Complete service of process"),
        ("Expedited Discovery", "File within 14 days"),
        ("Spoliation Sanctions", "File within 21 days"),
        ("Counsel Disqualification", "File within 21 days"),
        ("RICO Case Statement", "Per court schedule"),
        ("Expert Disclosure", "90 days before trial"),
    ]
    
    created = 0
    for name, desc in tasks:
        if create_task(space_id, name, desc):
            created += 1
    
    return created

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print(json.dumps(test_connection(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        spaces = list_spaces()
        for s in spaces:
            print(f"  {s.get('name', '?')} — {s.get('id', '?')}")
    else:
        print("Usage: python3 clickup_sync.py [test|list]")
