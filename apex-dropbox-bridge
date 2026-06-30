#!/usr/bin/env bash
# Bridge cloud Dropbox ingest → local apex-fs-commander-alpha/dropbox/ watcher
set -euo pipefail

HOME="${HOME:-/data/data/com.termux/files/home}"
ALPHA_DROPBOX="${HOME}/MISSIONS/APEX_INFRASTRUCTURE/INFRASTRUCTURE/apex-fs-commander-alpha/dropbox"
LOG="${HOME}/.apex/dropbox_bridge.log"
LOCK="${HOME}/.apex/dropbox_bridge.lock"

mkdir -p "$(dirname "$LOG")" "$ALPHA_DROPBOX"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) skip — bridge already running" >>"$LOG"
  exit 0
fi

{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) dropbox_bridge start ==="
  # Primary ingest lane
  rclone copy "dropbox:FileBoss_Inbox" "$ALPHA_DROPBOX" \
    --include "*.pdf" --include "*.PDF" \
    --include "*.md" --include "*.txt" \
    --max-age 168h --verbose --stats-one-line 2>&1 || true
  # Fallback: recent PDFs dropped in case ops root
  rclone copy "dropbox:01_CASE_CENTRIC_OPS" "$ALPHA_DROPBOX/inbox_case_ops" \
    --include "*.pdf" --include "*.PDF" \
    --max-depth 3 --max-age 168h --verbose --stats-one-line 2>&1 || true
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) dropbox_bridge done ==="
} >>"$LOG" 2>&1

# Kick watcher once if daemon not running
if ! pgrep -f "notion_workers_daemon.py" >/dev/null 2>&1; then
  source "${HOME}/.operator_key_vault/gatekeeper.env" 2>/dev/null || true
  python3 "${HOME}/scripts/notion_workers_daemon.py" --worker dropbox >>"$LOG" 2>&1 || true
fi