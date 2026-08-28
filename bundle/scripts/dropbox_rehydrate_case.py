#!/usr/bin/env python3
"""Re-hydrate 0-byte placeholders in Case_1FDV-23-0001009_ORGANIZED from UNIFIED_FORENSIC_LIBRARY."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
CASE_REMOTE = "dropbox:01_CASE_CENTRIC_OPS/Case_1FDV-23-0001009_ORGANIZED"
LIB_REMOTES = [
    "dropbox:UNIFIED_FORENSIC_LIBRARY/01_DOCUMENTS",
    "dropbox:UNIFIED_FORENSIC_LIBRARY",
    "dropbox:03_INTEL_ARCHIVE_DATA",
]
REPORT = HOME / ".apex/dropbox_rehydrate_report.json"
DRY = "--dry-run" in sys.argv
LIMIT = 0
for arg in sys.argv[1:]:
    if arg.startswith("--limit="):
        LIMIT = int(arg.split("=", 1)[1])


def rclone_ls(remote: str) -> list[tuple[int, str]]:
    proc = subprocess.run(
        ["rclone", "ls", remote],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    rows: list[tuple[int, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        rows.append((int(parts[0]), parts[1]))
    return rows


DOCKET_RE = re.compile(
    r"(MOTION|ORDER|SUBPOENA|ASSET_DEBT|NOTICE|NEF)_(\d+)",
    re.I,
)


def docket_key(path: str) -> str | None:
    m = DOCKET_RE.search(Path(path).name)
    return f"{m.group(1).upper()}_{m.group(2)}" if m else None


def basename_key(path: str) -> str:
    name = Path(path).name
    name = re.sub(r"_copy\d+", "", name, flags=re.I)
    name = re.sub(r"\.pdf$", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def main() -> int:
    lib_by_docket: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    lib_by_name: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for remote in LIB_REMOTES:
        print(f"Indexing {remote} …")
        for size, path in rclone_ls(remote):
            if size <= 0 or not path.lower().endswith(".pdf"):
                continue
            dk = docket_key(path)
            if dk:
                lib_by_docket[dk].append((size, path, remote))
            lib_by_name[basename_key(path)].append((size, path, remote))

    print("Scanning case folder for 0-byte PDF placeholders …")
    case_rows = rclone_ls(CASE_REMOTE)
    zero_pdfs = [(s, p) for s, p in case_rows if s == 0 and p.lower().endswith(".pdf")]
    lib_pdf_count = sum(len(v) for v in lib_by_name.values())
    print(
        f"Found {len(zero_pdfs)} zero-byte PDFs; library has {lib_pdf_count} non-empty PDFs"
    )

    plan: list[dict] = []
    seen_dest: set[str] = set()
    for _, dest_rel in zero_pdfs:
        if dest_rel in seen_dest:
            continue
        candidates: list[tuple[int, str, str]] = []
        dk = docket_key(dest_rel)
        if dk:
            candidates = lib_by_docket.get(dk, [])
        if not candidates:
            candidates = lib_by_name.get(basename_key(dest_rel), [])
        if not candidates:
            continue
        size, src_rel, remote = max(candidates, key=lambda x: x[0])
        seen_dest.add(dest_rel)
        plan.append(
            {
                "dest": f"{CASE_REMOTE}/{dest_rel}",
                "src": f"{remote}/{src_rel}",
                "bytes": size,
                "match": dk or "basename",
            }
        )

    print(f"Matched {len(plan)} placeholders to library PDFs")
    if LIMIT:
        plan = plan[:LIMIT]

    copied = 0
    errors: list[str] = []
    for i, item in enumerate(plan, 1):
        cmd = ["rclone", "copyto", item["src"], item["dest"]]
        if DRY:
            cmd.insert(1, "--dry-run")
        print(f"[{i}/{len(plan)}] {Path(item['dest']).name} ← {Path(item['src']).name}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode == 0:
            copied += 1
        else:
            errors.append(f"{item['dest']}: {proc.stderr.strip()[:200]}")

    report = {
        "at": datetime.now(timezone.utc).isoformat(),
        "dry_run": DRY,
        "zero_byte_pdfs": len(zero_pdfs),
        "matched": len(plan),
        "copied": copied,
        "errors": errors,
        "samples": plan[:10],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": not errors,
                "copied": copied,
                "matched": len(plan),
                "report": str(REPORT),
            },
            indent=2,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
