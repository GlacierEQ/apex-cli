#!/data/data/com.termux/files/usr/bin/bash
# Raise phantom-process cap — SAFE PATH ONLY (Developer Options toggle)
# ADB / Wireless Debugging intentionally NOT used.
set -euo pipefail

HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
STAMP="$HOME_DIR/.apex/phantom_limit_raised"
LOG="$HOME_DIR/logs/phantom_limit.log"
mkdir -p "$(dirname "$LOG")"

C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_CYAN='\033[96m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

count_procs() { ps -efww 2>/dev/null | grep -v grep | wc -l | tr -d ' '; }

echo -e "${C_BOLD}${C_CYAN}APEX — Raise Phantom Process Limit (safe path only)${C_RESET}"
echo "──────────────────────────────────────────────────"
echo -e "Processes now: ${C_BOLD}$(count_procs)${C_RESET} / 32 Android cap"
echo ""
echo -e "${C_BOLD}On the tablet:${C_RESET}"
echo "  1. Settings → System → Developer Options"
echo "  2. Enable: ${C_GREEN}Disable child process restrictions${C_RESET}"
echo "  3. Run: ${C_CYAN}sm-ops raise-limit --confirm${C_RESET}"
echo ""
echo -e "${C_YELLOW}ADB / Wireless Debugging is not used — not safe for this device.${C_RESET}"
echo ""

if [[ "${1:-}" != "--confirm" ]]; then
  echo "After the toggle is ON, run: sm-ops raise-limit --confirm"
  exit 0
fi

echo "$(date -Iseconds) source=dev_toggle_disable_child_process_restrictions" > "$STAMP"
echo "[$(date -Iseconds)] phantom limit raised via dev toggle" >> "$LOG"
echo -e "${C_GREEN}Confirmed. Stamp: $STAMP${C_RESET}"
echo -e "Keep ≤20 processes until stable. Run: ${C_CYAN}sm-ops trim-procs${C_RESET}"