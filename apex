#!/usr/bin/env bash
# apex — bounded APEX CLI dispatcher
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HOME_DIR="${HOME:-}"
JOB_APP_DIR="${APEX_JOB_APP_DIR:-${HOME_DIR:+$HOME_DIR/job-app}}"
RUNTIME_COMMIT="84a2907a316327e91dc0426f5407a34908aa4fc4"

exec_local_or_bin() {
    local command_name="$1"
    shift
    if [[ -x "$SCRIPT_DIR/$command_name" ]]; then exec "$SCRIPT_DIR/$command_name" "$@"; fi
    if [[ -n "$HOME_DIR" && -x "$HOME_DIR/bin/$command_name" ]]; then exec "$HOME_DIR/bin/$command_name" "$@"; fi
    echo "APEX dependency unavailable: $command_name" >&2; exit 78
}
require_home() { [[ -n "$HOME_DIR" ]] || { echo "APEX runtime unavailable: HOME is unset" >&2; exit 78; }; }
runtime_control() {
    require_home
    local root="$HOME_DIR/.apex/runtime_projection" cli="$root/scripts/runtime_cli.py" compiler="$root/runtime/compiler.py" contracts="$root/runtime/contracts"
    [[ -f "$cli" && -f "$compiler" && -d "$contracts" ]] || { echo "APEX canonical runtime projection unavailable under $root" >&2; exit 78; }
    exec python3 "$cli" --state-root "$HOME_DIR/.apex/runtime_state" --contract-dir "$contracts" --canonical-commit "$RUNTIME_COMMIT" --compiler-path "$compiler" "$@"
}
require_job_app_file() {
    local relative_path="$1" path
    [[ -n "$JOB_APP_DIR" ]] || { echo "APEX external job-app dependency unavailable: APEX_JOB_APP_DIR is unset and HOME is unavailable" >&2; exit 78; }
    path="$JOB_APP_DIR/$relative_path"
    [[ -f "$path" ]] || { echo "APEX external job-app dependency unavailable: $path" >&2; echo "Set APEX_JOB_APP_DIR to an explicit verified checkout if needed." >&2; exit 78; }
    printf '%s\n' "$path"
}
SUBCOMMAND="${1:-help}"; shift || true
case "$SUBCOMMAND" in
  boot|start) require_home; startup="$HOME_DIR/.apex/startup.sh"; [[ -x "$startup" ]] || { echo "APEX runtime unavailable: $startup is missing or not executable" >&2; exit 78; }; exec "$startup" "$@" ;;
  compose|runtime) require_home; activator="$HOME_DIR/scripts/dynamic_skill_activator.py"; [[ -f "$activator" ]] || { echo "APEX composition adapter unavailable: $activator is missing" >&2; exit 78; }; exec python3 "$activator" "${*:-session}" ;;
  runtimectl) runtime_control "$@" ;;
  replay) require_home; runtime_control replay "${1:-$HOME_DIR/.apex/last_runtime_receipt.json}" ;;
  resume) require_home; runtime_control resume "${1:-$HOME_DIR/.apex/last_runtime_receipt.json}" ;;
  capabilities) runtime_control capabilities "$@" ;;
  runtime-health) runtime_control health "$@" ;;
  governor) if [[ $# -eq 0 || "${1:-}" == "status" ]]; then runtime_control governor-status; else runtime_control "$@"; fi ;;
  runtime-status)
    require_home; receipt="$HOME_DIR/.apex/last_runtime_receipt.json"; composition="$HOME_DIR/.apex/last_composition_receipt.json"
    [[ -f "$receipt" ]] || { echo "APEX runtime receipt unavailable: $receipt" >&2; exit 78; }
    exec python3 - "$receipt" "$composition" <<'PY'
import json,sys
from pathlib import Path
rp,cp=Path(sys.argv[1]),Path(sys.argv[2]); r=json.loads(rp.read_text()); c=json.loads(cp.read_text()) if cp.is_file() else None
print(json.dumps({"status":r.get("status"),"schema":r.get("schema"),"run_id":r.get("run_id"),"canonical_runtime":r.get("runtime",{}).get("canonical_repository"),"canonical_commit":r.get("runtime",{}).get("canonical_commit"),"current_stage":r.get("continuation",{}).get("current_stage"),"completed_stages":r.get("continuation",{}).get("completed_stages",[]),"blockers":r.get("blockers",[]),"composition_status":c.get("status") if c else None,"composition_skills":c.get("skills",[]) if c else [],"receipt":str(rp)},indent=2))
PY
    ;;
  openclaw|claw) exec_local_or_bin apex-openclaw "$@" ;;
  daemon) exec_local_or_bin apex-daemon "$@" ;;
  highway) highway="$(require_job_app_file apex_highway.py)"; exec python3 "$highway" "$@" ;;
  hero|heroes|demo) heroes="$(require_job_app_file demo_heroes.sh)"; exec bash "$heroes" "$@" ;;
  status|health) highway="$(require_job_app_file apex_highway.py)"; governance="$(require_job_app_file apex_agent_governance_matrix.py)"; echo "=== APEX SYSTEM STATUS ==="; python3 "$highway"; python3 "$governance" ;;
  help|--help|-h) cat <<'EOF'
=== APEX CLI ===
Usage: apex <command> [args]

Nervous-system runtime:
  apex boot [objective]             Boot through the canonical resumable runtime
  apex compose [objective]          Recompute host skill composition evidence
  apex runtime-status               Read canonical runtime + composition state
  apex capabilities [args]          Read/select TTL-bound live capability state
  apex replay [receipt]             Attest compiler/contracts/skills/predicates
  apex resume [receipt|run_id]      Resume at the first incomplete lifecycle stage
  apex runtime-health [args]        Report runtime metrics and SLO evaluation
  apex governor [status]            Read resource-governor state
  apex runtimectl <command> ...     Full canonical runtime control surface

Repository-local commands:
  apex openclaw [action] [target]   Run apex-openclaw if installed here or in ~/bin
  apex daemon                       Run apex-daemon if installed here or in ~/bin

Explicit external job-app commands:
  apex highway                      Run apex_highway.py from APEX_JOB_APP_DIR
  apex hero                         Run demo_heroes.sh from APEX_JOB_APP_DIR
  apex status                       Run highway + governance scripts from APEX_JOB_APP_DIR

External job-app commands fail closed with exit 78 when their required files are absent.
Other external runtime dependencies also fail closed when required artifacts are unavailable.
EOF
    ;;
  *) echo "Unknown command: $SUBCOMMAND" >&2; echo "Run 'apex help' for available commands." >&2; exit 1 ;;
esac
