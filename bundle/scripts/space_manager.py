#!/usr/bin/env python3
"""
space_manager.py — Intelligent disk space management
Archives, compresses, and cleans based on usage thresholds.
"""

import os
import json
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta

HOME = Path.home()
LOG_DIR = HOME / ".local" / "share" / "tmp"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_usage(path):
    """Get disk usage for a path."""
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
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "pct": 0}


def get_dir_size(path):
    """Get directory size in bytes."""
    total = 0
    try:
        for f in Path(path).rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except:
        pass
    return total


def clean_caches():
    """Clear all safe caches."""
    cleaned = []
    cache_dirs = [
        HOME / ".cache" / "pip",
        HOME / ".cache" / "chromium",
        HOME / ".cache" / "mesa_shader_cache",
        HOME / ".cache" / "next-swc",
        HOME / ".cache" / "ms-playwright-go",
        HOME / ".npm" / "_cacache",
        Path("/tmp"),
    ]
    for d in cache_dirs:
        if d.exists():
            size = get_dir_size(d)
            if d == Path("/tmp"):
                # Only clean old tmp files
                for f in d.glob("*"):
                    if (
                        f.is_file()
                        and f.stat().st_mtime
                        < (datetime.now() - timedelta(days=1)).timestamp()
                    ):
                        f.unlink(missing_ok=True)
            else:
                shutil.rmtree(d, ignore_errors=True)
            cleaned.append({"path": str(d), "size_mb": round(size / 1e6, 1)})
    return cleaned


def compress_old_files(path, days=30):
    """Compress files older than N days."""
    compressed = []
    cutoff = datetime.now() - timedelta(days=days)
    for f in Path(path).rglob("*.log"):
        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            gz_path = f.with_suffix(".gz")
            if not gz_path.exists():
                with open(f, "rb") as fi:
                    with gzip.open(gz_path, "wb") as fo:
                        fo.write(fi.read())
                f.unlink()
                compressed.append({"file": str(f), "compressed": str(gz_path)})
    return compressed


def archive_to_drive(path, drive_path):
    """Archive a directory to Google Drive via rclone."""
    try:
        result = subprocess.run(
            ["rclone", "copy", str(path), f"gdrive:{drive_path}"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except:
        return False


def find_large_files(path, min_size_mb=100):
    """Find files larger than min_size_mb."""
    large = []
    try:
        for f in Path(path).rglob("*"):
            if f.is_file():
                size = f.stat().st_size
                if size > min_size_mb * 1e6:
                    large.append({"path": str(f), "size_mb": round(size / 1e6, 1)})
    except:
        pass
    return sorted(large, key=lambda x: x["size_mb"], reverse=True)


def generate_report():
    """Generate comprehensive space report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "partitions": {},
        "top_consumers": [],
        "large_files": [],
        "recommendations": [],
    }

    # Check partitions
    for mount in ["/", "/data", "/storage/emulated"]:
        if os.path.exists(mount):
            report["partitions"][mount] = get_usage(mount)

    # Check top consumers
    consumers = []
    for d in [
        HOME / "MISSIONS",
        HOME / "CYBERTACK",
        HOME / ".apex_automation",
        HOME / ".git",
        HOME / ".npm",
        HOME / ".cache",
        HOME / ".local",
    ]:
        if d.exists():
            size = get_dir_size(d)
            consumers.append({"path": str(d), "size_gb": round(size / 1e9, 1)})
    report["top_consumers"] = sorted(
        consumers, key=lambda x: x["size_gb"], reverse=True
    )

    # Find large files
    report["large_files"] = find_large_files(HOME, min_size_mb=50)[:20]

    # Recommendations
    data_usage = report["partitions"].get("/data", {}).get("pct", 0)
    if data_usage > 90:
        report["recommendations"].append(
            {
                "priority": "HIGH",
                "action": "Archive old MISSIONS data to Google Drive",
                "potential_savings_gb": 10,
            }
        )
        report["recommendations"].append(
            {
                "priority": "HIGH",
                "action": "Compress .apex_automation/case-organized (5.6GB)",
                "potential_savings_gb": 4,
            }
        )

    if data_usage > 85:
        report["recommendations"].append(
            {
                "priority": "MEDIUM",
                "action": "Clean .git history (863MB)",
                "potential_savings_gb": 0.5,
            }
        )
        report["recommendations"].append(
            {
                "priority": "MEDIUM",
                "action": "Archive downloads/ to Google Drive",
                "potential_savings_gb": 0.2,
            }
        )

    return report


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        print("=== AUTOMATED CLEANUP ===")
        cleaned = clean_caches()
        for item in cleaned:
            print(f"  ✅ {item['path']} ({item['size_mb']}MB)")
        compressed = compress_old_files(HOME, days=30)
        for item in compressed:
            print(f"  📦 Compressed: {item['file']}")
        print("\nCleanup complete.")
    else:
        report = generate_report()
        print(json.dumps(report, indent=2))
