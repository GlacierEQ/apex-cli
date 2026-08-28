#!/usr/bin/env python3
"""
Unified Memory Connect MCP Server (FastMCP).
Rock-solid gateway: Mem0 · Supermemory · MemoryPlugin · Pinecone · Qdrant · Context7
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_connect_core import (  # noqa: E402
    add_unified,
    get_cache,
    health_check,
    route_layers,
    search_unified,
    source_memory_env,
    write_mesh_config,
)

load_dotenv(Path.home() / ".env", override=True)
source_memory_env()

mcp = FastMCP("UnifiedMemory")


def _json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


@mcp.tool()
async def health_check_tool() -> str:
    """Probe all memory layers — keys + live reachability. No secrets returned."""
    result = await health_check()
    write_mesh_config(result)
    return _json(result)


@mcp.tool()
async def search_unified_memory(
    query: str,
    layers: str = "",
    top_k: int = 4,
    user_id: str = "operator",
) -> str:
    """
    Search across memory layers with dedupe and token limits.
    layers: comma-separated (mem0,supermemory,memory_plugin,pinecone,qdrant,context7) or empty for auto-route.
    """
    layer_list = [x.strip() for x in layers.split(",") if x.strip()] or None
    result = await search_unified(
        query, layers=layer_list, top_k=top_k, user_id=user_id
    )
    return _json(result)


@mcp.tool()
async def add_unified_memory(
    fact: str,
    targets: str = "mem0,supermemory",
    user_id: str = "operator",
) -> str:
    """Dual/multi-write fact to selected memory layers."""
    target_list = [x.strip() for x in targets.split(",") if x.strip()]
    result = await add_unified(fact, targets=target_list, user_id=user_id)
    return _json(result)


@mcp.tool()
async def semantic_memory_router(query: str, user_id: str = "operator") -> str:
    """
    APEX domain router — classifies intent and queries the best memory silo(s).
    Legal/evidence → Pinecone · Docs → Context7 · Cross-session → MemoryPlugin · Default → Mem0+SM
    """
    layers = route_layers(query)
    result = await search_unified(query, layers=layers, top_k=4, user_id=user_id)
    return _json({"routed_layers": layers, **result})


@mcp.tool()
async def add_mem0_fact(
    fact: str, account: str = "pro", user_id: str = "operator"
) -> str:
    """Add fact to Mem0 (backward-compatible with v1 MCP tool)."""
    from memory_connect_core import mem0_add
    import aiohttp

    async with aiohttp.ClientSession() as session:
        result = await mem0_add(session, fact, account=account, user_id=user_id)
    return _json(result)


@mcp.tool()
async def search_mem0_facts(
    query: str, account: str = "pro", user_id: str = "operator"
) -> str:
    """Search Mem0 episodic memory."""
    from memory_connect_core import mem0_search
    import aiohttp

    async with aiohttp.ClientSession() as session:
        items = await mem0_search(session, query, account=account, user_id=user_id)
    return _json(items)


@mcp.tool()
async def search_supermemory_facts(query: str, top_k: int = 4) -> str:
    """Search Supermemory knowledge layer."""
    from memory_connect_core import supermemory_search

    items = await supermemory_search(query, top_k=top_k)
    return _json(items)


@mcp.tool()
async def search_memory_plugin(
    query: str, account: str = "global", top_k: int = 4
) -> str:
    """Search Memory Plugin cross-session store."""
    from memory_connect_core import memory_plugin_search
    import aiohttp

    async with aiohttp.ClientSession() as session:
        items = await memory_plugin_search(session, query, account=account, top_k=top_k)
    return _json(items)


@mcp.tool()
async def query_pinecone_vector(query: str, top_k: int = 4) -> str:
    """Semantic search Pinecone evidence/legal archive."""
    from memory_connect_core import pinecone_search
    import aiohttp

    async with aiohttp.ClientSession() as session:
        items = await pinecone_search(session, query, top_k=top_k)
    return _json(items)


@mcp.tool()
async def query_qdrant_vector(query: str, top_k: int = 4) -> str:
    """Semantic search local Qdrant collection."""
    from memory_connect_core import qdrant_search
    import aiohttp

    async with aiohttp.ClientSession() as session:
        items = await qdrant_search(session, query, top_k=top_k)
    return _json(items)


@mcp.tool()
async def search_context7(query: str, top_k: int = 3) -> str:
    """Search Context7 library/documentation context."""
    from memory_connect_core import context7_search
    import aiohttp

    async with aiohttp.ClientSession() as session:
        items = await context7_search(session, query, top_k=top_k)
    return _json(items)


@mcp.tool()
async def batch_add_fact(
    fact: str,
    targets: str = "mem0,supermemory,memory_plugin",
    user_id: str = "operator",
) -> str:
    """Batch-write a fact to multiple memory targets in one call."""
    target_list = [x.strip() for x in targets.split(",") if x.strip()]
    result = await add_unified(fact, targets=target_list, user_id=user_id)
    return _json(result)


@mcp.tool()
def list_memory_sources() -> str:
    """List configured memory layers and cache stats (no secrets)."""
    from memory_connect_core import KEY_ALIASES, MESH_CONFIG, resolve_key

    layers = {}
    for group in KEY_ALIASES:
        layers[group] = {
            "configured": bool(resolve_key(group)),
            "aliases": KEY_ALIASES[group],
        }
    return _json(
        {
            "layers": layers,
            "cache_entries": len(get_cache()),
            "mesh_config": str(MESH_CONFIG) if MESH_CONFIG.is_file() else "not_built",
        }
    )


@mcp.tool()
def get_apex_cache_stats() -> str:
    """APEX zero-token cache statistics."""
    cache = get_cache()
    prefixes: dict[str, int] = {}
    for key in cache:
        prefix = key.split(":")[0]
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return _json({"total_entries": len(cache), "by_layer": prefixes})


@mcp.tool()
def clear_apex_cache() -> str:
    """Clear local APEX memory cache (forces fresh API calls)."""
    from memory_connect_core import CACHE_FILE

    if CACHE_FILE.is_file():
        CACHE_FILE.unlink()
    return _json({"ok": True, "cleared": str(CACHE_FILE)})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        result = asyncio.run(health_check())
        path = write_mesh_config(result)
        print(_json({"mesh_config": str(path), **result}))
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        print("Starting UnifiedMemory FastMCP server on port 8000 via SSE...")
        mcp.run("sse")
    else:
        mcp.run("stdio")
