#!/usr/bin/env python3
"""
OPERATOR-LINKED KEY VAULT
OPR-NS8-GE8-KC3-001-AI-GRS-GUID:983DE8C8-E120-1-B5A0-C6D8AF97BB09

Loads secrets from ~/.operator_key_vault/gatekeeper.env (mode 600).
API surface matches classic OperatorKeyVault getters; values never printed by --status.
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

OPERATOR_GUID = "983DE8C8-E120-1-B5A0-C6D8AF97BB09"
OPERATOR_CODE = "OPR-NS8-GE8-KC3-001-AI-GRS"

SERVICE_ENV_MAP: dict[str, list[str]] = {
    "mem0": ["MEM0_API_KEY", "MEM0_PRO_API_KEY"],
    "mem0_org": ["MEM0_ORG_ID"],
    "supermemory": ["SUPERMEMORY_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "together": ["TOGETHER_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "linear": ["LINEAR_API_KEY"],
    "notion": ["NOTION_API_KEY"],
    "slack": ["SLACK_BOT_TOKEN", "SLACK_XAPP_TOKEN"],
    "github": ["GITHUB_TOKEN", "GH_TOKEN"],
    "gitlab": ["GITLAB_TOKEN"],
    "vercel": ["VERCEL_TOKEN"],
    "render": ["RENDER_API_KEY"],
    "railway": ["RAILWAY_API_KEY"],
    "supabase": ["SUPABASE_ANON_KEY", "SUPABASE_ACCESS_TOKEN"],
    "pinecone": ["PINECONE_API_KEY"],
    "neo4j": ["NEO4J_API_KEY", "NEO4J_PASSWORD"],
    "xai": ["XAI_API_KEY"],
    "taskade": ["TASKADE_API_KEY"],
    "todoist": ["TODOIST_API_TOKEN"],
    "asana": ["ASANA_ACCESS_TOKEN"],
    "jira": ["JIRA_API_TOKEN"],
    "cursor": ["CURSOR_API_KEY"],
    "cody": ["CODY_API_KEY"],
    "warp": ["WARP_API_KEY"],
    "minimax": ["MINIMAX_JWT"],
    "nebius": ["NEBIUS_JWT"],
    "firebase": ["FIREBASE_API_KEY"],
    "prisma": ["PRISMA_POSTGRES_URL"],
}


def load_gatekeeper_env(path: Path | None = None) -> dict[str, str]:
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
            os.environ.setdefault(k, v)
    return out


def _any_val(o: Any) -> bool:
    if isinstance(o, dict):
        return any(_any_val(x) for x in o.values())
    if isinstance(o, list):
        return any(_any_val(x) for x in o)
    return bool(o)


class OperatorKeyVault:
    def __init__(self, session_key: str | None = None, env_path: Path | None = None):
        self.env_path = env_path or GATEKEEPER_ENV
        self._env = load_gatekeeper_env(self.env_path)
        self.session_key = session_key or self._env.get("APEX_SESSION_KEY") or ""
        self.operator_guid = self._env.get("OPERATOR_GUID") or OPERATOR_GUID
        self.operator_code = self._env.get("OPERATOR_CODE") or OPERATOR_CODE

    def _g(self, *names: str, default: str = "") -> str:
        for n in names:
            v = self._env.get(n) or os.environ.get(n)
            if v:
                return v
        return default

    def get(self, service: str, *, default: str | None = None) -> str | None:
        key = service.strip().lower()
        for env_var in SERVICE_ENV_MAP.get(key, []):
            val = self._g(env_var)
            if val:
                return val
        return self._g(service.strip().upper()) or default

    def require(self, service: str) -> str:
        val = self.get(service)
        if not val:
            raise KeyError(f"Missing credential for {service!r}")
        return val

    def has(self, service: str) -> bool:
        return bool(self.get(service))

    def export_to_environ(self) -> int:
        n = 0
        for k, v in self._env.items():
            os.environ[k] = v
            n += 1
        return n

    def get_mem0_keys(self) -> dict[str, Any]:
        return {
            "pro_account": {
                "api_key": self._g("MEM0_PRO_API_KEY", "MEM0_API_KEY"),
                "email": self._g("MEM0_PRO_EMAIL"),
                "org_id": self._g("MEM0_ORG_ID"),
                "org_name": self._g("MEM0_ORG_NAME"),
            },
            "regular_account": {
                "api_key": self._g("MEM0_REG_API_KEY"),
                "email": self._g("MEM0_REG_EMAIL"),
            },
            "additional_keys": [
                k
                for k in (
                    self._g("MEM0_API_KEY_ALT1"),
                    self._g("MEM0_API_KEY_ALT2"),
                    self._g("MEM0_API_KEY_ALT3"),
                )
                if k
            ],
        }

    def get_supermemory_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("SUPERMEMORY_API_KEY"),
            "secondary": self._g("SUPERMEMORY_API_KEY_SECONDARY"),
            "tertiary": self._g("SUPERMEMORY_API_KEY_TERTIARY"),
            "mcp_url": self._g("SUPERMEMORY_MCP_URL")
            or "https://api.supermemory.ai/mcp",
        }

    def get_memory_plugin_keys(self) -> dict[str, str]:
        return {
            "context_global": self._g("MEMORY_AUTH_TOKEN"),
            "direct_relevance": self._g("MEMORY_PLUGIN_TOKEN"),
        }

    def get_openai_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("OPENAI_API_KEY"),
            "windsurf": self._g("OPENAI_API_KEY_WINDSURF"),
            "admin": self._g("OPENAI_ADMIN_KEY"),
            "admin_legacy": self._g("OPENAI_ADMIN_KEY_LEGACY"),
        }

    def get_anthropic_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("ANTHROPIC_API_KEY"),
            "code_assistant": self._g("ANTHROPIC_API_KEY_CODE"),
        }

    def get_gemini_keys(self) -> dict[str, str]:
        return {
            "api_key": self._g("GEMINI_API_KEY"),
            "google_api": self._g("GOOGLE_API_KEY"),
            "code_assist_project": self._g("GOOGLE_OAUTH_PROJECT_ID"),
            "client_id": self._g("GOOGLE_OAUTH_CLIENT_ID"),
            "client_secret": self._g("GOOGLE_OAUTH_CLIENT_SECRET"),
        }

    def get_groq_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("GROQ_API_KEY"),
            "secondary": self._g("GROQ_API_KEY_SECONDARY"),
        }

    def get_deepseek_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("DEEPSEEK_API_KEY"),
            "secondary": self._g("DEEPSEEK_API_KEY_SECONDARY"),
            "tertiary": self._g("DEEPSEEK_API_KEY_TERTIARY"),
            "base_url": self._g("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        }

    def get_perplexity_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("PERPLEXITY_API_KEY"),
            "secondary": self._g("PERPLEXITY_API_KEY_SECONDARY"),
        }

    def get_minimax_keys(self) -> dict[str, str]:
        return {"jwt_token": self._g("MINIMAX_JWT")}

    def get_openrouter_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("OPENROUTER_API_KEY"),
            "secondary": self._g("OPENROUTER_API_KEY_SECONDARY"),
            "tertiary": self._g("OPENROUTER_API_KEY_TERTIARY"),
            "management": self._g("OPENROUTER_API_KEY_MGMT"),
            "agentic_browser": self._g("OPENROUTER_API_KEY_BROWSER"),
        }

    def get_together_ai_keys(self) -> dict[str, str]:
        return {"primary": self._g("TOGETHER_API_KEY")}

    def get_cohere_keys(self) -> dict[str, str]:
        return {"primary": self._g("COHERE_API_KEY")}

    def get_nebius_keys(self) -> dict[str, str]:
        return {"jwt": self._g("NEBIUS_JWT")}

    def get_linear_keys(self) -> dict[str, str]:
        return {"api_key": self._g("LINEAR_API_KEY")}

    def get_slack_keys(self) -> dict[str, str]:
        return {
            "xapp_token": self._g("SLACK_XAPP_TOKEN"),
            "app_id": self._g("SLACK_APP_ID"),
            "client_id": self._g("SLACK_CLIENT_ID"),
            "client_secret": self._g("SLACK_CLIENT_SECRET"),
            "signing_secret": self._g("SLACK_SIGNING_SECRET"),
            "verification": self._g("SLACK_VERIFICATION"),
        }

    def get_notion_keys(self) -> dict[str, str]:
        return {
            "api_key": self._g("NOTION_API_KEY"),
            "workspace_id": self._g("NOTION_WORKSPACE_ID"),
            "chats_db": self._g("NOTION_CHATS_DB"),
            "platforms_db": self._g("NOTION_PLATFORMS_DB"),
        }

    def get_jira_keys(self) -> dict[str, str]:
        return {"api_token": self._g("JIRA_API_TOKEN"), "site": self._g("JIRA_SITE")}

    def get_asana_keys(self) -> dict[str, str]:
        return {"token": self._g("ASANA_ACCESS_TOKEN")}

    def get_todoist_keys(self) -> dict[str, str]:
        return {"api_token": self._g("TODOIST_API_TOKEN")}

    def get_taskade_keys(self) -> dict[str, str]:
        return {
            "api_key": self._g("TASKADE_API_KEY"),
            "clickup_client_id": self._g("CLICKUP_CLIENT_ID"),
            "clickup_secret": self._g("CLICKUP_CLIENT_SECRET"),
        }

    def get_github_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("GITHUB_TOKEN", "GH_TOKEN"),
            "pat1": self._g("GITHUB_TOKEN_PAT1"),
            "pat2": self._g("GITHUB_TOKEN_PAT2"),
            "pat3": self._g("GITHUB_TOKEN_PAT3"),
            "pat_beme": self._g("GITHUB_TOKEN_BEME"),
            "pat_s41z": self._g("GITHUB_TOKEN_S41Z"),
            "client_secret": self._g("GITHUB_CLIENT_SECRET"),
            "awesome_forensics": self._g("GITHUB_TOKEN_FORENSICS"),
        }

    def get_gitlab_keys(self) -> dict[str, str]:
        return {
            "pat": self._g("GITLAB_TOKEN"),
            "feed_token": self._g("GITLAB_FEED_TOKEN"),
        }

    def get_cursor_keys(self) -> dict[str, str]:
        return {"api_key": self._g("CURSOR_API_KEY")}

    def get_cody_keys(self) -> dict[str, str]:
        return {"api_key": self._g("CODY_API_KEY")}

    def get_warp_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("WARP_API_KEY"),
            "secondary": self._g("WARP_API_KEY_SECONDARY"),
        }

    def get_vercel_keys(self) -> dict[str, str]:
        return {"token": self._g("VERCEL_TOKEN")}

    def get_render_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("RENDER_API_KEY"),
            "secondary": self._g("RENDER_API_KEY_SECONDARY"),
        }

    def get_railway_keys(self) -> dict[str, str]:
        return {"api_key": self._g("RAILWAY_API_KEY")}

    def get_supabase_keys(self) -> dict[str, str]:
        return {
            "anon_key": self._g("SUPABASE_ANON_KEY"),
            "glaciereq_key": self._g("SUPABASE_ACCESS_TOKEN"),
        }

    def get_prisma_keys(self) -> dict[str, str]:
        return {"postgres_url": self._g("PRISMA_POSTGRES_URL")}

    def get_pinecone_keys(self) -> dict[str, str]:
        return {
            "primary": self._g("PINECONE_API_KEY"),
            "higuy_key": self._g("PINECONE_API_KEY_HIGUY"),
        }

    def get_neo4j_keys(self) -> dict[str, str]:
        return {"api_key": self._g("NEO4J_API_KEY")}

    def get_firebase_keys(self) -> dict[str, str]:
        return {"api_key": self._g("FIREBASE_API_KEY")}

    def status(self) -> dict[str, Any]:
        services = []
        for name in sorted(SERVICE_ENV_MAP):
            present = self.has(name)
            which = None
            if present:
                for v in SERVICE_ENV_MAP[name]:
                    if self._g(v):
                        which = v
                        break
            services.append({"service": name, "loaded": present, "env_var": which})

        getter_map = {
            "mem0": "get_mem0_keys",
            "supermemory": "get_supermemory_keys",
            "openai": "get_openai_keys",
            "anthropic": "get_anthropic_keys",
            "gemini": "get_gemini_keys",
            "groq": "get_groq_keys",
            "deepseek": "get_deepseek_keys",
            "perplexity": "get_perplexity_keys",
            "openrouter": "get_openrouter_keys",
            "github": "get_github_keys",
            "notion": "get_notion_keys",
            "linear": "get_linear_keys",
            "vercel": "get_vercel_keys",
            "render": "get_render_keys",
            "supabase": "get_supabase_keys",
            "pinecone": "get_pinecone_keys",
            "slack": "get_slack_keys",
            "gitlab": "get_gitlab_keys",
        }
        getter_ok = {k: _any_val(getattr(self, m)()) for k, m in getter_map.items()}

        return {
            "operator_guid": self.operator_guid,
            "operator_code": self.operator_code,
            "gatekeeper": str(self.env_path),
            "gatekeeper_exists": self.env_path.is_file(),
            "env_key_count": len(self._env),
            "services_known": len(services),
            "services_loaded": sum(1 for s in services if s["loaded"]),
            "services": services,
            "getters_loaded": getter_ok,
            "note": "Secrets only in gatekeeper.env (600). Never committed to git.",
        }

    def export_manifest(self) -> Path:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        st = self.status()
        payload = {
            "at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
            "total_keys": st["env_key_count"],
            "services_loaded": st["services_loaded"],
            "vault_path": str(self.env_path),
            "operator_guid": self.operator_guid,
            "services": st["services"],
            "getters_loaded": st["getters_loaded"],
            "note": "Safe manifest — no secret material.",
        }
        MANIFEST.write_text(json.dumps(payload, indent=2) + "\n")
        try:
            os.chmod(MANIFEST, 0o600)
        except OSError:
            pass
        return MANIFEST


def main() -> int:
    import argparse
    import urllib.request

    ap = argparse.ArgumentParser(description="Operator key vault")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--has", metavar="SERVICE")
    ap.add_argument("--check-github", action="store_true")
    ap.add_argument(
        "--try-tokens", action="store_true", help="Try GITHUB_TOKEN* until one works"
    )
    args = ap.parse_args()

    vault = OperatorKeyVault()

    if args.has:
        print(json.dumps({"service": args.has, "loaded": vault.has(args.has)}))
        return 0 if vault.has(args.has) else 1

    if args.manifest:
        print(f"manifest: {vault.export_manifest()}")

    if args.check_github or args.try_tokens:
        candidates = []
        for k in (
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_TOKEN_PAT1",
            "GITHUB_TOKEN_PAT2",
            "GITHUB_TOKEN_PAT3",
            "GITHUB_TOKEN_BEME",
            "GITHUB_TOKEN_S41Z",
            "GITHUB_TOKEN_FORENSICS",
        ):
            v = vault._g(k)
            if v and v not in candidates:
                candidates.append(v)
        last_err = "no_token"
        for i, tok in enumerate(candidates):
            req = urllib.request.Request(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {tok}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "apex-operator-vault",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                # promote working token
                vault._env["GITHUB_TOKEN"] = tok
                os.environ["GITHUB_TOKEN"] = tok
                print(
                    json.dumps(
                        {
                            "github": True,
                            "login": data.get("login"),
                            "id": data.get("id"),
                            "token_index": i,
                        }
                    )
                )
                return 0
            except Exception as e:
                last_err = type(e).__name__
                continue
        print(
            json.dumps({"github": False, "reason": last_err, "tried": len(candidates)})
        )
        return 1

    print(json.dumps(vault.status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
