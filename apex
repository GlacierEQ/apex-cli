#!/usr/bin/env bash
# apex — bounded APEX CLI dispatcher
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HOME_DIR="${HOME:-}"
JOB_APP_DIR="${APEX_JOB_APP_DIR:-${HOME_DIR:+$HOME_DIR/job-app}}"
RUNTIME_COMMIT="1afda64498ddd90345231cdecec36cd85919a961"

exec_local_or_bin() {
    local command_name="$1"
    shift
    if [[ -x "$SCRIPT_DIR/$command_name" ]]; then
        exec "$SCRIPT_DIR/$command_name" "$@"
    fi
    if [[ -n "$HOME_DIR" && -x "$HOME_DIR/bin/$command_name" ]]; then
        exec "$HOME_DIR/bin/$command_name" "$@"
    fi
    echo "APEX dependency unavailable: $command_name" >&2
    exit 78
}

require_home() {
    if [[ -z "$HOME_DIR" ]]; then
        echo "APEX runtime unavailable: HOME is unset" >&2
        exit 78
    fi
}

runtime_control() {
    require_home
    local root="$HOME_DIR/.apex/runtime_projection"
    local cli="$root/scripts/runtime_cli.py"
    local compiler="$root/runtime/compiler.py"
    local contracts="$root/runtime/contracts"
    if [[ ! -f "$cli" || ! -f "$compiler" || ! -d "$contracts" ]]; then
        echo "APEX canonical runtime projection unavailable under $root" >&2
        exit 78
    fi
    exec python3 "$cli" \
        --state-root "$HOME_DIR/.apex/runtime_state" \
        --contract-dir "$contracts" \
        --canonical-commit "$RUNTIME_COMMIT" \
        --compiler-path "$compiler" \
        "$@"
}

require_job_app_file() {
    local relative_path="$1"
    if [[ -z "$JOB_APP_DIR" ]]; then
        echo "APEX external job-app dependency unavailable: APEX_JOB_APP_DIR is unset and HOME is unavailable" >&2
        exit 78
    fi
    local path="$JOB_APP_DIR/$relative_path"
    if [[ ! -f "$path" ]]; then
        echo "APEX external job-app dependency unavailable: $path" >&2
        echo "Set APEX_JOB_APP_DIR to an explicit verified checkout if needed." >&2
        exit 78
    fi
    printf '%s\n' "$path"
}

SUBCOMMAND="${1:-help}"
shift || true

case "$SUBCOMMAND" in
    boot|start)
        require_home
        startup="$HOME_DIR/.apex/startup.sh"
        if [[ ! -x "$startup" ]]; then
            echo "APEX runtime unavailable: $startup is missing or not executable" >&2
            exit 78
        fi
        exec "$startup" "$@"
        ;;
    compose|runtime)
        require_home
        activator="$HOME_DIR/scripts/dynamic_skill_activator.py"
        if [[ ! -f "$activator" ]]; then
            echo "APEX composition adapter unavailable: $activator is missing" >&2
            exit 78
        fi
        exec python3 "$activator" "${*:-session}"
        ;;
    runtimectl)
        runtime_control "$@"
        ;;
    replay)
        require_home
        target="${1:-$HOME_DIR/.apex/last_runtime_receipt.json}"
        runtime_control replay "$target"
        ;;
    resume)
        require_home
        target="${1:-$HOME_DIR/.apex/last_runtime_receipt.json}"
        runtime_control resume "$target"
        ;;
    capabilities)
        runtime_control capabilities "$@"
        ;;
    runtime-health)
        runtime_control health "$@"
        ;;
    governor)
        if [[ $# -eq 0 || "${1:-}" == "status" ]]; then
            runtime_control governor-status
        fi
        runtime_control "$@"
        ;;
    runtime-status)
        require_home
        receipt="$HOME_DIR/.apex/last_runtime_receipt.json"
        composition="$HOME_DIR/.apex/last_composition_receipt.json"
        if [[ ! -f "$receipt" ]]; then
            echo "APEX runtime receipt unavailable: $receipt" >&2
            exit 78
        fi
        exec python3 - "$receipt" "$composition" <<'PY'
import json
import sys
from pathlib import Path
runtime_path = Path(sys.argv[1])
composition_path = Path(sys.argv[2])
runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
composition = json.loads(composition_path.read_text(encoding="utf-8")) if composition_path.is_file() else None
print(json.dumps({
    "status": runtime.get("status"),
    "schema": runtime.get("schema"),
    "run_id": runtime.get("run_id"),
    "canonical_runtime": runtime.get("runtime", {}).get("canonical_repository"),
    "canonical_commit": runtime.get("runtime", {}).get("canonical_commit"),
    "current_stage": runtime.get("continuation", {}).get("current_stage"),
    "completed_stages": runtime.get("continuation", {}).get("completed_stages", []),
    "blockers": runtime.get("blockers", []),
    "composition_status": composition.get("status") if composition else None,
    "composition_skills": composition.get("skills", []) if composition else [],
    "receipt": str(runtime_path),
}, indent=2))
PY
        ;;
    openclaw|claw)
        exec_local_or_bin apex-openclaw "$@"
        ;;
    daemon)
        exec_local_or_bin apex-daemon "$@"
        ;;
    highway)
        highway="$(require_job_app_file apex_highway.py)"
        exec python3 "$highway" "$@"
        ;;
    hero|heroes|demo)
        heroes="$(require_job_app_file demo_heroes.sh)"
        exec bash "$heroes" "$@"
        ;;
    status|health)
        highway="$(require_job_app_file apex_highway.py)"
        governance="$(require_job_app_file apex_agent_governance_matrix.py)"
        echo "=== APEX SYSTEM STATUS ==="
        echo "APEX Highway Engine:"
        python3 "$highway"
        echo ""
        echo "APEX Governance Matrix:"
        python3 "$governance"
        ;;
    help|--help|-h)
        cat <<'EOF'
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
    *)
        echo "Unknown command: $SUBCOMMAND" >&2
        echo "Run 'apex help' for available commands." >&2
        exit 1
        ;;
esac
