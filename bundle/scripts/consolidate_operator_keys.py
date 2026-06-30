#!/usr/bin/env python3
"""
Consolidate operator keys from all vault sources into gatekeeper.env.

Sources: .gemini_keys, .apex_vault/credentials.env, fs-commander .env,
         Google Keep exports, operator_code_key_audit (VALID), antigravity paths.

Never prints secret values — manifest lists service names + rotation status.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
VAULT_DIR = HOME / ".operator_key_vault"
OUT_ENV = VAULT_DIR / "gatekeeper.env"
MANIFEST = VAULT_DIR / "key_manifest.json"

SOURCES = [
    HOME / ".gemini_keys",
    HOME / ".apex_vault/credentials.env",
    HOME / "MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha/.env",
    HOME / ".env",
]

AG_CLI_EXTRACTED = HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/ag_cli_environment/ag_cli_extracted.env"
MASTER_ENV = HOME / ".apex_vault/AGENTS/MASTER.env"
SHARED_KEYS = HOME / ".apex_vault/AGENTS/SHARED_KEYS.env"

# Environment 4 — canonical sovereign vault (SD card / Download)
ENV4_CANDIDATES = [
    Path("/storage/emulated/0/Download/Environment4_Organized_Vault.md.txt"),
    Path("/storage/emulated/0/Documents/environment4"),
    Path("/sdcard/Download/Environment4_Organized_Vault.md.txt"),
    Path("/sdcard/Documents/environment4"),
    HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/environment4/Environment4_Organized_Vault.md.txt",
]

KEEP_REGISTRY = HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep"

KEEP_PATHS = [
    HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep_export/goohlekeep2026.txt",
    HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep_export/Google_Keep_Document.txt",
    HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/keep_export/Google_Keep_Document_1.txt",
]

AUDIT_JSON = HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/operator_code_key_audit_final.json"

# Map discovered prefixes / aliases → canonical env var
ALIASES = {
    "NOTION_TOKEN": "NOTION_API_KEY",
    "GITHUB_PAT": "GITHUB_TOKEN",
    "GITHUB_TOKEN_PRIMARY": "GITHUB_TOKEN",
    "GITHUB_TOKEN_ALT": "GITHUB_TOKEN",
    "GITHUB_PERSONAL_ACCESS_TOKEN": "GITHUB_TOKEN",
    "MEM0_PRO_API_KEY": "MEM0_API_KEY",
    "MEM0_REG_API_KEY": "MEM0_API_KEY",
    "MEMORY_PLUGIN_TOKEN": "MEMORY_AUTH_TOKEN",
    "ASPEN_DIRECT": "MEMORY_AUTH_TOKEN",
    "ASPEN_GLOBAL": "MEMORY_AUTH_TOKEN",
    "COLOSSUS_KEY": "COLOSSUS_API_KEY",
    "PINECONE_PRIMARY_KEY": "PINECONE_API_KEY",
    "OPENAI_WINDSURF_KEY": "OPENAI_API_KEY",
    "mem0glaciereq": "MEM0_API_KEY",
}

# Canonical env vars we actually wire into the mesh
CANONICAL_VARS = frozenset({
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "NOTION_API_KEY",
    "MEM0_API_KEY", "SUPERMEMORY_API_KEY", "SUPERMEMORY_CODEX_API_KEY",
    "GROQ_API_KEY", "GEMINI_API_KEY", "PINECONE_API_KEY", "COLOSSUS_API_KEY",
    "COLOSSUS_MCP_URL", "COLOSSUS_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "SUPABASE_ACCESS_TOKEN", "QDRANT_URL", "QDRANT_API_KEY",
    "DEEPSEEK_API_KEY", "PERPLEXITY_API_KEY", "HUGGINGFACE_API_KEY",
    "COURTLISTENER_API_KEY", "ELEVENLABS_API_KEY", "MEMORY_AUTH_TOKEN",
    "MEMORY_PLUGIN_TOKEN", "SMITHERY_API_KEY", "E2B_API_KEY", "DROPBOX_KEY",
    "DROPBOX_SECRET", "DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN",
    "DROPBOX_ACCESS_TOKEN", "DROPBOX_TOKEN_PATH", "OPENROUTER_API_KEY",
    "OPENROUTER_TOKEN", "LINEAR_API_KEY", "VERCEL_TOKEN", "XAI_API_KEY",
    "NEO4J_URI", "NEO4J_PASSWORD", "NEO4J_USERNAME", "MEM0_ORG_ID",
    "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "SHADE_API_KEY", "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT",
    "MIMO_API_KEY", "MIMO_GLASS_API_KEY", "PARSEHUB_API_KEY", "TASKADE_API_KEY",
    "HARPA_API_KEY", "ONEDRIVE_TOKEN_PATH", "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_PROJECT_ID", "GOOGLE_OAUTH_CLIENT_PATH",
    "GOOGLE_CASEY_OAUTH_CLIENT_ID", "GOOGLE_SERVICE_ACCOUNT_GLACIER_PATH",
    "GOOGLE_SERVICE_ACCOUNT_FIREBASE_PATH", "GOOGLE_SERVICE_ACCOUNT_CASEY_PATH",
    "DROPBOX_ACCESS_TOKEN", "ONEDRIVE_ACCESS_TOKEN", "ONEDRIVE_DRIVE_ID",
})

TOKEN_PATTERNS = [
    (re.compile(r"^(sk-proj-[a-zA-Z0-9_-]{20,})$"), "OPENAI_API_KEY"),
    (re.compile(r"^(sk-ant-api[0-9a-zA-Z_-]+)$"), "ANTHROPIC_API_KEY"),
    (re.compile(r"^(ghp_[a-zA-Z0-9]+)$"), "GITHUB_TOKEN"),
    (re.compile(r"^(github_pat_[a-zA-Z0-9_]+)$"), "GITHUB_TOKEN"),
    (re.compile(r"^(ntn_[a-zA-Z0-9]+)$"), "NOTION_API_KEY"),
    (re.compile(r"^(m0-[a-zA-Z0-9]+)$"), "MEM0_API_KEY"),
    (re.compile(r"^(sm_[a-zA-Z0-9_]{20,})$"), "SUPERMEMORY_API_KEY"),
    (re.compile(r"^(gsk_[a-zA-Z0-9]+)$"), "GROQ_API_KEY"),
    (re.compile(r"^(AIza[0-9A-Za-z_-]{30,})$"), "GEMINI_API_KEY"),
    (re.compile(r"^(pcsk_[a-zA-Z0-9]+)$"), "PINECONE_API_KEY"),
    (re.compile(r"^(dckr_pat_[a-zA-Z0-9_-]+)$"), "DOCKER_PAT"),
    (re.compile(r"^(pplx-[a-zA-Z0-9]+)$"), "PERPLEXITY_API_KEY"),
    (re.compile(r"^(sk_[a-f0-9]{40,})$"), "SHADE_API_KEY"),
    (re.compile(r"^(cfat_[A-Za-z0-9]+)$"), "CLOUDFLARE_API_TOKEN"),
    (re.compile(r"^(tskdp_[A-Za-z0-9]+)$"), "TASKADE_API_KEY"),
    (re.compile(r"^(hrp-[A-Za-z0-9_-]+)$"), "HARPA_API_KEY"),
    (re.compile(r"^(e2b_[a-f0-9]+)$"), "E2B_API_KEY"),
    (re.compile(r"^(sk-sup[a-z0-9]+)$"), "MIMO_API_KEY"),
    (re.compile(r"^(sbp_v0_[a-f0-9]+)$"), "SUPABASE_ACCESS_TOKEN"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _accept_key(key: str) -> bool:
    if key in CANONICAL_VARS or key in ALIASES:
        return True
    if key.endswith(("_PATH", "_ENDPOINT", "_ID")) and len(key) >= 8:
        return True
    return key.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_URL")) and len(key) >= 8


def parse_env_file(path: Path) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key or not val or val in ("", "PENDING_USER_PROVISION"):
            continue
        if not _accept_key(key):
            continue
        found[key] = (val, str(path))
    return found


SECTION_TO_VAR = {
    "github": "GITHUB_TOKEN",
    "notion": "NOTION_API_KEY",
    "supermemory": "SUPERMEMORY_API_KEY",
    "mem0": "MEM0_API_KEY",
    "memory plugin": "MEMORY_AUTH_TOKEN",
    "linear": "LINEAR_API_KEY",
    "vercel": "VERCEL_TOKEN",
    "smithery": "SMITHERY_API_KEY",
    "qdrant": "QDRANT_API_KEY",
    "pinecone": "PINECONE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",
    "huggingface": "HUGGINGFACE_API_KEY",
    "supabase": "SUPABASE_SERVICE_KEY",
}


def resolve_env4_path() -> Path | None:
    for p in ENV4_CANDIDATES:
        if p.is_file():
            return p
    return None


def mirror_env4_to_vault(src: Path) -> Path:
    dest_dir = HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/environment4"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "Environment4_Organized_Vault.md.txt"
    if src.resolve() != dest.resolve():
        dest.write_text(src.read_text(encoding="utf-8", errors="ignore"))
    return dest


def parse_environment4_vault(path: Path) -> dict[str, tuple[str, str]]:
    """Parse Environment 4 organized vault — prefer tokens tagged Environment 4."""
    found: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return found
    section = ""
    env4_priority: dict[str, tuple[str, str]] = {}

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("### "):
            section = line[4:].lower().split("(")[0].strip()
            continue
        if not line.startswith("- "):
            # KEY=value inline (Neo4j etc.)
            if "=" in line and any(k in line.upper() for k in ("NEO4J_", "SUPABASE", "QDRANT")):
                for part in re.findall(r"([A-Z][A-Z0-9_]*)=([^\s,]+)", line):
                    k, v = part[0], part[1].strip('"')
                    if _accept_key(k):
                        found[k] = (v, f"{path}:env4_inline")
            continue

        body = line[2:].strip()
        label = ""
        if "(" in body and ")" in body:
            m = re.search(r"\(([^)]+)\)\s*$", body)
            if m:
                label = m.group(1).lower()
                body = body[: m.start()].strip()

        # Section header line like "MEMORY_PLUGIN_TOKEN LFv..."
        parts = body.split(None, 1)
        token = parts[-1] if parts else body
        if len(parts) == 2 and parts[0].isupper() and "_" in parts[0]:
            var = ALIASES.get(parts[0], parts[0])
            val = parts[1].strip()
            if _accept_key(var):
                entry = (val, f"{path}:env4_labeled")
                if "environment 4" in label:
                    env4_priority[var] = entry
                elif var not in found:
                    found[var] = entry
            continue

        # Bare token — map via prefix or section
        val = token.strip().strip('"')
        var = None
        for pat, vname in TOKEN_PATTERNS:
            if pat.match(val):
                var = vname
                break
        if not var:
            for key, vname in SECTION_TO_VAR.items():
                if key in section:
                    var = vname
                    break
        if not var:
            continue
        entry = (val, f"{path}:env4_{section or 'token'}")
        if "environment 4" in label:
            env4_priority[var] = entry
        elif var not in found:
            found[var] = entry

    # Environment 4 tagged keys win
    found.update(env4_priority)
    return found


def parse_keep_registry(path: Path) -> dict[str, tuple[str, str]]:
    """Extract keys from AI-processed keep registry (OperatorKeyVault Python dicts)."""
    found: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return found
    text = path.read_text(encoding="utf-8", errors="ignore")
    section = ""
    for line in text.splitlines():
        if "def get_" in line and "_keys" in line:
            section = line.split("get_")[1].split("_keys")[0]
            continue
        for m in re.finditer(r'"(api_key|primary|secondary|token|pat\d*|github_master|admin)":\s*"([^"]{12,})"', line):
            label, val = m.group(1), m.group(2)
            var = None
            sec = section.lower()
            if sec in ("openai",) or val.startswith("sk-proj"):
                var = "OPENAI_API_KEY"
            elif sec in ("anthropic",) or val.startswith("sk-ant"):
                var = "ANTHROPIC_API_KEY"
            elif sec in ("github",) or val.startswith(("ghp_", "github_pat_")):
                var = "GITHUB_TOKEN"
            elif sec in ("notion",) or val.startswith("ntn_"):
                var = "NOTION_API_KEY"
            elif sec in ("mem0",) or val.startswith("m0-"):
                var = "MEM0_API_KEY"
            elif sec in ("supermemory",) or val.startswith("sm_"):
                var = "SUPERMEMORY_API_KEY"
            elif sec in ("gemini",) or val.startswith("AIza"):
                var = "GEMINI_API_KEY"
            elif sec in ("groq",) or val.startswith("gsk_"):
                var = "GROQ_API_KEY"
            elif sec in ("pinecone",) or val.startswith("pcsk_"):
                var = "PINECONE_API_KEY"
            elif sec in ("deepseek",):
                var = "DEEPSEEK_API_KEY"
            elif sec in ("perplexity",) or val.startswith("pplx-"):
                var = "PERPLEXITY_API_KEY"
            elif sec in ("openrouter",) or val.startswith("sk-or-v1-"):
                var = "OPENROUTER_API_KEY"
            elif sec in ("xai",) or val.startswith("xai-"):
                var = "XAI_API_KEY"
            elif sec in ("supabase",) and label in ("service_role", "admin", "secret_key"):
                var = "SUPABASE_SERVICE_KEY"
            if var:
                found[var] = (val, f"{path}:keep_registry:{sec}")
    found.update(parse_keep_loose(path))
    return found


def parse_keep_loose(path: Path) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return found
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Label = value lines (e.g. "Github=ghp_...")
    for m in re.finditer(r"(?m)^([A-Za-z][A-Za-z0-9_ ./-]{0,40})=\s*([^\n]+)$", text):
        label, val = m.group(1).strip(), m.group(2).strip()
        if len(val) < 8:
            continue
        canon = label.upper().replace(" ", "_").replace(".", "_")
        if "GITHUB" in canon:
            canon = "GITHUB_TOKEN"
        elif "NOTION" in canon:
            canon = "NOTION_API_KEY"
        elif "MEM0" in canon or "MEM0GLACIEREQ" in canon.replace(" ", ""):
            canon = "MEM0_API_KEY"
        elif "OPENAI" in canon or val.startswith("sk-proj"):
            canon = "OPENAI_API_KEY"
        elif val.startswith("sm_"):
            canon = "SUPERMEMORY_API_KEY"
        elif val.startswith("ntn_"):
            canon = "NOTION_API_KEY"
        else:
            continue
        found[canon] = (val, f"{path}:keep_label")
    # Bare token lines (prefix-matched only)
    for line in text.splitlines():
        s = line.strip()
        for pat, var in TOKEN_PATTERNS:
            if pat.match(s):
                found[var] = (s, f"{path}:bare")
    return found


def parse_audit_valid(path: Path) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return found
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return found
    service_map = {
        "github": "GITHUB_TOKEN",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "notion": "NOTION_API_KEY",
        "groq": "GROQ_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "pinecone": "PINECONE_API_KEY",
        "mem0": "MEM0_API_KEY",
        "supermemory": "SUPERMEMORY_API_KEY",
    }
    for row in data:
        if row.get("status") != "VALID":
            continue
        svc = service_map.get(row.get("service", ""), row.get("service", "").upper() + "_API_KEY")
        key = row.get("key", "")
        if key:
            found[svc] = (key, row.get("source", "audit_valid"))
    return found


def enrich_from_credential_files(keys: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Derive scalar tokens from JSON credential paths when present."""
    out = dict(keys)
    dropbox_path = out.get("DROPBOX_TOKEN_PATH", ("", ""))[0]
    if dropbox_path and Path(dropbox_path).is_file():
        try:
            data = json.loads(Path(dropbox_path).read_text(encoding="utf-8"))
            tok = data.get("access_token", "")
            if tok:
                out["DROPBOX_ACCESS_TOKEN"] = (tok, f"{dropbox_path}:access_token")
        except (json.JSONDecodeError, OSError):
            pass
    onedrive_path = out.get("ONEDRIVE_TOKEN_PATH", ("", ""))[0]
    if onedrive_path and Path(onedrive_path).is_file():
        try:
            data = json.loads(Path(onedrive_path).read_text(encoding="utf-8"))
            tok = data.get("access_token", "")
            if tok:
                out["ONEDRIVE_ACCESS_TOKEN"] = (tok, f"{onedrive_path}:access_token")
            if data.get("drive_id"):
                out["ONEDRIVE_DRIVE_ID"] = (data["drive_id"], f"{onedrive_path}:drive_id")
        except (json.JSONDecodeError, OSError):
            pass
    return out


