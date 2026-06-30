#!/usr/bin/env bash
# space-monitor.sh — Automated disk space monitoring and cleanup
# Run: bash ~/scripts/space-monitor.sh

set -euo pipefail

LOG_FILE="$HOME/.local/share/tmp/space_monitor.log"
DAILY_REPORT="$HOME/.local/share/tmp/space_daily_report.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

get_usage() {
    local path="$1"
    local total=$(df "$path" 2>/dev/null | tail -1 | awk '{print $2}')
    local used=$(df "$path" 2>/dev/null | tail -1 | awk '{print $3}')
    local avail=$(df "$path" 2>/dev/null | tail -1 | awk '{print $4}')
    local pct=$(df "$path" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
    echo "$total $used $avail $pct"
}

echo -e "${YELLOW}=== SPACE MONITOR ===${NC}"
echo ""

# Check all partitions
for mount in "/" "/data" "/storage/emulated"; do
    if mountpoint -q "$mount" 2>/dev/null || [ -d "$mount" ]; then
        read total used avail pct <<< $(get_usage "$mount")
        if [ "$pct" -gt 90 ]; then
            echo -e "${RED}⚠️  $mount: ${pct}% used (${avail}K free)${NC}"
        elif [ "$pct" -gt 75 ]; then
            echo -e "${YELLOW}⚡ $mount: ${pct}% used (${avail}K free)${NC}"
        else
            echo -e "${GREEN}✅ $mount: ${pct}% used (${avail}K free)${NC}"
        fi
    fi
done

echo ""
echo -e "${YELLOW}=== TOP SPACE CONSUMERS ===${NC}"
du -sh "$HOME"/MISSIONS "$HOME"/CYBERTACK "$HOME"/.apex_automation "$HOME"/.git "$HOME"/.npm "$HOME"/.cache 2>/dev/null | sort -rh | head -10

echo ""
echo -e "${YELLOW}=== AUTOMATED CLEANUP ===${NC}"

# 1. Clear caches
echo "Clearing caches..."
rm -rf "$HOME/.cache/pip" 2>/dev/null && echo "  ✅ pip cache"
rm -rf "$HOME/.cache/chromium" 2>/dev/null && echo "  ✅ chromium cache"
rm -rf "$HOME/.cache/mesa_shader_cache" 2>/dev/null && echo "  ✅ mesa shader cache"
rm -rf "$HOME/.cache/next-swc" 2>/dev/null && echo "  ✅ next-swc cache"

# 2. Clear package manager
echo "Clearing package manager..."
apt clean 2>/dev/null && echo "  ✅ apt cache"

# 3. Clear temp files
echo "Clearing temp files..."
rm -rf /tmp/*.log /tmp/*.tmp 2>/dev/null && echo "  ✅ temp files"

# 4. Compress old log files
echo "Compressing old logs..."
find "$HOME" -name "*.log" -mtime +7 -exec gzip {} \; 2>/dev/null && echo "  ✅ compressed old logs"

# 5. Remove empty directories
echo "Removing empty directories..."
find "$HOME" -type d -empty -delete 2>/dev/null && echo "  ✅ removed empty dirs"

# 6. Report
echo ""
echo -e "${GREEN}=== CLEANUP COMPLETE ===${NC}"
echo ""

# Final status
for mount in "/" "/data" "/storage/emulated"; do
    if mountpoint -q "$mount" 2>/dev/null || [ -d "$mount" ]; then
        read total used avail pct <<< $(get_usage "$mount")
        echo "$mount: ${pct}% used (${avail}K free)"
    fi
done

log "Cleanup completed at $(date)"
