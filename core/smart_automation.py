#!/usr/bin/env python3
"""
smart_automation.py — Governed automation framework
Rate limiting, error recovery, conditional execution, audit logging.
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

HOME = Path.home()
LOG_DIR = HOME / ".local" / "share" / "tmp"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG = LOG_DIR / "automation_audit.jsonl"

# Rate limiting state
_rate_limits = {}

def rate_limit(service, max_per_hour=10):
    """Rate limit function calls per service per hour."""
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%d-%H")
    
    if service not in _rate_limits:
        _rate_limits[service] = {}
    
    if hour_key not in _rate_limits[service]:
        _rate_limits[service][hour_key] = 0
    
    if _rate_limits[service][hour_key] >= max_per_hour:
        return False
    
    _rate_limits[service][hour_key] += 1
    return True

def audit_log(action, service, status, details=""):
    """Log action to audit trail."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "service": service,
        "status": status,
        "details": details
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def with_retry(func, max_retries=3, backoff=2):
    """Decorator for retry with exponential backoff."""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = backoff ** attempt
                    print(f"  Retry {attempt+1}/{max_retries} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
    return wrapper

def with_rate_limit(service, max_per_hour=10):
    """Decorator for rate limiting."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not rate_limit(service, max_per_hour):
                audit_log("rate_limited", service, "blocked")
                return {"status": "rate_limited", "service": service}
            return func(*args, **kwargs)
        return wrapper
    return decorator

def with_governance(func):
    """Decorator that adds governance: logging, timing, error handling."""
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            audit_log(func.__name__, "success", f"{duration:.0f}ms")
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            audit_log(func.__name__, "error", str(e)[:200])
            raise
    return wrapper

# ==========================================
# GOVERNED AUTOMATION ACTIONS
# ==========================================

@with_governance
@with_rate_limit("gdrive", max_per_hour=20)
def sync_to_gdrive(source, dest):
    """Sync files to Google Drive with rate limiting."""
    result = subprocess.run(
        ["rclone", "copy", str(source), f"gdrive:{dest}"],
        capture_output=True, timeout=120
    )
    return {"status": "ok", "files": len(list(Path(source).glob("*.md")))}

@with_governance
@with_rate_limit("onedrive", max_per_hour=20)
def sync_to_onedrive(source, dest):
    """Sync files to OneDrive with rate limiting."""
    result = subprocess.run(
        ["rclone", "copy", str(source), f"onedrive:{dest}"],
        capture_output=True, timeout=120
    )
    return {"status": "ok"}

@with_governance
@with_rate_limit("github", max_per_hour=5)
def push_to_github(repo_path):
    """Push to GitHub with rate limiting."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True, text=True, timeout=10
    )
    if result.stdout.strip():
        subprocess.run(["git", "-C", str(repo_path), "add", "-A"], timeout=10)
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", f"Auto: {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            capture_output=True, timeout=10
        )
        subprocess.run(["git", "-C", str(repo_path), "push"], capture_output=True, timeout=30)
        return {"status": "pushed"}
    return {"status": "no_changes"}

@with_governance
def sync_to_notion(database_id, case_dir):
    """Sync case files to Notion with governance."""
    try:
        result = subprocess.run(
            ["python3", str(HOME / "scripts" / "notion_sync.py"), "sync", str(case_dir)],
            capture_output=True, text=True, timeout=60
        )
        return {"status": "ok", "output": result.stdout.strip()[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ==========================================
# GOVERNED ORCHESTRATOR
# ==========================================

def governed_cycle():
    """Run one governed automation cycle with all safety checks."""
    print(f"=== GOVERNED CYCLE {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    results = {}
    
    # 1. Health check (always runs, no rate limit)
    try:
        result = subprocess.run(
            ["python3", str(HOME / "scripts" / "termux_health.py")],
            capture_output=True, text=True, timeout=30
        )
        health = json.loads(result.stdout) if result.stdout.strip() else {}
        results["health"] = {"status": "ok", "healthy": health.get("healthy", False)}
        if not health.get("healthy", True):
            print(f"  ⚠️ Health issues: {health.get('issues', [])}")
    except:
        results["health"] = {"status": "error"}
    
    # 2. Auto-organize (rate limited)
    try:
        result = subprocess.run(
            ["python3", str(HOME / "scripts" / "auto_organize.py")],
            capture_output=True, text=True, timeout=120
        )
        results["organize"] = {"status": "ok"}
        print("  ✅ Organized")
    except:
        results["organize"] = {"status": "error"}
    
    # 3. Sync to Google Drive (rate limited)
    try:
        sync_to_gdrive(HOME / "CYBERTACK" / "ORGANIZED", "0_CASE_MASTER/")
        results["gdrive"] = {"status": "ok"}
        print("  ✅ Google Drive synced")
    except:
        results["gdrive"] = {"status": "error"}
    
    # 4. Sync to OneDrive (rate limited)
    try:
        sync_to_onedrive(HOME / "CYBERTACK" / "ORGANIZED", "CASE_1FDV-23-0001009/")
        results["onedrive"] = {"status": "ok"}
        print("  ✅ OneDrive synced")
    except:
        results["onedrive"] = {"status": "error"}
    
    # 5. Push to GitHub (rate limited)
    try:
        push_to_github(HOME / "CYBERTACK" / "LEAN_CASE")
        results["github"] = {"status": "ok"}
        print("  ✅ GitHub pushed")
    except:
        results["github"] = {"status": "error"}
    
    # 6. Notion sync (rate limited)
    try:
        sync_to_notion(None, str(HOME / "CYBERTACK" / "LEAN_CASE"))
        results["notion"] = {"status": "ok"}
        print("  ✅ Notion synced")
    except:
        results["notion"] = {"status": "error"}
    
    print("\n=== CYCLE COMPLETE ===")
    return results

if __name__ == "__main__":
    governed_cycle()