def canonicalize(keys: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for k, (v, src) in keys.items():
        ck = ALIASES.get(k, k)
        if not _accept_key(ck) and ck not in CANONICAL_VARS:
            continue
        if ck not in out:
            out[ck] = (v, src)
    return out


def merge_all() -> tuple[dict[str, tuple[str, str]], dict]:
    merged: dict[str, tuple[str, str]] = {}
    provenance: dict[str, str] = {}

    # Lowest → highest priority (later wins)
    layers: list[tuple[str, dict[str, tuple[str, str]]]] = []

    layers.append(("audit_valid", parse_audit_valid(AUDIT_JSON)))
    for p in KEEP_PATHS:
        layers.append((f"keep:{p.name}", parse_keep_loose(p)))
    for p in SOURCES:
        layers.append((p.name, parse_env_file(p)))

    env4_src = resolve_env4_path()
    if env4_src:
        mirrored = mirror_env4_to_vault(env4_src)
        layers.append(("environment4", parse_environment4_vault(mirrored)))

    # Antigravity/Gemini CLI environment (MASTER.env + latest conversation DB)
    for path, name in [(SHARED_KEYS, "shared_keys"), (MASTER_ENV, "master_env"), (AG_CLI_EXTRACTED, "ag_cli")]:
        layer = parse_env_file(path)
        if layer:
            layers.append((name, layer))

    # AI-processed keep registry (highest-fidelity Keep distill)
    keep_layer = parse_keep_registry(KEEP_REGISTRY)
    if keep_layer:
        layers.append(("keep_registry", keep_layer))

    # User intake batches — highest priority (explicit vault drops)
    for intake in sorted(VAULT_DIR.glob("intake_*.env")):
        layers.append((f"intake:{intake.name}", parse_env_file(intake)))

    for layer_name, layer in layers:
        layer = canonicalize(layer)
        for k, (v, src) in layer.items():
            merged[k] = (v, src)
            provenance[k] = f"{layer_name}:{src}"

    merged = enrich_from_credential_files(merged)
    for k, (v, src) in merged.items():
        if k not in provenance:
            provenance[k] = src

    return merged, provenance


def write_env(keys: dict[str, tuple[str, str]]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Colossus GateKeeper vault — generated {_now()}",
        "# Sources: gemini_keys, apex_vault, keep, operator audit",
        "",
    ]
    for k in sorted(keys):
        v, _ = keys[k]
        lines.append(f'export {k}="{v}"')
    OUT_ENV.write_text("\n".join(lines) + "\n")
    OUT_ENV.chmod(0o600)


def write_manifest(keys: dict[str, tuple[str, str]], provenance: dict[str, str]) -> None:
    services = []
    for k in sorted(keys):
        src = provenance.get(k, "")
        rotated = "keep" in src or "audit" in src
        services.append({
            "env_var": k,
            "source": src.split(":")[0][-40:] if src else "unknown",
            "historical_source": rotated,
            "loaded": True,
        })
    MANIFEST.write_text(json.dumps({
        "at": _now(),
        "total_keys": len(keys),
        "vault_path": str(OUT_ENV),
        "sources_scanned": [str(p) for p in SOURCES + KEEP_PATHS + [AUDIT_JSON]],
        "environment4_path": str(resolve_env4_path() or ""),
        "ag_cli_index": str(HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/ag_cli_environment/AG_CLI_ENVIRONMENT_INDEX.md"),
        "ag_cli_extracted": str(AG_CLI_EXTRACTED) if AG_CLI_EXTRACTED.is_file() else "",
        "keep_registry": str(KEEP_REGISTRY) if KEEP_REGISTRY.is_file() else "",
        "intake_batches": [str(p) for p in sorted(VAULT_DIR.glob("intake_*.env"))],
        "credentials_dir": str(VAULT_DIR / "credentials"),
        "note": "Priority: intake_batch > keep_registry > ag_cli/MASTER > environment4 > gemini_keys",
        "services": services,
    }, indent=2))


def main() -> int:
    keys, prov = merge_all()
    write_env(keys)
    write_manifest(keys, prov)
    print(f"Consolidated {len(keys)} keys → {OUT_ENV}")
    print(f"Manifest → {MANIFEST}")
    print("Services loaded:", ", ".join(sorted(keys.keys())[:20]), ("..." if len(keys) > 20 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())