#!/usr/bin/env python3
"""
OPERATOR-LINKED KEY VAULT (safe)

Loads credentials from environment / ~/.operator_key_vault/gatekeeper.env only.
NEVER hardcodes secrets. NEVER prints secret values.

Operator GUID (non-secret): 983DE8C8-E120-1-B5A0-C6D8AF97BB09
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("HOME", str(Path.home())))
VAULT_DIR = HOME / ".operator_key_vault"
GATEKEEPER_ENV = VAULT_DIR / "gatekeeper.env"
MANIFEST = VAULT_DIR / "key_manifest.json"
CREDENTIALS_DIR = VAULT_DIR / "credentials"

OPERATOR_GUID = "983DE8C8-E120-1-B5A0-C6D8AF97BB09"
OPERATOR_CODE = "OPR-NS8-GE8-KC3-001-AI-GRS"

# Logical service → env var candidates (first hit wins)
SERVICE_ENV_MAP: dict[str, list[str]] = {
    "mem0": ["MEM0_API_KEY", "MEM0_PRO_API_KEY"],
    "mem0_org": ["MEM0_ORG_ID"],
    "supermemory": ["SUPERMEMORY_API_KEY", "SUPERMEMORY_CODEX_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY", "OPENROUTER_TOKEN"],
    "together": ["TOGETHER_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "linear": ["LINEAR_API_KEY"],
    "notion": ["NOTION_API_KEY", "NOTION_TOKEN"],
    "slack": ["SLACK_BOT_TOKEN", "SLACK_XAPP_TOKEN"],
    "github": ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"],
    "gitlab": ["GITLAB_TOKEN", "GITLAB_PAT"],
    "vercel": ["VERCEL_TOKEN"],
    "render": ["RENDER_API_KEY"],
    "railway": ["RAILWAY_API_KEY", "RAILWAY_TOKEN"],
    "supabase": ["SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_ACCESS_TOKEN"],
    "pinecone": ["PINECONE_API_KEY"],
    "neo4j": ["NEO4J_PASSWORD", "NEO4J_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "taskade": ["TASKADE_API_KEY"],
    "todoist": ["TODOIST_API_TOKEN"],
    "asana": ["ASANA_ACCESS_TOKEN"],
    "jira": ["JIRA_API_TOKEN"],
    "cursor": ["CURSOR_API_KEY"],
    "smithery": ["SMITHERY_API_KEY"],
    "dropbox": ["DROPBOX_ACCESS_TOKEN", "DROPBOX_REFRESH_TOKEN"],
}


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}…{value[-4:]} (len={len(value)})"


def load_gatekeeper_env(path: Path | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines into a dict (does not print values)."""
    path = path or GATEKEEPER_ENV
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k) and v:
            out[k] = v
            # also inject into process env if missing
            os.environ.setdefault(k, v)
    return out


