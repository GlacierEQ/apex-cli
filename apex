#!/usr/bin/env bash
# apex — bounded APEX CLI dispatcher
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
JOB_APP_DIR="${APEX_JOB_APP_DIR:-$HOME/job-app}"

exec_local_or_bin() {
    local command_name="$1"
    shift
    if [[ -x "$SCRIPT_DIR/$command_name" ]]; then
        exec "$SCRIPT_DIR/$command_name" "$@"
    fi
    if [[ -x "$HOME/bin/$command_name" ]]; then
        exec "$HOME/bin/$command_name" "$@"
    fi
    echo "APEX dependency unavailable: $command_name" >&2
    exit 78
}

require_job_app_file() {
    local relative_path="$1"
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

Repository-local commands:
  apex openclaw [action] [target]  Run the apex-openclaw command if installed here or in ~/bin
  apex daemon                      Run the apex-daemon command if installed here or in ~/bin

Explicit external job-app commands:
  apex highway                     Run apex_highway.py from APEX_JOB_APP_DIR
  apex hero                        Run demo_heroes.sh from APEX_JOB_APP_DIR
  apex status                      Run highway + governance scripts from APEX_JOB_APP_DIR

External job-app commands fail closed with exit 78 when their files are absent.
EOF
        ;;
    *)
        echo "Unknown command: $SUBCOMMAND" >&2
        echo "Run 'apex help' for available commands." >&2
        exit 1
        ;;
esac
