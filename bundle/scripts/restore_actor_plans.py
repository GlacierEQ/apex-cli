#!/usr/bin/env python3
"""Restore canonical CATACLYSM actor plans from FEDERAL-WARFARE vault archive."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
ARCHIVE_ACTORS = (
    HOME
    / "MISSIONS/AEON_777/CORE_MISSION/AEON-BRAIN-777/02_EVIDENCE_VAULT"
    / "CONSOLIDATED_ARCHIVE/1FDV-23-0001009-FEDERAL-WARFARE/THE_CATACLYSM/ACTORS"
)
CURRENT_ACTORS = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/ACTORS"
COMPLETE_STRATEGY = (
    HOME
    / "MISSIONS/AEON_777/CORE_MISSION/AEON-BRAIN-777/02_EVIDENCE_VAULT"
    / "CONSOLIDATED_ARCHIVE/APEX_SUPREME_MEGA_CHUNK_V1/FORENSICS/EXHIBITS"
    / "CATACLYSM__COMPLETE_PER_ACTOR_STRATEGY.md"
)
PERPLEXITY_KB = HOME / "documents/filing_package/PERPLEXITY_LEGAL_KNOWLEDGE_BASE.md"
YAMATANI_INTEL = (
    HOME
    / "MISSIONS/APEX_INFRASTRUCTURE/aspen-grove-operator-v7/research/intelligence/actors/yamatani_profile.md"
)
BROWER_PROFILE = (
    HOME
    / "MISSIONS/APEX_INFRASTRUCTURE/aspen-grove-operator-v7/research/intelligence/actors/brower_complete_profile.md"
)
RESTORE_LOG = HOME / ".supermemory/ops/actor-plans-restore.json"


def main() -> int:
    if not ARCHIVE_ACTORS.is_dir():
        raise SystemExit(f"Archive missing: {ARCHIVE_ACTORS}")

    CURRENT_ACTORS.mkdir(parents=True, exist_ok=True)
    restored = []
    for src in sorted(ARCHIVE_ACTORS.iterdir()):
        if src.name.startswith("."):
            continue
        dest = CURRENT_ACTORS / src.name
        shutil.copy2(src, dest)
        restored.append(src.name)

    # Full contingency master (Perplexity-era complete strategy)
    if COMPLETE_STRATEGY.is_file():
        shutil.copy2(
            COMPLETE_STRATEGY,
            CURRENT_ACTORS / "CONTINGENCY_COMPLETE_PER_ACTOR_STRATEGY.md",
        )
        restored.append("CONTINGENCY_COMPLETE_PER_ACTOR_STRATEGY.md")

    if PERPLEXITY_KB.is_file():
        shutil.copy2(PERPLEXITY_KB, CURRENT_ACTORS / "PERPLEXITY_LEGAL_KNOWLEDGE_BASE.md")
        restored.append("PERPLEXITY_LEGAL_KNOWLEDGE_BASE.md")

    # Intelligence cross-refs
    intel_dir = CURRENT_ACTORS / "INTELLIGENCE"
    intel_dir.mkdir(exist_ok=True)
    for label, src in [("yamatani_profile.md", YAMATANI_INTEL), ("brower_complete_profile.md", BROWER_PROFILE)]:
        if src.is_file():
            shutil.copy2(src, intel_dir / label)

    # Refresh BY_ACTOR plan symlinks
    by_actor = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/EVIDENCE/BY_ACTOR"
    relinked = 0
    for actor_dir in by_actor.iterdir():
        if not actor_dir.is_dir() or actor_dir.name.startswith("_"):
            continue
        plans = actor_dir / "PLANS"
        if plans.is_dir():
            for link in plans.iterdir():
                if link.is_symlink():
                    link.unlink()
                    relinked += 1

    RESTORE_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESTORE_LOG.write_text(
        __import__("json").dumps(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "source": str(ARCHIVE_ACTORS),
                "files_restored": len(restored),
                "symlinks_cleared": relinked,
                "restored": restored,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Restored {len(restored)} files from vault archive")
    print(f"Cleared {relinked} stale PLANS symlinks — run: sm-ops actors --skip-supermemory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())