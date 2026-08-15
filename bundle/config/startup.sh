#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
  echo "[APEX STARTUP] failed: HOME unavailable" >&2
  exit 78
fi

APEX_DIR="$HOME_DIR/.apex"
ACTIVATION="$APEX_DIR/MASTERSKILL_ACTIVATION.json"
COMPOSITION_RECEIPT="$APEX_DIR/last_composition_receipt.json"
RUNTIME_ROOT="$APEX_DIR/runtime_projection"
RUNTIME_STATE="$APEX_DIR/runtime_state"
RUNTIME_CLI="$RUNTIME_ROOT/scripts/runtime_cli.py"
RUNTIME_VERIFY="$RUNTIME_ROOT/scripts/verify_runtime_projection.py"
RUNTIME_COMPILER="$RUNTIME_ROOT/runtime/compiler.py"
RUNTIME_CONTRACTS="$RUNTIME_ROOT/runtime/contracts"
RUNTIME_MANIFEST="$RUNTIME_ROOT/RUNTIME_PROJECTION.json"
CANONICAL_RUNTIME_COMMIT="84a2907a316327e91dc0426f5407a34908aa4fc4"
TASK="${*:-session}"
RUN_ID="boot-$(date +%s)-$$"

export GLACIEREQ_MASTERSKILL="glaciereq-nervous-system"
export GLACIEREQ_MASTERSKILL_ACTIVATION="$ACTIVATION"
export APEX_RUNTIME_CANONICAL_COMMIT="$CANONICAL_RUNTIME_COMMIT"
export APEX_RUNTIME_STATE_ROOT="$RUNTIME_STATE"
export APEX_RUNTIME_CONTRACT_DIR="$RUNTIME_CONTRACTS"
export APEX_RUNTIME_COMPILER="$RUNTIME_COMPILER"

runtime() {
  python3 "$RUNTIME_CLI" \
    --state-root "$RUNTIME_STATE" \
    --contract-dir "$RUNTIME_CONTRACTS" \
    --canonical-commit "$CANONICAL_RUNTIME_COMMIT" \
    --compiler-path "$RUNTIME_COMPILER" \
    "$@"
}

for required in "$ACTIVATION" "$RUNTIME_CLI" "$RUNTIME_VERIFY" "$RUNTIME_COMPILER" "$RUNTIME_MANIFEST"; do
  if [[ ! -f "$required" ]]; then
    echo "[APEX STARTUP] failed: missing $required" >&2
    exit 11
  fi
done

python3 "$RUNTIME_VERIFY" --root "$RUNTIME_ROOT" --expect-commit "$CANONICAL_RUNTIME_COMMIT" >/dev/null
runtime validate-contract >/dev/null
runtime start "$TASK" --run-id "$RUN_ID" >/dev/null
runtime advance "$RUN_ID" >/dev/null

# Local capabilities are verified from present, checksum-validated files. External
# connectors/models remain DISCOVERED until a host adapter performs their live probes.
runtime capability-register runtime.kernel runtime local --ttl 3600 --scopes read,execute >/dev/null
runtime capability-probe runtime.kernel --connected --authenticated --authorized --invokable --verified --latency-ms 0 >/dev/null

for skill in glaciereq-nervous-system apex-aspen-grove-bootup verification; do
  skill_file="$HOME_DIR/.agents/skills/$skill/SKILL.md"
  if [[ ! -f "$skill_file" ]]; then
    echo "[APEX STARTUP] failed: missing baseline skill $skill_file" >&2
    exit 12
  fi
  runtime capability-register "skill.$skill" skill local --ttl 3600 --scopes read,execute --endpoint-ref "$skill_file" >/dev/null
  runtime capability-probe "skill.$skill" --connected --authenticated --authorized --invokable --verified --latency-ms 0 >/dev/null
done
runtime advance "$RUN_ID" >/dev/null

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
  echo "[APEX STARTUP] failed: no composition adapter is installed" >&2
  exit 13
