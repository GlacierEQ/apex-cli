#!/usr/bin/env python3
"""
Ingest Antigravity CLI + Gemini CLI environment into operator vault.

Sources:
  - antigravity-cli/conversations/*.db (most recent first — Keep paste chats)
  - antigravity-cli/history.jsonl
  - .apex_vault/AGENTS/MASTER.env + SHARED_KEYS.env
  - gemini settings/mcp config (env var names only)
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
AG_CLI = HOME / ".apex_vault/AGENTS/gemini/antigravity-cli"
GEMINI = HOME / ".apex_vault/AGENTS/gemini"
VAULT_AGENTS = HOME / ".apex_vault/AGENTS"
OUT_DIR = HOME / "MISSIONS/SUPPORTING_DATA/SECRETS_AUDIT/ag_cli_environment"
EXTRACTED_KEYS = OUT_DIR / "ag_cli_extracted.env"
INDEX_MD = OUT_DIR / "AG_CLI_ENVIRONMENT_INDEX.md"

TOKEN_PATTERNS = [
    (re.compile(r"(sk-proj-[a-zA-Z0-9_-]{20,})"), "OPENAI_API_KEY"),
    (re.compile(r"(sk-ant-api[0-9a-zA-Z_-]+)"), "ANTHROPIC_API_KEY"),
    (re.compile(r"(github_pat_[a-zA-Z0-9_]+)"), "GITHUB_TOKEN"),
    (re.compile(r"(ghp_[a-zA-Z0-9]+)"), "GITHUB_TOKEN"),
    (re.compile(r"(ntn_[a-zA-Z0-9]+)"), "NOTION_API_KEY"),
    (re.compile(r"(m0-[a-zA-Z0-9]+)"), "MEM0_API_KEY"),
    (re.compile(r"(sm_[a-zA-Z0-9_]{20,})"), "SUPERMEMORY_API_KEY"),
    (re.compile(r"(gsk_[a-zA-Z0-9]+)"), "GROQ_API_KEY"),
    (re.compile(r"(AIza[0-9A-Za-z_-]{30,})"), "GEMINI_API_KEY"),
    (re.compile(r"(pcsk_[a-zA-Z0-9]+)"), "PINECONE_API_KEY"),
    (re.compile(r"(pplx-[a-zA-Z0-9]+)"), "PERPLEXITY_API_KEY"),
    (re.compile(r"(sk-or-v1-[a-f0-9]+)"), "OPENROUTER_API_KEY"),
    (re.compile(r"(sk-[a-f0-9]{32})"), "DEEPSEEK_API_KEY"),
    (re.compile(r"(lin_api_[a-zA-Z0-9]+)"), "LINEAR_API_KEY"),
    (re.compile(r"(sbp_[a-f0-9]+)"), "SUPABASE_SERVICE_KEY"),
    (re.compile(r"(xai-[a-zA-Z0-9_-]{20,})"), "XAI_API_KEY"),
    (re.compile(r"(hf_[a-zA-Z0-9]+)"), "HUGGINGFACE_API_KEY"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_from_blob(data: bytes | str) -> dict[str, str]:
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="ignore")
    else:
        text = str(data)
    found: dict[str, str] = {}
    for pat, var in TOKEN_PATTERNS:
        for m in pat.finditer(text):
            found[var] = m.group(1)
    return found


def extract_conversation_dbs() -> tuple[dict[str, tuple[str, str]], list[dict]]:
    keys: dict[str, tuple[str, str]] = {}
    conv_meta: list[dict] = []
    conv_dir = AG_CLI / "conversations"
    if not conv_dir.is_dir():
        return keys, conv_meta

    dbs = sorted(conv_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for db in dbs:
        signal_steps = 0
        db_keys: dict[str, str] = {}
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT step_payload, metadata FROM steps")
            for payload, meta in cur.fetchall():
                for blob in (payload, meta):
                    if not blob:
                        continue
                    extracted = extract_from_blob(blob)
                    if extracted:
                        signal_steps += 1
                        db_keys.update(extracted)
            conn.close()
        except sqlite3.Error:
            continue

        conv_meta.append({
            "id": db.stem,
            "mtime": datetime.fromtimestamp(db.stat().st_mtime, tz=timezone.utc).isoformat(),
            "size_mb": round(db.stat().st_size / 1048576, 1),
            "signal_steps": signal_steps,
            "keys_found": len(db_keys),
        })
        for var, val in db_keys.items():
            if var not in keys:
                keys[var] = (val, f"ag_cli:{db.name}")

    return keys, conv_meta


def extract_history_jsonl() -> dict[str, tuple[str, str]]:
    keys: dict[str, tuple[str, str]] = {}
    hist = AG_CLI / "history.jsonl"
    if not hist.is_file():
        return keys
    for line in hist.read_text(encoding="utf-8", errors="ignore").splitlines():
        for var, val in extract_from_blob(line).items():
            if var not in keys:
                keys[var] = (val, "ag_cli:history.jsonl")
    return keys


def parse_env_file(path: Path, label: str) -> dict[str, tuple[str, str]]:
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
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v:
            found[k] = (v, label)
    return found


def write_extracted_env(all_keys: dict[str, tuple[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# AG CLI environment extract — {_now()}", ""]
    for k in sorted(all_keys):
        v, _ = all_keys[k]
        lines.append(f'export {k}="{v}"')
    EXTRACTED_KEYS.write_text("\n".join(lines) + "\n")
    EXTRACTED_KEYS.chmod(0o600)


def write_index(conv_meta: list[dict], key_count: int) -> None:
    recent = conv_meta[0] if conv_meta else {}
    lines = [
        "# Antigravity CLI + Gemini CLI Environment Index",
        "",
        f"**Updated:** {_now()}",
        "",
        "## Canonical paths",
        "",
        "| Component | Path |",
        "|-----------|------|",
        f"| Antigravity CLI root | `{AG_CLI}` |",
        f"| Gemini agent home | `{GEMINI}` |",
        f"| MASTER.env | `{VAULT_AGENTS / 'MASTER.env'}` |",
        f"| SHARED_KEYS.env | `{VAULT_AGENTS / 'SHARED_KEYS.env'}` |",
        f"| Vault catalog | `{VAULT_AGENTS / 'VAULT_CATALOG.md'}` |",
        "",
        "## Most recent conversation (Keep paste + AI processing)",
        "",
    ]
    if recent:
        lines.extend([
            f"- **ID:** `{recent.get('id')}`",
            f"- **Modified:** {recent.get('mtime')}",
            f"- **Size:** {recent.get('size_mb')} MB",
            f"- **Steps with key/signal content:** {recent.get('signal_steps')}",
            f"- **Unique tokens extracted:** {recent.get('keys_found')}",
            "",
        ])
    lines.extend([
        "## Conversation archive (newest first)",
        "",
        "| ID | Modified | MB | Keys |",
        "|----|----------|-----|------|",
    ])
    for c in conv_meta[:12]:
        lines.append(f"| `{c['id'][:8]}…` | {c['mtime'][:10]} | {c['size_mb']} | {c['keys_found']} |")

    lines.extend([
        "",
        "## Gemini CLI MCP mesh (from settings.json)",
        "",
        "- github, gdrive, filesystem, dropbox, onedrive",
        "- taskade, web_search, memory_systems, quantum_code_synthesis",
        "",
        "## Extracted keys",
        "",
        f"**{key_count}** canonical vars → `{EXTRACTED_KEYS}`",
        "",
        "## Commands",
        "",
        "```bash",
        "python3 scripts/ingest_ag_cli_environment.py",
        "sm-ops prime-keys",
        "```",
    ])
    INDEX_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    merged: dict[str, tuple[str, str]] = {}

    # Lowest → highest priority
    merged.update(extract_history_jsonl())
    db_keys, conv_meta = extract_conversation_dbs()
    for k, v in db_keys.items():
        merged[k] = v
    for path, label in [
        (VAULT_AGENTS / "SHARED_KEYS.env", "shared_keys"),
        (VAULT_AGENTS / "MASTER.env", "master_env"),
    ]:
        for k, v in parse_env_file(path, label).items():
            merged[k] = v

    write_extracted_env(merged)
    write_index(conv_meta, len(merged))
    print(f"AG CLI ingest: {len(merged)} keys → {EXTRACTED_KEYS}")
    print(f"Index → {INDEX_MD}")
    if conv_meta:
        r = conv_meta[0]
        print(f"Latest conv: {r['id']} ({r['size_mb']}MB, {r['keys_found']} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())