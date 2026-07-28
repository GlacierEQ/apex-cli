#!/usr/bin/env python3
# SPDX-License-Identifier: GlacierEQ-Proprietary-Open-Architecture
# Copyright (c) 2026 Casey del Carpio Barton / GlacierEQ
"""
benchmark_pipeline.py — APEX Cognitive Pipeline Matrix Benchmark
================================================================
Performs parallel load tests across multiplexed routes and records the latency 
metrics directly into your Neon Postgres 1009 database.
"""

import time
import asyncio
import aiohttp
import json
import os
import psycopg2
from datetime import datetime, timezone

# Load configurations
NEON_CONN_STRING = os.environ.get("APEX_NEO4J_DIRECT_CONN") or "postgresql://glaciereq-owner@c-6.us-east-1.aws.neon.tech/1009?sslmode=require"
BRIDGE_URL = os.environ.get("APEX_BRIDGE_URL", "http://localhost:8080")
TEST_CONNECTORS = ["notion", "postgres", "e2b"]

async def test_route_latency(session, connector: str) -> float:
    payload = {
        "connector": connector,
        "payload": {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 999
        }
    }
    start = time.perf_counter()
    try:
        async with session.post(f"{BRIDGE_URL}/", json=payload, timeout=5) as response:
            await response.read()
            if response.status == 200:
                return (time.perf_counter() - start) * 1000  # Return in ms
    except Exception as e:
        print(f"Error testing {connector}: {e}")
    return -1.0

async def run_load_test(concurrency: int = 10):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(concurrency):
            for conn in TEST_CONNECTORS:
                tasks.append(test_route_latency(session, conn))
        results = await asyncio.gather(*tasks)
        valid_results = [r for r in results if r > 0]
        
        avg_latency = sum(valid_results) / len(valid_results) if valid_results else 0.0
        p95_latency = sorted(valid_results)[int(len(valid_results) * 0.95)] if valid_results else 0.0
        
        return {
            "avg_ms": avg_latency,
            "p95_ms": p95_latency,
            "success_rate": len(valid_results) / len(results) * 100 if results else 0.0
        }

def log_metrics_to_neon(avg_ms: float, p95_ms: float, success_rate: float):
    """Write performance records directly to the 1009 database"""
    try:
        conn = psycopg2.connect(NEON_CONN_STRING)
        cur = conn.cursor()
        
        # Ensure benchmark table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apex_benchmarks (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                avg_latency_ms DOUBLE PRECISION,
                p95_latency_ms DOUBLE PRECISION,
                success_rate DOUBLE PRECISION,
                bridge_target VARCHAR(255)
            );
        """)
        
        cur.execute("""
            INSERT INTO apex_benchmarks (avg_latency_ms, p95_latency_ms, success_rate, bridge_target)
            VALUES (%s, %s, %s, %s);
        """, (avg_ms, p95_ms, success_rate, BRIDGE_URL))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"💾 Metrics written to Neon 1009: {avg_ms:.2f}ms avg / {p95_ms:.2f}ms p95")
    except Exception as e:
        print(f"❌ Failed to write to Neon Postgres: {e}")

if __name__ == "__main__":
    print("🚀 Starting APEX Cognitive Pipeline Multiplexer Benchmark...")
    metrics = asyncio.run(run_load_test(concurrency=15))
    print(f"Metrics: Average: {metrics['avg_ms']:.2f}ms | P95: {metrics['p95_ms']:.2f}ms | Success: {metrics['success_rate']:.1f}%")
    
    # Commit metrics directly to Neon
    log_metrics_to_neon(metrics['avg_ms'], metrics['p95_ms'], metrics['success_rate'])
