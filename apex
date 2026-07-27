#!/usr/bin/env bash
# apex — Unified APEX Ecosystem CLI Runner
set -euo pipefail

SUBCOMMAND="${1:-help}"
shift || true

case "$SUBCOMMAND" in
    openclaw|claw)
        exec "$HOME/bin/apex-openclaw" "$@"
        ;;
    daemon)
        exec "$HOME/bin/apex-daemon" "$@"
        ;;
    highway)
        exec python3 "$HOME/job-app/apex_highway.py" "$@"
        ;;
    hero|heroes|demo)
        exec bash "$HOME/job-app/demo_heroes.sh" "$@"
        ;;
    status|health)
        echo "=== APEX SYSTEM STATUS ==="
        echo "APEX Highway Engine:"
        python3 "$HOME/job-app/apex_highway.py"
        echo ""
        echo "APEX Governance Matrix:"
        python3 "$HOME/job-app/apex_agent_governance_matrix.py"
        ;;
    help|--help|-h)
        echo "=== APEX MASTER CLI ==="
        echo "Usage: apex <command> [args]"
        echo ""
        echo "Commands:"
        echo "  apex openclaw [action] [target]  Run OpenClaw computer-user action engine"
        echo "  apex openclaw vision             Sample screen vision & OCR elements"
        echo "  apex openclaw config             Display OpenClaw top-tier configuration"
        echo "  apex daemon                      Run APEX background daemon"
        echo "  apex highway                     Scan 61-node APEX Highway network mesh"
        echo "  apex hero                        Run 20-Hero demonstration suite"
        echo "  apex status                      Display system status and governance matrix"
        ;;
    *)
        echo "Unknown command: $SUBCOMMAND" >&2
        echo "Run 'apex help' for available commands." >&2
        exit 1
        ;;
esac
