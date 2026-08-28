#!/usr/bin/env python3
"""Read-only diagnostics for optional memory-provider connections.

No credential is embedded in this repository. Each remote provider check requires
its credential/endpoint through the environment and performs only read-only
requests. Missing configuration is reported as unavailable rather than replaced
with a fallback secret.
"""

from __future__ import annotations

import asyncio
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from dotenv import load_dotenv

try:
    from neo4j import AsyncGraphDatabase
except ImportError:
    AsyncGraphDatabase = None

load_dotenv(Path.home() / ".env", override=False)


def print_header(message: str) -> None:
    print(f"\n=== {message} ===")


def _configured(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


async def verify_mem0() -> bool:
    print_header("Mem0 Cloud Memory Verification")
    mem_key = _configured("MEM0_API_KEY", "MEM_API_KEY")
    if not mem_key:
        print(
            "⚠️ Mem0 verification skipped: MEM0_API_KEY/MEM_API_KEY is not configured."
        )
        return False

    url = "https://api.mem0.ai/v1/memories/?user_id=test_verification"
    headers = {"Authorization": f"Token {mem_key}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    print("✅ Mem0 read-only API check succeeded.")
                    return True
                print(f"❌ Mem0 read-only API check returned HTTP {response.status}.")
                return False
    except Exception as exc:
        print(f"❌ Mem0 read-only API check failed: {exc}")
        return False


async def verify_neo4j() -> bool:
    print_header("Neo4j Graph Database Verification")
    uri = _configured("NEO4J_URI")
    neo4j_user = _configured("NEO4J_USER")
    neo4j_credential = _configured("NEO4J_PASSWORD")
    if not uri or not neo4j_user or not neo4j_credential:
        print(
            "⚠️ Neo4j verification skipped: URI/user/credential is not fully configured."
        )
        return False
    if AsyncGraphDatabase is None:
        print("⚠️ Neo4j verification skipped: neo4j Python package is unavailable.")
        return False

    parsed = urlparse(uri)
    host = parsed.hostname
    port = parsed.port or 7687
    if not host:
        print("❌ Neo4j URI has no hostname.")
        return False

    try:
        with socket.socket() as sock:
            sock.settimeout(1.5)
            if sock.connect_ex((host, port)) != 0:
                print(f"⚠️ Neo4j endpoint is unavailable at {host}:{port}.")
                return False

        async with AsyncGraphDatabase.driver(
            uri, auth=(neo4j_user, neo4j_credential)
        ) as driver:
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                passed = bool(record and record["ok"] == 1)
                print(
                    "✅ Neo4j read-only query succeeded."
                    if passed
                    else "❌ Neo4j read-only query failed."
                )
                return passed
    except Exception as exc:
        print(f"❌ Neo4j read-only verification failed: {exc}")
        return False


async def verify_pinecone() -> bool:
    print_header("Pinecone Vector Database Verification")
    api_key = _configured("PINECONE_PRIMARY_KEY", "PINECONE_API_KEY")
    host = _configured("PINECONE_HOST")
    if not api_key or not host:
        print("⚠️ Pinecone verification skipped: API key/host is not configured.")
        return False

    url = f"https://{host}/describe_index_stats"
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={}) as response:
                if response.status == 200:
                    print("✅ Pinecone read-only index-stats check succeeded.")
                    return True
                print(
                    f"❌ Pinecone read-only index-stats check returned HTTP {response.status}."
                )
                return False
    except Exception as exc:
        print(f"❌ Pinecone read-only verification failed: {exc}")
        return False


async def verify_qdrant() -> bool:
    print_header("Qdrant Vector Database Verification")
    host = os.getenv("QDRANT_HOST") or "localhost"
    port = int(os.getenv("QDRANT_PORT") or "6333")
    collection = os.getenv("QDRANT_COLLECTION") or "apex_memory"
    api_key = _configured("QDRANT_KEY")

    try:
        with socket.socket() as sock:
            sock.settimeout(1.5)
            if sock.connect_ex((host, port)) != 0:
                print(f"⚠️ Qdrant endpoint is unavailable at {host}:{port}.")
                return False

        headers = {"api-key": api_key} if api_key else {}
        url = f"http://{host}:{port}/collections/{collection}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    print("✅ Qdrant read-only collection check succeeded.")
                    return True
                print(
                    f"❌ Qdrant read-only collection check returned HTTP {response.status}."
                )
                return False
    except Exception as exc:
        print(f"❌ Qdrant read-only verification failed: {exc}")
        return False


async def main() -> None:
    print("=" * 60)
    print("READ-ONLY MEMORY CONNECTION DIAGNOSTICS")
    print("=" * 60)
    results = await asyncio.gather(
        verify_mem0(), verify_pinecone(), verify_neo4j(), verify_qdrant()
    )
    labels = ("Mem0", "Pinecone", "Neo4j", "Qdrant")
    print("\n" + "=" * 60)
    for label, passed in zip(labels, results):
        print(
            f"{label:10}: {'AVAILABLE' if passed else 'UNAVAILABLE / NOT CONFIGURED'}"
        )
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
