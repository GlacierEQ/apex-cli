#!/usr/bin/env python3
"""
space_daemon.py — Automated space monitoring daemon
Runs every hour, cleans caches, archives old data, alerts on high usage.
"""

import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta

HOME = Path.home()
LOG_DIR = HOME / ".local" / "share" / "tmp"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "space_daemon.log"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_usage(path):
    try:
        st = os.statvfs(str(path))
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        pct = int((used / total) * 100) if total > 0 else 0
        return {
            "total_gb": round(total / 1e9, 1),
            "used_gb": round(used / 1e9, 1),
            "free_gb": round(free / 1e9, 1),
            "pct": pct,
        }
    except:
        return {"pct": 0, "free_gb": 0}


def clean_caches():
    cleaned = 0
    for d in [
        HOME / ".cache" / "pip",
        HOME / ".cache" / "chromium",
        HOME / ".cache" / "mesa_shader_cache",
        HOME / ".cache" / "next-swc",
        HOME / ".npm" / "_cacache",
    ]:
        if d.exists():
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d, ignore_errors=True)
            cleaned += size
    return cleaned


def compress_logs():
    compressed = 0
    cutoff = datetime.now() - timedelta(days=7)
    for f in HOME.rglob("*.log"):
        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            gz = f.with_suffix(".gz")
            if not gz.exists():
                try:
                    with open(f, "rb") as fi, gzip.open(gz, "wb") as fo:
                        fo.write(fi.read())
                    compressed += f.stat().st_size
                    f.unlink()
                except:
                    pass
    return compressed


def run_cycle():
    log("=== Space daemon cycle ===")

    # Check partitions
    data = get_usage("/data")
    log(f"Data partition: {data['pct']}% used, {data['free_gb']}GB free")

    # Clean caches if > 85%
    if data["pct"] > 85:
        cleaned = clean_caches()
        log(f"Cleaned caches: {cleaned / 1e6:.1f}MB")

    # Compress old logs if > 80%
    if data["pct"] > 80:
        compressed = compress_logs()
        if compressed > 0:
            log(f"Compressed logs: {compressed / 1e6:.1f}MB")

    # Alert if critical
    if data["pct"] > 95:
        log(f"⚠️ CRITICAL: {data['pct']}% used — {data['free_gb']}GB free")
    elif data["pct"] > 90:
        log(f"⚡ WARNING: {data['pct']}% used — {data['free_gb']}GB free")

    return data


if __name__ == "__main__":
    data = run_cycle()
    print(f"Status: {data['pct']}% used, {data['free_gb']}GB free")