fi

if command -v sm-ops >/dev/null 2>&1; then
  (
    unset SUPERMEMORY_API_KEY || true
    sm-ops prime "$TASK" --max-tokens 1000
  ) >/dev/null 2>&1 || true
fi

COMPOSE_START_NS="$(python3 -c 'import time; print(time.time_ns())')"
python3 "$ACTIVATOR" "$TASK" >/dev/null
COMPOSE_END_NS="$(python3 -c 'import time; print(time.time_ns())')"
COMPOSE_MS="$(python3 - "$COMPOSE_START_NS" "$COMPOSE_END_NS" <<'PY'
import sys
print((int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000)
PY
)"
runtime metric composition_latency_ms "$COMPOSE_MS" --labels-json "{\"run_id\":\"$RUN_ID\"}" >/dev/null

if [[ ! -f "$COMPOSITION_RECEIPT" ]]; then
  echo "[APEX STARTUP] failed: composition adapter emitted no receipt" >&2
  exit 14
fi
python3 - "$COMPOSITION_RECEIPT" <<'PY'
import json, sys
from pathlib import Path
receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if receipt.get("status") != "READY":
    raise SystemExit(f"composition status={receipt.get('status')!r} blockers={receipt.get('blockers')!r}")
PY

# The adapter completed DISCOVER/MAP/REUSE/EXTEND/EXECUTE/VERIFY/PERSIST as one
# host operation. Commit each canonical checkpoint only after the adapter returns READY.
for _ in 1 2 3 4 5 6 7 8; do
  runtime advance "$RUN_ID" >/dev/null
done

mkdir -p "$RUNTIME_STATE"
SKILLS_JSON="$RUNTIME_STATE/boot_skills.json"
PREDICATES_JSON="$RUNTIME_STATE/boot_predicates.json"
python3 - "$COMPOSITION_RECEIPT" "$SKILLS_JSON" <<'PY'
import json, sys
from pathlib import Path
source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Path(sys.argv[2]).write_text(json.dumps([
    {"name": item.get("name"), "path": item.get("path")}
    for item in source.get("skills", []) if item.get("path")
], indent=2) + "\n", encoding="utf-8")
PY
python3 - "$RUNTIME_MANIFEST" "$PREDICATES_JSON" <<'PY'
import hashlib, json, sys
from pathlib import Path
path = Path(sys.argv[1])
h = hashlib.sha256(path.read_bytes()).hexdigest()
Path(sys.argv[2]).write_text(json.dumps([
    {"type": "file_sha256", "path": str(path), "sha256": h}
], indent=2) + "\n", encoding="utf-8")
PY

runtime receipt "$RUN_ID" READY \
  --activation "$ACTIVATION" \
  --skills-json "$SKILLS_JSON" \
  --predicates-json "$PREDICATES_JSON" >/dev/null

CANONICAL_RECEIPT="$RUNTIME_STATE/last_runtime_receipt.json"
runtime replay "$CANONICAL_RECEIPT" >/dev/null
cp "$CANONICAL_RECEIPT" "$APEX_DIR/last_runtime_receipt.json"

python3 - "$APEX_DIR/last_runtime_receipt.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("schema") != "glaciereq.runtime-receipt.v2" or data.get("status") != "READY":
    raise SystemExit(f"[APEX STARTUP] failed: canonical receipt invalid: {data.get('schema')} {data.get('status')}")
PY

# READY is a terminal lifecycle claim. Publish it only after durable boot state,
# canonical receipt creation, replay attestation, and external receipt persistence
# have all succeeded. Any earlier failure leaves the run resumable rather than lying.
runtime finalize "$RUN_ID" READY >/dev/null

python3 - "$APEX_DIR/last_runtime_receipt.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print(f"[APEX STARTUP] READY run={data['run_id']} canonical={data['runtime']['canonical_commit']} receipt={path}")
PY
