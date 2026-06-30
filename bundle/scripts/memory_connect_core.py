#!/usr/bin/env python3
"""
APEX Memory Connect Core — rock-solid multi-layer memory mesh.

Layers: Mem0 · Supermemory · MemoryPlugin · Pinecone · Qdrant · Context7
Token discipline: cache-first, dedupe, truncate, top-k limits.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
CACHE_DIR = HOME / ".apex_cache"
CACHE_FILE = CACHE_DIR / "memory_hits.json"
MESH_CONFIG = HOME / ".apex" / "MEMORY_MESH.json"

MAX_FACT_LENGTH = 1000
SIMILARITY_THRESHOLD = 0.75
DEFAULT_TOP_K = 4

ENV_SOURCES = [
    HOME / ".gemini_keys",
    HOME / ".operator_key_vault" / "gatekeeper.env",
    HOME / ".apex_vault" / "AGENTS" / "MASTER.env",
    HOME / ".env",
]

KEY_ALIASES: dict[str, list[str]] = {
    "mem0_pro": ["MEM0_PRO_API_KEY", "MEM0_PRO", "MEM0_API_KEY", "MEM_API_KEY"],
    "mem0_reg": ["MEM0_REG_API_KEY", "MEM0_HI1", "MEM0GLACIEREQ"],
    "supermemory": ["SUPERMEMORY_PRIMARY_KEY", "SUPERMEMORY_KEY", "SUPERMEMORY_API_KEY", "SUPERMEMORY"],
    "memory_global": ["MEMORY_GLOBAL_KEY", "MEMORY_PLUGIN_PRIMARY", "MEMORY_PLUGIN"],
    "memory_direct": ["MEMORY_DIRECT_KEY", "MEMORY_PLUGIN_SPECIALIZED", "MEMORY_PLUGIN_2_EVIDENCE"],
    "pinecone": ["PINECONE_PRIMARY_KEY", "PINECONE_API_KEY", "PINECONE"],
    "qdrant": ["QDRANT_KEY", "QDRANT"],
    "context7": ["CONTEXT7", "CONTEXT7_API_KEY"],
    "openai_embed": [
        "OPENAI_WINDSURF_KEY",
        "OPENAI_API_KEY",
        "OPENAI_WINDSURF",
        "OPENAI_KEY",
        "BDDDE66_COHERE_API_KEY",
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


def source_memory_env() -> None:
    """Load memory credentials from vault sources (setdefault — never override)."""
    for path in ENV_SOURCES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)


def resolve_key(group: str) -> str | None:
    source_memory_env()
    for alias in KEY_ALIASES.get(group, [group]):
        val = os.environ.get(alias)
        if val:
            return val
    return None


def get_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def set_cache(key: str, val: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = get_cache()
    cache[key] = val
    if len(cache) > 500:
        for k in list(cache.keys())[:100]:
            del cache[k]
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def truncate(text: str, limit: int = MAX_FACT_LENGTH) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        text = normalize_text(item.get("text", ""))
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(item)
    return out


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())[:500]


def pack_results(items: list[dict[str, Any]], top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    items = dedupe_items(items)
    items.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
    return items[:top_k]


# ─── Mem0 (delegates to mem0_master_apex) ───────────────────────────────────

def _mem0_master(account: str, user_id: str, agent_id: str = "apex-grok"):
    import sys
    scripts = HOME / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from mem0_master_apex import Mem0Master, Mem0Scope
    return Mem0Master(account=account, scope=Mem0Scope(user_id=user_id, agent_id=agent_id))  # type: ignore


async def mem0_search(
    session: aiohttp.ClientSession,
    query: str,
    *,
    account: str = "pro",
    user_id: str = "operator",
    agent_id: str = "apex-grok",
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    del session
    cache_key = f"mem0:{account}:{user_id}:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)

    try:
        m = _mem0_master(account, user_id, agent_id)
        results = await asyncio.to_thread(m.search, query, top_k=top_k, rerank=True, threshold=0.3)
        out = []
        for r in results or []:
            text = (r.get("memory") or r.get("text") or r.get("content") or "").strip()
            if text:
                out.append({"layer": "mem0", "source": "[M]", "text": truncate(text), "score": float(r.get("score", 0.5))})
        set_cache(cache_key, json.dumps(out))
        return out
    except Exception as e:
        return [{"layer": "mem0", "error": str(e)[:200]}]


async def mem0_add(
    session: aiohttp.ClientSession,
    fact: str,
    *,
    account: str = "pro",
    user_id: str = "operator",
    agent_id: str = "apex-grok",
) -> dict[str, Any]:
    del session  # master uses httpx
    try:
        m = _mem0_master(account, user_id, agent_id)
        result = await asyncio.to_thread(m.add, truncate(fact), infer=True)
        return {"ok": True, "layer": "mem0", "result": result}
    except Exception as e:
        return {"ok": False, "layer": "mem0", "error": str(e)[:200]}


# ─── Supermemory ────────────────────────────────────────────────────────────

def _supermemory_cli_search(query: str, top_k: int) -> list[dict[str, Any]]:
    tag = os.environ.get("SUPERMEMORY_TAG", "apex-home")
    try:
        proc = subprocess.run(
            ["supermemory", "search", query, "--tag", tag, "--limit", str(top_k), "--mode", "hybrid", "--rerank", "--json"],
            capture_output=True, text=True, timeout=45, cwd=str(HOME),
        )
        if proc.returncode != 0:
            return [{"layer": "supermemory", "error": proc.stderr[:200] or "cli_failed"}]
        data = json.loads(proc.stdout)
        out = []
        for r in data.get("results", []):
            text = (r.get("memory") or r.get("content") or "").strip()
            if text:
                out.append({
                    "layer": "supermemory",
                    "source": "[S]",
                    "text": truncate(text),
                    "score": float(r.get("similarity", 0.5)),
                })
        return out
    except Exception as e:
        return [{"layer": "supermemory", "error": str(e)[:200]}]


async def supermemory_search(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    cache_key = f"supermemory:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)
    # CLI is sync; run in thread would be ideal — subprocess is fine for Termux
    out = _supermemory_cli_search(query, top_k)
    if out and "error" not in out[0]:
        set_cache(cache_key, json.dumps(out))
    return out


async def supermemory_add(fact: str) -> dict[str, Any]:
    tag = os.environ.get("SUPERMEMORY_TAG", "apex-home")
    try:
        proc = subprocess.run(
            ["supermemory", "remember", truncate(fact), "--tag", tag, "--static"],
            capture_output=True, text=True, timeout=45, cwd=str(HOME),
        )
        return {"ok": proc.returncode == 0, "layer": "supermemory", "detail": (proc.stdout or proc.stderr)[:300]}
    except Exception as e:
        return {"ok": False, "layer": "supermemory", "error": str(e)[:200]}


# ─── Memory Plugin ──────────────────────────────────────────────────────────

def _memory_plugin_config() -> tuple[str, str, str]:
    source_memory_env()
    base = (
        os.environ.get("MEMORY_PLUGIN_ENDPOINT")
        or os.environ.get("CONST_MP_MEMORY_ENDPOINT", "").replace("MP_API + ", "").split("?")[0]
        or "https://memory.glaciereq.app"
    )
    if not base.startswith("http"):
        base = "https://memory.glaciereq.app"
    token = resolve_key("memory_global") or resolve_key("memory_direct") or ""
    return base.rstrip("/"), token, "global"


async def memory_plugin_search(
    session: aiohttp.ClientSession,
    query: str,
    *,
    account: str = "global",
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    base, token, _ = _memory_plugin_config()
    if not token:
        return [{"layer": "memory_plugin", "error": "no_api_key"}]

    cache_key = f"mp:{account}:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)

    key = resolve_key("memory_global") if account == "global" else resolve_key("memory_direct")
    if not key:
        return [{"layer": "memory_plugin", "error": "no_account_key"}]

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    endpoints = [
        f"{base}/api/v2/memory/search",
        f"{base}/v2/memory/search",
        f"{base}/api/memory/search",
    ]
    body = {"query": query, "limit": top_k}
    for url in endpoints:
        try:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                items = data if isinstance(data, list) else data.get("results", data.get("memories", data.get("data", [])))
                out = []
                for r in items or []:
                    text = (r.get("content") or r.get("memory") or r.get("text") or "").strip()
                    if text:
                        out.append({"layer": "memory_plugin", "source": "[MP]", "text": truncate(text), "score": float(r.get("score", 0.5))})
                if out:
                    set_cache(cache_key, json.dumps(out))
                    return out
        except Exception:
            continue
    return [{"layer": "memory_plugin", "error": "endpoint_unreachable", "base": base}]


async def memory_plugin_add(
    session: aiohttp.ClientSession,
    fact: str,
    *,
    account: str = "global",
) -> dict[str, Any]:
    base, _, _ = _memory_plugin_config()
    key = resolve_key("memory_global") if account == "global" else resolve_key("memory_direct")
    if not key:
        return {"ok": False, "layer": "memory_plugin", "error": "no_api_key"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"content": truncate(fact), "type": "fact"}
    for url in (f"{base}/api/v2/memory", f"{base}/v2/memory", f"{base}/api/memory"):
        try:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status in (200, 201):
                    return {"ok": True, "layer": "memory_plugin", "status": resp.status}
        except Exception:
            continue
    return {"ok": False, "layer": "memory_plugin", "error": "endpoint_unreachable"}


# ─── Embeddings (shared Pinecone + Qdrant) ──────────────────────────────────

async def embed_query(session: aiohttp.ClientSession, query: str) -> list[float] | None:
    openai_key = resolve_key("openai_embed")
    if openai_key and not openai_key.startswith("co-"):
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        body = {"input": [query], "model": "text-embedding-ada-002"}
        async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["data"][0]["embedding"]

    cohere_key = os.environ.get("BDDDE66_COHERE_API_KEY") or os.environ.get("COHERE_API_KEY")
    if cohere_key:
        url = "https://api.cohere.com/v1/embed"
        headers = {"Authorization": f"Bearer {cohere_key}", "Content-Type": "application/json"}
        body = {"texts": [query], "model": "embed-english-v3.0", "input_type": "search_query"}
        async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                emb = data.get("embeddings", [[]])[0]
                if emb:
                    return emb
    return None


# ─── Pinecone ───────────────────────────────────────────────────────────────

async def pinecone_search(session: aiohttp.ClientSession, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    cache_key = f"pinecone:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)

    pc_key = resolve_key("pinecone")
    vector = await embed_query(session, query)
    if not pc_key or not vector:
        return [{"layer": "pinecone", "error": "missing_key_or_embedding"}]

    host = os.environ.get("PINECONE_HOST") or "apex-main-xwjbbs7.svc.aped-4627-b74a.pinecone.io"
    url = f"https://{host}/query"
    headers = {"Api-Key": pc_key, "Content-Type": "application/json"}
    body = {"vector": vector, "topK": top_k, "includeMetadata": True}
    async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            return [{"layer": "pinecone", "error": f"status_{resp.status}"}]
        data = await resp.json()
        out = []
        for m in data.get("matches", []):
            if m.get("score", 0) < SIMILARITY_THRESHOLD:
                continue
            meta = m.get("metadata") or {}
            text = (meta.get("text") or meta.get("content") or "").strip()
            if text:
                out.append({"layer": "pinecone", "source": "[PC]", "text": truncate(text), "score": float(m.get("score", 0))})
        set_cache(cache_key, json.dumps(out))
        return out


# ─── Qdrant ─────────────────────────────────────────────────────────────────

def _qdrant_base_url() -> str | None:
    endpoint = os.environ.get("QDRANT_ENDPOINT", "").strip().rstrip("/")
    if endpoint.startswith("http"):
        return endpoint
    host = os.environ.get("QDRANT_HOST") or "localhost"
    port = int(os.environ.get("QDRANT_PORT") or "6333")
    scheme = "https" if port == 443 else "http"
    return f"{scheme}://{host}:{port}"


async def qdrant_search(session: aiohttp.ClientSession, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    cache_key = f"qdrant:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)

    base = _qdrant_base_url()
    if not base:
        return [{"layer": "qdrant", "error": "no_endpoint"}]

    collection = os.environ.get("QDRANT_COLLECTION") or "apex_memory"
    api_key = resolve_key("qdrant")

    # Local socket check only for non-HTTPS endpoints
    if base.startswith("http://"):
        host_part = base.split("://", 1)[1]
        host, _, port_s = host_part.partition(":")
        port = int(port_s or "6333")
        s = socket.socket()
        s.settimeout(1.5)
        if s.connect_ex((host, port)) != 0:
            s.close()
            return [{"layer": "qdrant", "error": "offline", "host": host, "port": port}]
        s.close()

    vector = await embed_query(session, query)
    if not vector:
        return [{"layer": "qdrant", "error": "no_embedding"}]

    url = f"{base}/collections/{collection}/points/search"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    body = {"vector": vector, "limit": top_k, "with_payload": True}
    try:
        async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                return [{"layer": "qdrant", "error": f"status_{resp.status}", "detail": (await resp.text())[:200]}]
            data = await resp.json()
            out = []
            for pt in data.get("result", []):
                payload = pt.get("payload") or {}
                text = (payload.get("text") or payload.get("content") or "").strip()
                score = float(pt.get("score", 0))
                if text and score >= SIMILARITY_THRESHOLD:
                    out.append({"layer": "qdrant", "source": "[QD]", "text": truncate(text), "score": score})
            set_cache(cache_key, json.dumps(out))
            return out
    except (aiohttp.ClientError, OSError) as e:
        return [{"layer": "qdrant", "error": "unreachable", "detail": str(e)[:120]}]


# ─── Context7 ───────────────────────────────────────────────────────────────

async def context7_search(session: aiohttp.ClientSession, query: str, top_k: int = 3) -> list[dict[str, Any]]:
    key = resolve_key("context7")
    if not key:
        return [{"layer": "context7", "error": "no_api_key"}]

    cache_key = f"context7:{_query_hash(query)}"
    if cached := get_cache().get(cache_key):
        return json.loads(cached)

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    endpoints = [
        ("GET", f"https://context7.com/api/v1/search?query={query}&limit={top_k}", None),
        ("POST", "https://context7.com/api/v1/search", {"query": query, "limit": top_k}),
        ("POST", "https://api.context7.com/v1/search", {"query": query, "limit": top_k}),
    ]
    for method, url, body in endpoints:
        try:
            kwargs: dict[str, Any] = {"headers": headers, "timeout": aiohttp.ClientTimeout(total=25)}
            if method == "POST" and body:
                kwargs["json"] = body
            async with session.request(method, url, **kwargs) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                items = data if isinstance(data, list) else data.get("results", data.get("data", []))
                out = []
                for r in items or []:
                    text = (r.get("content") or r.get("snippet") or r.get("text") or r.get("title") or "").strip()
                    if text:
                        out.append({
                            "layer": "context7",
                            "source": "[C7]",
                            "text": truncate(text),
                            "score": float(r.get("score", 0.6)),
                            "library": r.get("library", r.get("id", "")),
                        })
                if out:
                    set_cache(cache_key, json.dumps(out))
                    return out[:top_k]
        except Exception:
            continue
    return [{"layer": "context7", "error": "endpoint_unreachable"}]


# ─── Unified router ───────────────────────────────────────────────────────────

LAYER_KEYWORDS: dict[str, list[str]] = {
    "context7": ["docs", "library", "api reference", "sdk", "framework", "npm", "pypi", "documentation"],
    "pinecone": ["evidence", "legal", "precedent", "pdf", "document", "exhibit", "brief", "court", "law"],
    "memory_plugin": ["session", "built", "discussed", "operator state", "cross-session", "plugin"],
    "supermemory": ["link", "url", "repo", "github", "bookmark", "knowledge", "durable"],
    "qdrant": ["local", "vector", "embedding", "collection", "indexed"],
    "mem0": [],  # default fallback
}


def route_layers(query: str, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        return explicit
    q = query.lower()
    for layer, keywords in LAYER_KEYWORDS.items():
        if any(k in q for k in keywords):
            return [layer, "mem0", "supermemory"]
    return ["mem0", "supermemory", "memory_plugin"]


async def search_unified(
    query: str,
    *,
    layers: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
    user_id: str = "operator",
) -> dict[str, Any]:
    source_memory_env()
    target_layers = route_layers(query, layers)
    all_items: list[dict[str, Any]] = []
    layer_results: dict[str, Any] = {}

    async with aiohttp.ClientSession() as session:
        for layer in target_layers:
            if layer == "mem0":
                items = await mem0_search(session, query, user_id=user_id, top_k=top_k)
            elif layer == "supermemory":
                items = await supermemory_search(query, top_k=top_k)
            elif layer == "memory_plugin":
                items = await memory_plugin_search(session, query, top_k=top_k)
            elif layer == "pinecone":
                items = await pinecone_search(session, query, top_k=top_k)
            elif layer == "qdrant":
                items = await qdrant_search(session, query, top_k=top_k)
            elif layer == "context7":
                items = await context7_search(session, query, top_k=top_k)
            else:
                continue
            layer_results[layer] = items
            if items and "error" not in items[0]:
                all_items.extend(items)

    packed = pack_results(all_items, top_k=top_k * 2)
    return {
        "query": query,
        "layers_queried": target_layers,
        "layer_results": layer_results,
        "unified": packed,
        "count": len(packed),
        "at": _now(),
    }


async def add_unified(
    fact: str,
    *,
    targets: list[str] | None = None,
    user_id: str = "operator",
) -> dict[str, Any]:
    source_memory_env()
    targets = targets or ["mem0", "supermemory"]
    results: dict[str, Any] = {}
    async with aiohttp.ClientSession() as session:
        for t in targets:
            if t == "mem0":
                results["mem0"] = await mem0_add(session, fact, user_id=user_id)
            elif t == "supermemory":
                results["supermemory"] = await supermemory_add(fact)
            elif t == "memory_plugin":
                results["memory_plugin"] = await memory_plugin_add(session, fact)
    return {"ok": any(r.get("ok") for r in results.values()), "results": results, "at": _now()}


def _layer_live(items: list[dict[str, Any]]) -> tuple[bool, str]:
    if not items:
        return False, "empty"
    if items[0].get("error"):
        return False, str(items[0].get("error"))
    return True, "ok"


async def _mem0_ping(session: aiohttp.ClientSession) -> tuple[bool, str]:
    del session
    try:
        h = await asyncio.to_thread(_mem0_master("pro", "casey").health)
        return h.get("ok", False), "ok" if h.get("ok") else h.get("error", "fail")
    except Exception as e:
        return False, str(e)[:80]


async def _memory_plugin_ping(session: aiohttp.ClientSession) -> tuple[bool, str]:
    base, _, _ = _memory_plugin_config()
    key = resolve_key("memory_global") or resolve_key("memory_direct")
    if not key:
        return False, "no_api_key"
    headers = {"Authorization": f"Bearer {key}"}
    for path in ("/health", "/api/health", "/api/v2/health", "/"):
        try:
            async with session.get(f"{base}{path}", headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status in (200, 204):
                    return True, f"ok:{path}"
        except Exception:
            continue
    items = await memory_plugin_search(session, "ping", top_k=1)
    return _layer_live(items)


async def health_check() -> dict[str, Any]:
    """Probe all memory layers — keys present + live reachability."""
    source_memory_env()
    status: dict[str, Any] = {"at": _now(), "layers": {}}

    async with aiohttp.ClientSession() as session:
        mem0_live, mem0_detail = await _mem0_ping(session)
        status["layers"]["mem0"] = {
            "key_present": bool(resolve_key("mem0_pro")),
            "live": mem0_live,
            "detail": mem0_detail,
        }

        sm_items = await supermemory_search("health_check", top_k=1)
        sm_live, sm_detail = _layer_live(sm_items)
        status["layers"]["supermemory"] = {
            "key_present": bool(resolve_key("supermemory")),
            "live": sm_live,
            "detail": sm_detail,
        }

        mp_live, mp_detail = await _memory_plugin_ping(session)
        status["layers"]["memory_plugin"] = {
            "key_present": bool(resolve_key("memory_global") or resolve_key("memory_direct")),
            "live": mp_live,
            "detail": mp_detail,
            "optional": True,
        }

        pc_items = await pinecone_search(session, "legal evidence", top_k=1)
        pc_live, pc_detail = _layer_live(pc_items)
        pc_key = bool(resolve_key("pinecone"))
        status["layers"]["pinecone"] = {
            "key_present": pc_key,
            "live": pc_live,
            "detail": pc_detail if pc_live else (pc_detail if pc_key else "no_api_key"),
            "optional": not pc_live and pc_key,
        }

        qd_items = await qdrant_search(session, "health", top_k=1)
        qd_live, qd_detail = _layer_live(qd_items)
        status["layers"]["qdrant"] = {
            "key_present": bool(resolve_key("qdrant") or os.environ.get("QDRANT_ENDPOINT")),
            "live": qd_live,
            "detail": qd_detail,
            "optional": True,
        }

        c7_items = await context7_search(session, "python", top_k=1)
        c7_live, c7_detail = _layer_live(c7_items)
        status["layers"]["context7"] = {
            "key_present": bool(resolve_key("context7")),
            "live": c7_live,
            "detail": c7_detail,
        }

    live_count = sum(
        1 for v in status["layers"].values()
        if isinstance(v, dict) and v.get("live") is True
    )
    status["summary"] = {
        "layers_total": len(status["layers"]),
        "layers_live": live_count,
        "cache_entries": len(get_cache()),
    }
    return status


async def _cli_main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="APEX memory connect CLI")
    ap.add_argument("command", choices=["health", "search", "add", "route"])
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--layers", default="")
    ap.add_argument("--targets", default="mem0,supermemory")
    ap.add_argument("--user-id", default="operator")
    args = ap.parse_args()

    if args.command == "health":
        h = await health_check()
        path = write_mesh_config(h)
        print(json.dumps({"mesh_config": str(path), **h}, indent=2))
        return 0

    if args.command == "search":
        layers = [x.strip() for x in args.layers.split(",") if x.strip()] or None
        r = await search_unified(args.query, layers=layers, user_id=args.user_id)
        print(json.dumps(r, indent=2))
        return 0

    if args.command == "route":
        layers = route_layers(args.query)
        r = await search_unified(args.query, layers=layers, user_id=args.user_id)
        print(json.dumps({"routed_layers": layers, **r}, indent=2))
        return 0

    if args.command == "add":
        targets = [x.strip() for x in args.targets.split(",") if x.strip()]
        r = await add_unified(args.query, targets=targets, user_id=args.user_id)
        print(json.dumps(r, indent=2))
        return 0 if r.get("ok") else 1

    return 1


def write_mesh_config(health: dict[str, Any]) -> Path:
    APEX = HOME / ".apex"
    APEX.mkdir(parents=True, exist_ok=True)
    mesh = {
        "version": "1.0",
        "at": _now(),
        "profile": "coremaximized",
        "layers": ["mem0", "supermemory", "memory_plugin", "pinecone", "qdrant", "context7"],
        "routing": {
            "default": ["mem0", "supermemory", "memory_plugin"],
            "legal_evidence": ["pinecone", "mem0"],
            "documentation": ["context7", "supermemory"],
            "local_vector": ["qdrant", "pinecone"],
            "cross_session": ["memory_plugin", "mem0"],
        },
        "token_rules": {
            "max_fact_length": MAX_FACT_LENGTH,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "cache_file": str(CACHE_FILE),
            "default_top_k": DEFAULT_TOP_K,
        },
        "health": health,
        "mcp": {
            "server": "unified-memory",
            "script": str(HOME / "scripts" / "unified_memory_mcp.py"),
            "gatekeeper_route": "colossus-gatekeeper → memory_route",
        },
    }
    MESH_CONFIG.write_text(json.dumps(mesh, indent=2) + "\n", encoding="utf-8")
    (APEX / "memory_layer_status.json").write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    return MESH_CONFIG


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_cli_main()))