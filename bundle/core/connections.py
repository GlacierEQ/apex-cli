#!/usr/bin/env python3
# SPDX-License-Identifier: GlacierEQ-Proprietary-Open-Architecture
# Copyright (c) 2026 Casey del Carpio Barton / GlacierEQ
"""
connections.py — Connection Manager
====================================
Loads SaaS connection IDs from ~/.apex/connections.json (or env vars).
Never hardcodes credentials in source code.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("connections")

CONFIG_PATH = Path(os.path.expanduser("~/.apex/connections.json"))


class ConnectionManager:
    """
    Manages SaaS connection IDs and credentials.
    Priority: env vars > ~/.apex/connections.json > defaults.
    """

    # Env var names for each service
    ENV_MAP = {
        "github": "APEX_GITHUB_CONN",
        "google_drive": "APEX_GDRIVE_CONN",
        "dropbox": "APEX_DROPBOX_CONN",
        "onedrive": "APEX_ONEDRIVE_CONN",
        "notion": "APEX_NOTION_CONN",
        "gmail": "APEX_GMAIL_CONN",
        "neo4j_aura": "APEX_NEO4J_AURA_CONN",
        "neo4j_direct": "APEX_NEO4J_DIRECT_CONN",
        "openai": "APEX_OPENAI_CONN",
        "pinecone": "APEX_PINECONE_CONN",
        "sharepoint": "APEX_SHAREPOINT_CONN",
    }

    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load connections from config file."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    self._connections = json.load(f)
                log.info(f"✅ Loaded {len(self._connections)} connections from {CONFIG_PATH}")
            except Exception as e:
                log.error(f"❌ Failed to load connections: {e}")
        else:
            log.warning(f"⚠️ No connections file at {CONFIG_PATH}. Using env vars only.")

    def get(self, service: str) -> Optional[str]:
        """
        Get a connection ID for a service.
        Checks env var first, then config file.
        """
        # 1. Check env var
        env_var = self.ENV_MAP.get(service)
        if env_var:
            env_val = os.environ.get(env_var, "")
            if env_val:
                return env_val

        # 2. Check config file
        conn = self._connections.get(service, {})
        if isinstance(conn, dict):
            return conn.get("connection_id", "")
        return conn if isinstance(conn, str) else None

    def get_tools(self, service: str) -> list:
        """Get available tools for a service."""
        conn = self._connections.get(service, {})
        if isinstance(conn, dict):
            return conn.get("tools", [])
        return []

    def list_services(self) -> list:
        """List all configured services."""
        return list(self._connections.keys())

    def health_report(self) -> Dict[str, bool]:
        """Check which services have connection IDs configured."""
        report = {}
        for service in self.ENV_MAP:
            conn_id = self.get(service)
            report[service] = bool(conn_id)
        return report


# Singleton
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def get_connection(service: str) -> Optional[str]:
    """Convenience: get a connection ID."""
    return get_manager().get(service)


if __name__ == "__main__":
    mgr = ConnectionManager()
    report = mgr.health_report()
    print("\n🔌 CONNECTION HEALTH REPORT")
    print("=" * 40)
    for service, ok in report.items():
        print(f"  {'✅' if ok else '❌'} {service}")
    configured = sum(1 for v in report.values() if v)
    print(f"\n  {configured}/{len(report)} services configured")
