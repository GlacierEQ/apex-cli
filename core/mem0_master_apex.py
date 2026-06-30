#!/usr/bin/env python3
"""
APEX Mem0 Master — unified platform client (REST + optional SDK).

Tier 1: org/project headers, batch ops, async
Tier 2: add/search with metadata, categories, expiration, immutable
Tier 3: history, export, feedback, v2/v3 APIs
Tier 4: dual-account routing (pro + regular)
Tier 5: health, cache, CLI

Accounts (keys from env — never hardcode):
  pro  → MEM0_PRO_API_KEY / MEM0_PRO  (casey@hi-classhomeservices.com, user_id: casey)
  reg  → MEM0_REG_API_KEY / MEM0_HI1  (higuy.vids@gmail.com, user_id: higuy)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
CACHE_DIR = HOME / ".apex_cache"
CACHE_FILE = CACHE_DIR / "mem0_master_cache.json"
BASE_URL = "https://api.mem0.ai"

AccountName = Literal["pro", "reg"]

ENV_SOURCES = [
    HOME / ".gemini_keys",
    HOME / ".operator_key_vault" / "gatekeeper.env",
    HOME / ".apex_vault" / "AGENTS" / "MASTER.env",
    HOME / ".env",
]

ACCOUNT_PROFILES: dict[AccountName, dict[str, str]] = {
    "pro": {
        "email": "casey@hi-classhomeservices.com",
        "default_user_id": "casey",
        "default_agent_id": "apex-grok",
        "tier": "PRO",
    },
    "reg": {
        "email": "higuy.vids@gmail.com",
        "default_user_id": "higuy",
        "default_agent_id": "apex-grok",
        "tier": "REGULAR",
    },
}

KEY_ALIASES: dict[AccountName, list[str]] = {
    "pro": ["MEM0_PRO_API_KEY", "MEM0_PRO", "MEM0_API_KEY", "MEM_API_KEY"],
    "reg": ["MEM0_REG_API_KEY", "MEM0_HI1", "MEM0GLACIEREQ"],
}


def source_env() -> None:
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
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def resolve_api_key(account: AccountName) -> str:
    source_env()
    for alias in KEY_ALIASES[account]:
        if val := os.environ.get(alias):
            return val
    raise RuntimeError(f"Mem0 API key missing for account '{account}'. Set one of: {KEY_ALIASES[account]}")


def _cache_get(key: str) -> Any | None:
    if not CACHE_FILE.is_file():
        return None
    try:
        return json.loads(CACHE_FILE.read_text()).get(key)
    except json.JSONDecodeError:
        return None


def _cache_set(key: str, val: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if CACHE_FILE.is_file():
        try:
            data = json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    data[key] = val
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class Mem0Scope:
    user_id: str | None = None
    agent_id: str | None = None
    app_id: str | None = None
    run_id: str | None = None
    org_id: str | None = None
    project_id: str | None = None

    def filters(self) -> dict[str, Any]:
        f: dict[str, Any] = {}
        if self.user_id:
            f["user_id"] = self.user_id
        if self.agent_id:
            f["agent_id"] = self.agent_id
        if self.app_id:
            f["app_id"] = self.app_id
        if self.run_id:
            f["run_id"] = self.run_id
        return f

    def top_level_ids(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for k in ("user_id", "agent_id", "app_id", "run_id"):
            if v := getattr(self, k):
                out[k] = v
        return out


@dataclass
class Mem0Master:
    """Synchronous Mem0 platform client — full API surface."""

    account: AccountName = "pro"
    scope: Mem0Scope = field(default_factory=Mem0Scope)
    timeout: float = 45.0

    def __post_init__(self) -> None:
        profile = ACCOUNT_PROFILES[self.account]
        if not self.scope.user_id:
            self.scope.user_id = profile["default_user_id"]
        if not self.scope.agent_id:
            self.scope.agent_id = profile["default_agent_id"]
        if not self.scope.org_id:
            self.scope.org_id = os.environ.get("MEM0_ORG_ID")
        if not self.scope.project_id:
            self.scope.project_id = os.environ.get("MEM0_PROJECT_ID")
        self._api_key = resolve_api_key(self.account)

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.scope.org_id:
            h["x-mem0-org-id"] = self.scope.org_id
        if self.scope.project_id:
            h["x-mem0-project-id"] = self.scope.project_id
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | list | None = None,
        params: dict | None = None,
    ) -> Any:
        url = f"{BASE_URL}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.request(method, url, headers=self._headers(), json=json_body, params=params)
            if r.status_code >= 400:
                raise RuntimeError(f"Mem0 {method} {path} → {r.status_code}: {r.text[:400]}")
            if not r.content:
                return {}
            return r.json()

    # ── TIER 2: Add ───────────────────────────────────────────────────────

    def add(
        self,
        content: str | list[dict[str, str]],
        *,
        metadata: dict | None = None,
        infer: bool = True,
        output_format: str = "v1.1",
        immutable: bool = False,
        async_mode: bool = False,
        expiration_date: str | None = None,
        custom_categories: dict | None = None,
        custom_instructions: str | None = None,
        includes: str | None = None,
        excludes: str | None = None,
        version: str = "v2",
        use_v3: bool = True,
    ) -> dict[str, Any]:
        messages = content if isinstance(content, list) else [{"role": "user", "content": str(content)}]
        body: dict[str, Any] = {
            "messages": messages,
            "infer": infer,
            "output_format": output_format,
            "immutable": immutable,
            "async_mode": async_mode,
            "version": version,
            **self.scope.top_level_ids(),
        }
        if metadata:
            body["metadata"] = metadata
        if expiration_date:
            body["expiration_date"] = expiration_date
        if custom_categories:
            body["custom_categories"] = custom_categories
        if custom_instructions:
            body["custom_instructions"] = custom_instructions
        if includes:
            body["includes"] = includes
        if excludes:
            body["excludes"] = excludes
        path = "/v3/memories/add/" if use_v3 else "/v1/memories/"
        return self._request("POST", path, json_body=body)

    # ── TIER 2: Search ────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        rerank: bool = True,
        threshold: float | None = 0.3,
        metadata_filter: dict | None = None,
        api_version: Literal["v3", "v2", "v1"] = "v3",
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        cache_key = hashlib.sha256(f"{self.account}:{query}:{top_k}".encode()).hexdigest()
        if use_cache and (cached := _cache_get(cache_key)):
            return cached

        filters = {**self.scope.filters(), **(metadata_filter or {})}
        if api_version == "v3":
            body: dict[str, Any] = {
                "query": query,
                "top_k": top_k,
                "rerank": rerank,
                "filters": filters,
            }
            if threshold is not None:
                body["threshold"] = threshold
            data = self._request("POST", "/v3/memories/search/", json_body=body)
        elif api_version == "v2":
            body = {"query": query, "filters": filters, "top_k": top_k}
            data = self._request("POST", "/v2/memories/search/", json_body=body)
        else:
            body = {"query": query, "filters": filters}
            data = self._request("POST", "/v1/memories/search/", json_body=body)

        results = data if isinstance(data, list) else data.get("results", data.get("memories", []))
        results = results or []
        if use_cache:
            _cache_set(cache_key, results)
        return results

    # ── TIER 3: Read ──────────────────────────────────────────────────────

    def get(self, memory_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/memories/{memory_id}/")

    def get_all(self, *, limit: int = 100, page: int = 1, api_version: Literal["v2", "v1"] = "v2") -> Any:
        """List memories — v2 uses POST with filters; v1 supports GET."""
        if api_version == "v2":
            body = {**self.scope.filters(), "limit": limit, "page": page}
            return self._request("POST", "/v2/memories/", json_body=body)
        params = {**self.scope.top_level_ids(), "limit": limit, "page": page}
        return self._request("GET", "/v1/memories/", params=params)

    def history(self, memory_id: str) -> Any:
        return self._request("GET", f"/v1/memories/{memory_id}/history/")

    # ── TIER 3: Update / Delete ───────────────────────────────────────────

    def update(self, memory_id: str, text: str) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/v1/memories/{memory_id}/",
            json_body={"text": text},
        )

    def batch_update(self, memories: list[dict[str, str]]) -> dict[str, Any]:
        """Each item: {"memory_id": "...", "text": "..."}"""
        return self._request("PUT", "/v1/memories/batch/", json_body={"memories": memories})

    def delete(self, memory_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/memories/{memory_id}/")

    def batch_delete(self, memory_ids: list[str]) -> dict[str, Any]:
        return self._request("DELETE", "/v1/memories/batch/", json_body={"memory_ids": memory_ids})

    def delete_all(self) -> dict[str, Any]:
        return self._request("DELETE", "/v1/memories/", json_body=self.scope.filters())

    # ── TIER 3: Export & Feedback ─────────────────────────────────────────

    def create_export(self, *, format: str = "json") -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/memories/export/",
            json_body={**self.scope.filters(), "format": format},
        )

    def get_export(self, export_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/memories/export/{export_id}/")

    def feedback(self, memory_id: str, feedback: str, *, reason: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"memory_id": memory_id, "feedback": feedback}
        if reason:
            body["reason"] = reason
        return self._request("POST", "/v1/memories/feedback/", json_body=body)

    # ── TIER 4: Health ────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        try:
            hits = self.search("health ping", top_k=1, use_cache=False)
            return {
                "ok": True,
                "account": self.account,
                "email": ACCOUNT_PROFILES[self.account]["email"],
                "user_id": self.scope.user_id,
                "search_ok": True,
                "hits": len(hits),
            }
        except Exception as e:
            return {"ok": False, "account": self.account, "error": str(e)[:200]}


class AsyncMem0Master:
    """Async Mem0 platform client — parallel batch + non-blocking ingest."""

    def __init__(self, account: AccountName = "pro", scope: Mem0Scope | None = None) -> None:
        self._sync = Mem0Master(account=account, scope=scope or Mem0Scope())
        self.account = account

    def _headers(self) -> dict[str, str]:
        return self._sync._headers()

    async def _request(self, method: str, path: str, *, json_body: dict | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=self._sync.timeout) as client:
            r = await client.request(method, url, headers=self._headers(), json=json_body)
            if r.status_code >= 400:
                raise RuntimeError(f"Mem0 async {method} {path} → {r.status_code}: {r.text[:400]}")
            return r.json() if r.content else {}

    async def add(self, content: str | list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync.add, content, **kwargs)

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._sync.search, query, **kwargs)

    async def batch_add(self, facts: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        return await asyncio.gather(*[self.add(f, **kwargs) for f in facts])


def dual_search(query: str, *, top_k: int = 4) -> dict[str, Any]:
    """Search both pro + regular accounts, dedupe by text."""
    out: dict[str, Any] = {"query": query, "accounts": {}}
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for acct in ("pro", "reg"):
        try:
            m = Mem0Master(account=acct)  # type: ignore
            hits = m.search(query, top_k=top_k, use_cache=True)
            out["accounts"][acct] = hits
            for h in hits:
                text = (h.get("memory") or h.get("text") or "").strip().lower()
                if text and text not in seen:
                    seen.add(text)
                    merged.append({**h, "account": acct})
        except Exception as e:
            out["accounts"][acct] = {"error": str(e)[:200]}
    out["merged"] = merged[: top_k * 2]
    return out


def try_sdk_demo() -> dict[str, Any]:
    """Optional MemoryClient SDK path if mem0 package installed."""
    try:
        from mem0 import AsyncMemoryClient, MemoryClient  # type: ignore
    except ImportError:
        return {"sdk": False, "reason": "pip install mem0ai not present — REST client active"}

    key = resolve_api_key("pro")
    client = MemoryClient(api_key=key)
    scope = Mem0Scope(user_id="casey")
    filters = scope.filters()
    try:
        all_mem = client.get_all(filters=filters, limit=1)
        return {"sdk": True, "get_all_ok": True, "sample": str(all_mem)[:200]}
    except Exception as e:
        return {"sdk": True, "get_all_ok": False, "error": str(e)[:200]}


def cli() -> int:
    ap = argparse.ArgumentParser(description="APEX Mem0 Master CLI")
    ap.add_argument("command", choices=[
        "health", "add", "search", "get", "get-all", "history", "update", "delete",
        "batch-delete", "export", "dual-search", "sdk-check", "demo",
    ])
    ap.add_argument("args", nargs="*", help="content, query, or memory_id")
    ap.add_argument("--account", choices=["pro", "reg"], default="pro")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--agent-id", default="apex-grok")
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--metadata", default="", help='JSON metadata for add')
    ap.add_argument("--immutable", action="store_true")
    ap.add_argument("--no-infer", action="store_true")
    ns = ap.parse_args()

    scope = Mem0Scope(
        user_id=ns.user_id or None,
        agent_id=ns.agent_id,
    )
    m = Mem0Master(account=ns.account, scope=scope)

    if ns.command == "health":
        print(json.dumps({"pro": Mem0Master("pro").health(), "reg": Mem0Master("reg").health()}, indent=2))
        return 0

    if ns.command == "dual-search":
        print(json.dumps(dual_search(" ".join(ns.args) or "apex operator", top_k=ns.top_k), indent=2))
        return 0

    if ns.command == "sdk-check":
        print(json.dumps(try_sdk_demo(), indent=2))
        return 0

    if ns.command == "demo":
        demo_run(m)
        return 0

    if ns.command == "add":
        meta = json.loads(ns.metadata) if ns.metadata else None
        r = m.add(
            " ".join(ns.args),
            metadata=meta,
            immutable=ns.immutable,
            infer=not ns.no_infer,
        )
        print(json.dumps(r, indent=2))
        return 0

    if ns.command == "search":
        r = m.search(" ".join(ns.args), top_k=ns.top_k)
        print(json.dumps(r, indent=2))
        return 0

    if ns.command == "get-all":
        print(json.dumps(m.get_all(limit=ns.top_k), indent=2))
        return 0

    if ns.command == "get" and ns.args:
        print(json.dumps(m.get(ns.args[0]), indent=2))
        return 0

    if ns.command == "history" and ns.args:
        print(json.dumps(m.history(ns.args[0]), indent=2))
        return 0

    if ns.command == "update" and len(ns.args) >= 2:
        print(json.dumps(m.update(ns.args[0], " ".join(ns.args[1:])), indent=2))
        return 0

    if ns.command == "delete" and ns.args:
        print(json.dumps(m.delete(ns.args[0]), indent=2))
        return 0

    if ns.command == "batch-delete" and ns.args:
        print(json.dumps(m.batch_delete(ns.args), indent=2))
        return 0

    if ns.command == "export":
        print(json.dumps(m.create_export(), indent=2))
        return 0

    ap.print_help()
    return 1


def demo_run(m: Mem0Master) -> None:
    """End-to-end demo: add → search → export probe."""
    stamp = datetime.now(timezone.utc).isoformat()
    print(f"=== Mem0 Master Demo ({m.account}) ===")
    print("Health:", json.dumps(m.health()))
    add_resp = m.add(
        f"APEX mem0 master demo ping at {stamp}",
        metadata={"source": "mem0_master_apex", "demo": True},
        infer=True,
    )
    print("Add:", json.dumps(add_resp)[:500])
    search_resp = m.search("APEX mem0 master", top_k=3)
    print("Search:", json.dumps(search_resp)[:800])
    print("Done.")


if __name__ == "__main__":
    raise SystemExit(cli())