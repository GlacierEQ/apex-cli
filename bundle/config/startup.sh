#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
  echo "[APEX STARTUP] failed: HOME unavailable" >&2
  exit 78
fi

APEX_DIR="$HOME_DIR/.apex"
STATE="$APEX_DIR/STARTUP_STATE.json"
ACTIVATION="$APEX_DIR/MASTERSKILL_ACTIVATION.json"
RECEIPT="$APEX_DIR/last_runtime_receipt.json"
TASK="${*:-session}"

export GLACIEREQ_MASTERSKILL="glaciereq-nervous-system"
export GLACIEREQ_MASTERSKILL_ACTIVATION="$ACTIVATION"

if [[ ! -f "$ACTIVATION" ]]; then
  echo "[APEX STARTUP] failed: missing $ACTIVATION" >&2
  exit 11
fi

ACTIVATOR=""
for candidate in \
  "$HOME_DIR/scripts/dynamic_skill_activator.py" \
  "$HOME_DIR/MiMo-Config/scripts/dynamic_skill_activator.py" \
  "$HOME_DIR/mimo-config/scripts/dynamic_skill_activator.py"
do
  if [[ -f "$candidate" ]]; then
    ACTIVATOR="$candidate"
    break
  fi
done

if [[ -z "$ACTIVATOR" ]]; then
  echo "[APEX STARTUP] failed: no nervous-system composition compiler is installed" >&2
  exit 12
fi

if command -v sm-ops >/dev/null 2>&1; then
  (
    unset SUPERMEMORY_API_KEY || true
    sm-ops prime "$TASK" --max-tokens 1000
  ) >/dev/null 2>&1 || true
fi

python3 "$ACTIVATOR" "$TASK"

if [[ ! -f "$RECEIPT" ]]; then
  echo "[APEX STARTUP] failed: no runtime receipt emitted" >&2
  exit 13
fi

python3 - "$RECEIPT" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("status") != "READY":
    raise SystemExit(f"[APEX STARTUP] failed: runtime status={data.get('status')!r}")
if data.get("masterskill") != "glaciereq-nervous-system":
    raise SystemExit(f"[APEX STARTUP] failed: unexpected masterskill={data.get('masterskill')!r}")
print(f"[APEX STARTUP] READY masterskill={data['masterskill']} receipt={path}")
PY
