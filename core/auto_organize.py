#!/usr/bin/env python3
"""
auto_organize.py — Recursive automatic organization system
Detects new files, categorizes them, pushes to all drives.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
CYBERTACK = HOME / "CYBERTACK"
ORGANIZED = CYBERTACK / "ORGANIZED"

# Content categories
CATEGORIES = {
    "LEGAL_MOTIONS": ["MOTION", "INJUNCTION", "TRO", "STAY", "HABEAS"],
    "LEGAL_BRIEFS": ["BRIEF", "1983", "1985"],
    "LEGAL_COMPLAINTS": ["COMPLAINT"],
    "REFERRALS": ["FBI", "BAR", "JUDICIAL", "DISCOVERY", "REFERRAL"],
    "EVIDENCE_CORE": ["SMOKING", "CREDENTIAL", "OFW", "PHOTOS", "DECLARATION"],
    "EVIDENCE_FORENSIC": ["FORENSIC", "TEMPORAL", "ATTACK", "TAMPERING", "RICO_PREDICATE"],
    "DEFENDANT_DOSSIERS": ["SMASH", "DOSSIER", "ACTOR", "BROWER_CASE", "DISCIPLINARY"],
    "TIMELINE": ["TIMELINE", "CHRONOLOGY"],
    "DAMAGES": ["DAMAGE", "DAMAGES"],
    "OPERATIONAL": ["MASTER", "CASCADING", "OPERATION", "WITNESS", "EXPERT", "SERVICE", "FILING", "MATRIX"],
    "COURT_ORDERS": ["ORDER", "PROPOSED"],
}

def categorize_file(filename):
    """Categorize a file based on its name."""
    upper = filename.upper()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in upper:
                return category
    return "UNCATEGORIZED"

def scan_new_files():
    """Scan for files not yet in ORGANIZED."""
    organized_files = set()
    for f in ORGANIZED.rglob("*.md"):
        organized_files.add(f.name)
    
    new_files = []
    for f in CYBERTACK.rglob("*.md"):
        if f.name not in organized_files and "ORGANIZED" not in str(f):
            new_files.append(f)
    
    return new_files

def organize_file(filepath):
    """Organize a single file into the right category."""
    category = categorize_file(filepath.name)
    dest_dir = ORGANIZED / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filepath.name
    if not dest.exists():
        import shutil
        shutil.copy2(filepath, dest)
        return {"file": filepath.name, "category": category, "status": "organized"}
    return {"file": filepath.name, "category": category, "status": "already_exists"}

def sync_to_drives():
    """Sync organized content to Google Drive and OneDrive."""
    results = []
    
    # Google Drive
    try:
        subprocess.run(
            ["rclone", "copy", str(ORGANIZED) + "/", "gdrive:0_CASE_MASTER/"],
            capture_output=True, timeout=60
        )
        results.append("Google Drive: synced")
    except:
        results.append("Google Drive: timeout")
    
    # OneDrive
    try:
        subprocess.run(
            ["rclone", "copy", str(ORGANIZED) + "/", "onedrive:CASE_1FDV-23-0001009/"],
            capture_output=True, timeout=60
        )
        results.append("OneDrive: synced")
    except:
        results.append("OneDrive: timeout")
    
    return results

def run_cycle():
    """Run one organization cycle."""
    print(f"=== AUTO-ORGANIZE CYCLE {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    # 1. Scan for new files
    new_files = scan_new_files()
    print(f"New files found: {len(new_files)}")
    
    # 2. Organize each file
    organized = 0
    for f in new_files:
        result = organize_file(f)
        if result["status"] == "organized":
            organized += 1
            print(f"  ✅ {result['file']} → {result['category']}")
    
    print(f"Organized: {organized} files")
    
    # 3. Sync to drives
    print("\nSyncing to drives...")
    sync_results = sync_to_drives()
    for r in sync_results:
        print(f"  {r}")
    
    # 4. Report
    total = sum(1 for _ in ORGANIZED.rglob("*.md"))
    print(f"\nTotal organized: {total} files")
    return {"new": len(new_files), "organized": organized, "total": total}

if __name__ == "__main__":
    run_cycle()
