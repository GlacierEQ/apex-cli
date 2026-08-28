#!/usr/bin/env python3
"""Verify all memory mesh layers and write MEMORY_MESH.json status."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_connect_core import health_check, source_memory_env, write_mesh_config  # noqa: E402


def _icon(live: bool, key: bool) -> str:
    if live:
        return "LIVE"
    if key:
        return "KEY_ONLY"
    return "OFFLINE"


async def main() -> int:
    source_memory_env()
    print("=" * 60)
    print("  APEX MEMORY MESH — 7-LAYER CONNECTIVITY REPORT")
    print("=" * 60)

    health = await health_check()
    path = write_mesh_config(health)

    layer_order = [
        "mem0",
        "supermemory",
        "memory_plugin",
        "pinecone",
        "qdrant",
        "context7",
    ]
    for name in layer_order:
        info = health["layers"].get(
            name, health["layers"].get("mem0_pro" if name == "mem0" else name, {})
        )
        if name == "mem0":
            info = health["layers"].get("mem0", {})
        key_ok = info.get("key_present", False)
        live = info.get("live", False)
        detail = info.get("detail", "")
        print(f"  {name:18} {_icon(live, key_ok):10} {detail}")

    summary = health.get("summary", {})
    print("=" * 60)
    print(f"  Live: {summary.get('layers_live', 0)}/{summary.get('layers_total', 0)}")
    print(f"  Cache entries: {summary.get('cache_entries', 0)}")
    print(f"  Mesh config: {path}")
    print("=" * 60)

    # Also write compact report
    report_path = Path.home() / ".apex" / "memory_mesh_report.json"
    report_path.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")

    live = summary.get("layers_live", 0)
    # Core mesh: mem0 + supermemory + context7 minimum; vector layers optional
    return 0 if live >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