class OperatorKeyVault:
    """
    Secure key access for operators.

    Usage:
        vault = OperatorKeyVault()
        token = vault.get("github")          # raw secret for local use only
        vault.status()                       # names + presence, never values
    """

    def __init__(self, env_path: Path | None = None):
        self.operator_guid = OPERATOR_GUID
        self.operator_code = OPERATOR_CODE
        self.env_path = env_path or GATEKEEPER_ENV
        self._env = load_gatekeeper_env(self.env_path)
        # merge current process env (higher priority for already-exported)
        for k, v in os.environ.items():
            if k.isupper() and v and k not in self._env:
                self._env[k] = v

    def get(self, service: str, *, default: str | None = None) -> str | None:
        """Return first available secret for a logical service name."""
        key = service.strip().lower()
        for env_var in SERVICE_ENV_MAP.get(key, []):
            val = self._env.get(env_var) or os.environ.get(env_var)
            if val:
                return val
        # direct env var if user passes OPENAI_API_KEY style
        upper = service.strip().upper()
        return self._env.get(upper) or os.environ.get(upper) or default

    def get_env(self, env_var: str, *, default: str | None = None) -> str | None:
        return self._env.get(env_var) or os.environ.get(env_var) or default

    def require(self, service: str) -> str:
        val = self.get(service)
        if not val:
            raise KeyError(f"Missing credential for service={service!r} (check gatekeeper.env)")
        return val

    def has(self, service: str) -> bool:
        return bool(self.get(service))

    def status(self) -> dict[str, Any]:
        """Non-secret inventory for steward / health checks."""
        services = []
        for name, vars_ in sorted(SERVICE_ENV_MAP.items()):
            present = self.has(name)
            which = None
            if present:
                for v in vars_:
                    if self._env.get(v) or os.environ.get(v):
                        which = v
                        break
            services.append({"service": name, "loaded": present, "env_var": which})
        loaded = sum(1 for s in services if s["loaded"])
        return {
            "operator_guid": self.operator_guid,
            "operator_code": self.operator_code,
            "gatekeeper": str(self.env_path),
            "gatekeeper_exists": self.env_path.is_file(),
            "services_known": len(services),
            "services_loaded": loaded,
            "services": services,
            "note": "Values never included. Ingest secrets via gatekeeper.env only.",
        }

    def export_manifest(self) -> Path:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        st = self.status()
        payload = {
            "at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "total_keys": st["services_loaded"],
            "vault_path": str(self.env_path),
            "operator_guid": self.operator_guid,
            "services": [
                {
                    "env_var": s["env_var"] or s["service"].upper(),
                    "service": s["service"],
                    "loaded": s["loaded"],
                    "source": "gatekeeper.env" if s["loaded"] else None,
                }
                for s in st["services"]
            ],
            "note": "Safe vault — no secret material in this file.",
        }
        MANIFEST.write_text(json.dumps(payload, indent=2) + "\n")
        try:
            os.chmod(MANIFEST, 0o600)
        except OSError:
            pass
        return MANIFEST


def ensure_gatekeeper_template() -> Path:
    """Create chmod-600 template if missing (empty placeholders only)."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    if not GATEKEEPER_ENV.is_file():
        lines = [
            "# Operator gatekeeper.env — NEVER commit this file",
            f"# {OPERATOR_CODE} GUID={OPERATOR_GUID}",
            "# Format: KEY=value  (one per line)",
            "",
            "# GITHUB_TOKEN=",
            "# OPENAI_API_KEY=",
            "# ANTHROPIC_API_KEY=",
            "# MEM0_API_KEY=",
            "# SUPERMEMORY_API_KEY=",
            "# PERPLEXITY_API_KEY=",
            "# NOTION_API_KEY=",
            "# LINEAR_API_KEY=",
            "# GEMINI_API_KEY=",
            "",
        ]
        GATEKEEPER_ENV.write_text("\n".join(lines))
        os.chmod(GATEKEEPER_ENV, 0o600)
    return GATEKEEPER_ENV


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Operator key vault (safe status only)")
    ap.add_argument("--status", action="store_true", help="Print service load status")
    ap.add_argument("--template", action="store_true", help="Ensure gatekeeper.env template")
    ap.add_argument("--manifest", action="store_true", help="Write key_manifest.json")
    ap.add_argument(
        "--has",
        metavar="SERVICE",
        help="Exit 0 if service credential present (no value printed)",
    )
    args = ap.parse_args()

    if args.template:
        p = ensure_gatekeeper_template()
        print(f"template: {p} mode={oct(p.stat().st_mode & 0o777)}")

    vault = OperatorKeyVault()
    if args.has:
        ok = vault.has(args.has)
        print(json.dumps({"service": args.has, "loaded": ok}))
        return 0 if ok else 1
    if args.manifest:
        path = vault.export_manifest()
        print(f"manifest: {path}")
    if args.status or not any([args.template, args.manifest, args.has]):
        print(json.dumps(vault.status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
