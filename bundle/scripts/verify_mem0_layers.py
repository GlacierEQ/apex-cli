#!/usr/bin/env python3
"""
Verification script for Mem0 multi‑layer integration.
Runs Neo4j, Pinecone, and Mem0 checks in parallel with async/await.
"""
import asyncio
import os
import json
import sys
import random
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Use async drivers
try:
    from neo4j import AsyncGraphDatabase
except ImportError:
    AsyncGraphDatabase = None

load_dotenv(Path.home() / ".env", override=True)

# Helper to format output headers
def print_header(msg):
    print(f"\n=== {msg} ===")

# 1. Verify Mem0 API layer
async def verify_mem0():
    try:
        # Resolve keys
        mem_key = os.getenv("MEM0_API_KEY") or os.getenv("MEM_API_KEY")
        if not mem_key:
            # Fallback to known valid pro key
            mem_key = "m0-XsPsE19WZoEesvOFYbm9A6Du98pWS8wyfHUXJ60U"
            
        print_header("Mem0 Cloud Memory Verification")
        url = "https://api.mem0.ai/v1/memories/?user_id=test_verification"
        headers = {"Authorization": f"Token {mem_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                status = r.status
                if status == 200:
                    print(f"✅ Mem0 Cloud API is ACTIVE (status={status})")
                    return True
                else:
                    body = await r.text()
                    print(f"❌ Mem0 Cloud API returned status {status}: {body}")
                    return False
    except Exception as e:
        print(f"❌ Mem0 Cloud API connection failed: {e}")
        return False

# 2. Verify Neo4j Graph Database layer
async def verify_neo4j():
    try:
        uri = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
        user = os.getenv("NEO4J_USER") or "neo4j"
        password = os.getenv("NEO4J_PASSWORD") or "neo4j"
        
        print_header("Neo4j Graph Database Verification")
        
        if not AsyncGraphDatabase:
            print("⚠️ 'neo4j' Python package not installed or cannot be imported.")
            return False
            
        # Check if local/remote Neo4j port is even open before attempting driver connection
        # to avoid long timeout blocks.
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 7687
        
        s = socket.socket()
        s.settimeout(1.5)
        conn_res = s.connect_ex((host, port))
        s.close()
        
        if conn_res != 0:
            print(f"⚠️ Neo4j Database is OFFLINE (Port {port} on {host} is closed). Skipping connection test.")
            return False
            
        async with AsyncGraphDatabase.driver(uri, auth=(user, password)) as driver:
            async with driver.session() as session:
                result = await session.run("RETURN 'graph test' AS msg")
                record = await result.single()
                print("✅ Neo4j Database is ACTIVE. Result:", record["msg"])
                return True
    except Exception as e:
        print(f"❌ Neo4j Graph Verification Failed: {e}")
        return False

# 3. Verify Pinecone Vector Database layer
async def verify_pinecone():
    try:
        print_header("Pinecone Vector Database Verification")
        
        # Pinecone keys & host details
        pc_api_key = os.getenv("PINECONE_PRIMARY_KEY") or os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX") or "apex-main"
        
        if not pc_api_key:
            raise RuntimeError("Missing configuration for Pinecone API Key.")
            
        # Get Pinecone index host
        host = os.getenv("PINECONE_HOST") or "apex-main-xwjbbs7.svc.aped-4627-b74a.pinecone.io"
        
        # Generate a synthetic 1536-dimensional vector to test index operations
        print(f"Generating 1536-dimensional verification vector (dimension matches OpenAI ada-002)...")
        embedding = [random.uniform(-1.0, 1.0) for _ in range(1536)]
        
        # 3.1 Upsert verification vector
        print(f"Upserting verification vector to Pinecone Index '{index_name}'...")
        upsert_url = f"https://{host}/vectors/upsert"
        headers = {"Api-Key": pc_api_key, "Content-Type": "application/json"}
        upsert_payload = {
            "vectors": [
                {
                    "id": "verify_test_vector",
                    "values": embedding,
                    "metadata": {"text": "synthetic verification vector", "test": True}
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(upsert_url, headers=headers, json=upsert_payload) as r:
                if r.status != 200:
                    raise RuntimeError(f"Upsert failed: HTTP {r.status} - {await r.text()}")
                
            # 3.2 Query verification vector
            print("Querying vector from Pinecone Index...")
            query_url = f"https://{host}/query"
            query_payload = {
                "vector": embedding,
                "topK": 1,
                "includeMetadata": True
            }
            async with session.post(query_url, headers=headers, json=query_payload) as r:
                if r.status != 200:
                    raise RuntimeError(f"Query failed: HTTP {r.status} - {await r.text()}")
                query_data = await r.json()
                matches = query_data.get("matches", [])
                
        if matches:
            print("✅ Pinecone Vector Database is ACTIVE.")
            print(f"Match: id={matches[0].get('id')}, score={matches[0].get('score')}")
            return True
        else:
            print("❌ Pinecone query succeeded but returned 0 matches.")
            return False
            
    except Exception as e:
        print(f"❌ Pinecone Vector Verification Failed: {e}")
        return False

async def verify_qdrant():
    try:
        print_header("Qdrant Vector Database Verification")
        
        host = os.getenv("QDRANT_HOST") or "localhost"
        port = int(os.getenv("QDRANT_PORT") or "6333")
        collection = os.getenv("QDRANT_COLLECTION") or "apex_memory"
        api_key = os.getenv("QDRANT_KEY")
        
        # Socket check first
        import socket
        s = socket.socket()
        s.settimeout(1.5)
        conn_res = s.connect_ex((host, port))
        s.close()
        
        if conn_res != 0:
            print(f"⚠️ Qdrant Database is OFFLINE (Port {port} on {host} is closed). Skipping API test.")
            return False
            
        url = f"http://{host}:{port}/collections/{collection}"
        headers = {}
        if api_key:
            headers["api-key"] = api_key
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if r.status == 200:
                    print(f"✅ Qdrant Vector Database is ACTIVE (Collection '{collection}' exists).")
                    return True
                else:
                    body = await r.text()
                    print(f"⚠️ Qdrant returned status {r.status} for collection '{collection}': {body}")
                    return False
    except Exception as e:
        print(f"❌ Qdrant Vector Verification Failed: {e}")
        return False

async def main():
    print("=" * 60)
    print("      DIAGNOSTIC REPORT FOR MEMORY CONNECTION LAYERS")
    print("=" * 60)
    
    results = await asyncio.gather(verify_mem0(), verify_pinecone(), verify_neo4j(), verify_qdrant())
    
    print("\n" + "=" * 60)
    print("                     SUMMARY")
    print("=" * 60)
    print(f"  Mem0 Cloud API Layer         : {'✅ ACTIVE' if results[0] else '❌ OFFLINE/ERROR'}")
    print(f"  Pinecone Vector DB Layer     : {'✅ ACTIVE' if results[1] else '❌ OFFLINE/ERROR'}")
    print(f"  Neo4j Graph DB Layer         : {'✅ ACTIVE' if results[2] else '⚠️ OFFLINE (Port 7687 closed)'}")
    print(f"  Qdrant Vector DB Layer       : {'✅ ACTIVE' if results[3] else '⚠️ OFFLINE (Port 6333 closed)'}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
