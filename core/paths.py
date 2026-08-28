"""
Configurable Paths — Replace hardcoded /tasklet/ with environment-aware resolution
GlacierEQ APEX | computer-user core

Priority:
  1. Environment variables (APEX_*_DIR)
  2. ~/.apex/config.json paths
  3. Defaults ($HOME/automation/ or /tasklet/)
"""

import json
import os
from pathlib import Path

_CONFIG_PATH = Path.home() / ".apex" / "config.json"
_config = {}

if _CONFIG_PATH.exists():
    try:
        _config = json.loads(_CONFIG_PATH.read_text())
    except Exception:
        pass


def _resolve(env_key: str, config_key: str, default: str) -> Path:
    """Resolve a path from env var > config file > default."""
    val = os.environ.get(env_key)
    if val:
        return Path(val)
    val = _config.get(config_key)
    if val:
        return Path(val)
    return Path(default)


# ─── Core Paths ──────────────────────────────────────────────────────────────

BASE_DIR = _resolve("APEX_BASE_DIR", "base_dir", str(Path.home() / "automation"))
TASKLET_DIR = _resolve("APEX_TASKLET_DIR", "tasklet_dir", str(BASE_DIR / "tasklet"))
WORKSPACE_DIR = _resolve(
    "APEX_WORKSPACE_DIR", "workspace_dir", str(TASKLET_DIR / "workspace" / "home")
)
TMP_DIR = _resolve(
    "APEX_TMP_DIR", "tmp_dir", str(Path.home() / ".local" / "share" / "tmp")
)

# ─── Skill Output Paths ─────────────────────────────────────────────────────

GMAIL_DIR = TASKLET_DIR / "gmail"
GMAIL_FORENSIC_DIR = GMAIL_DIR / "forensic"
GMAIL_DRAFTS_DIR = GMAIL_DIR / "drafts"

VOICE_MEMOS_DIR = TASKLET_DIR / "voice-memos"
VOICE_MEMOS_PROCESSED = VOICE_MEMOS_DIR / "processed"

CATACLYSM_DIR = TASKLET_DIR / "cataclysm" / "evidence"
NOTION_QUEUE_DIR = TASKLET_DIR / "notion" / "queue"
PIPELINE_REPORTS_DIR = TASKLET_DIR / "pipeline-reports"

# ─── Config Files ────────────────────────────────────────────────────────────

CONNECTIONS_FILE = _resolve(
    "APEX_CONNECTIONS_FILE",
    "connections_file",
    str(Path.home() / ".apex" / "connections.json"),
)
SESSION_DIR = TASKLET_DIR / "sessions"
COOKIES_DIR = SESSION_DIR / "cookies"

# ─── Ensure directories exist ────────────────────────────────────────────────

ALL_DIRS = [
    TASKLET_DIR,
    WORKSPACE_DIR,
    TMP_DIR,
    GMAIL_DIR,
    GMAIL_FORENSIC_DIR,
    GMAIL_DRAFTS_DIR,
    VOICE_MEMOS_DIR,
    VOICE_MEMOS_PROCESSED,
    CATACLYSM_DIR,
    NOTION_QUEUE_DIR,
    PIPELINE_REPORTS_DIR,
    SESSION_DIR,
    COOKIES_DIR,
]


def ensure_dirs():
    """Create all output directories."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# Auto-create on import
ensure_dirs()


# ─── Credential Loader ──────────────────────────────────────────────────────


def load_credentials(service: str, account: str = "") -> dict:
    """
    Load credentials for a service.
    Priority: env vars > ~/.apex/connections.json

    Returns dict with service-specific keys (email, password, token, etc.)
    """
    creds = {}

    # Check env vars first
    prefix = f"APEX_{service.upper()}"
    for key in ["EMAIL", "PASSWORD", "TOKEN", "API_KEY", "SECRET"]:
        env_val = os.environ.get(f"{prefix}_{key}")
        if env_val:
            creds[key.lower()] = env_val

    # Check config file
    if CONNECTIONS_FILE.exists() and not creds:
        try:
            cfg = json.loads(CONNECTIONS_FILE.read_text())
            service_cfg = cfg.get(service, {})
            if isinstance(service_cfg, dict):
                if account and account in service_cfg:
                    creds = service_cfg[account]
                else:
                    creds = service_cfg
            elif isinstance(service_cfg, str):
                creds = {"token": service_cfg}
        except Exception:
            pass

    return creds
