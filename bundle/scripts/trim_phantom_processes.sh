#!/data/data/com.termux/files/usr/bin/bash
# Trim processes — target ≤18 under default 32 cap (real safe zone)
set -euo pipefail

STAMP="${HOME:-/data/data/com.termux/files/home}/.apex/phantom_limit_raised"
if [ -f "$STAMP" ]; then
  TARGET="${TARGET:-40}"
else
  TARGET="${TARGET:-18}"
fi
C_YELLOW='\033[93m'
C_GREEN='\033[92m'
C_RESET='\033[0m'

count() { ps -efww 2>/dev/null | grep -v grep | wc -l | tr -d ' '; }

kill_pattern() {
  local pattern="$1"
  local pids
  pids=$(pgrep -f "$pattern" 2>/dev/null || true)
  for pid in $pids; do
    echo "Stopping pid $pid ($pattern)"
    kill "$pid" 2>/dev/null || true
  done
}

BEFORE=$(count)
echo -e "Processes before: ${C_YELLOW}${BEFORE}${C_RESET} (safe target ≤ ${TARGET})"

adb kill-server 2>/dev/null || true

for pattern in \
  "backend_guardian" "qdrant" "neo4j console" \
  "apex_optimizer.py" "codex_weaver.py" "autonomous_litigation_daemon" \
  "gnome-keyring-daemon" "agy.va39" "dbus-daemon"; do
  kill_pattern "$pattern"
done

if [ "$(count)" -gt "$TARGET" ]; then
  kill_pattern "crash_protect.py --daemon"
fi

if [ "$(count)" -gt "$TARGET" ] && command -v sv >/dev/null 2>&1; then
  sv down cupsd 2>/dev/null || true
  echo "Stopped cupsd"
fi

sleep 1
AFTER=$(count)
echo -e "Processes after:  ${C_GREEN}${AFTER}${C_RESET} (freed $((BEFORE - AFTER)))"

if [ ! -f "$STAMP" ] && [ "$AFTER" -gt 20 ]; then
  echo -e "${C_YELLOW}Still high. Flip Developer Options → Disable child process restrictions, then sm-ops raise-limit --confirm${C_RESET}"
  exit 1
fi
if [ -f "$STAMP" ]; then
  echo -e "${C_GREEN}Raised limit active (dev toggle). Headroom OK at ${AFTER} processes.${C_RESET}"
fi