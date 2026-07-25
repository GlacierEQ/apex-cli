#!/usr/bin/env bash
# install.sh — Complete runtime installer
# Run: bash install.sh

set -euo pipefail

echo "=== APEX CLI INSTALLER ==="
echo ""

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/bin"
CONFIG_DIR="$HOME/.apex"
MEMORY_DIR="$HOME/.local/share/mimocode/memory"

# Create directories
echo "Creating directories..."
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$MEMORY_DIR"

# Install CLI tools
echo "Installing CLI tools..."
cp "$BUNDLE_DIR"/apex-* "$BIN_DIR/" 2>/dev/null
chmod +x "$BIN_DIR"/apex-* 2>/dev/null
echo "  ✅ CLI tools installed to ~/bin/"

# Install core modules
echo "Installing core modules..."
mkdir -p "$CONFIG_DIR/core"
cp "$BUNDLE_DIR"/core/*.py "$CONFIG_DIR/core/" 2>/dev/null
echo "  ✅ Core modules installed"

# Install config
echo "Installing config..."
if [ -f "$BUNDLE_DIR/config/AGENTS.md" ]; then
    cp "$BUNDLE_DIR/config/AGENTS.md" "$HOME/" 2>/dev/null || true
elif [ -f "$BUNDLE_DIR/AGENTS.md" ]; then
    cp "$BUNDLE_DIR/AGENTS.md" "$HOME/" 2>/dev/null || true
fi
echo "  ✅ AGENTS.md installed"

# Install scripts
echo "Installing scripts..."
mkdir -p "$HOME/scripts"
[ -d "$BUNDLE_DIR/scripts" ] && cp "$BUNDLE_DIR"/scripts/*.py "$HOME/scripts/" 2>/dev/null || true
[ -d "$BUNDLE_DIR/scripts" ] && cp "$BUNDLE_DIR"/scripts/*.sh "$HOME/scripts/" 2>/dev/null || true
[ -d "$HOME/scripts" ] && chmod +x "$HOME/scripts/"*.sh 2>/dev/null || true
echo "  ✅ Scripts installed"

# Install tests
echo "Installing tests..."
mkdir -p "$HOME/tests"
[ -d "$BUNDLE_DIR/tests" ] && cp "$BUNDLE_DIR"/tests/*.py "$HOME/tests/" 2>/dev/null || true
echo "  ✅ Tests installed"

# Verify
echo ""
echo "=== VERIFICATION ==="
echo ""

# Check CLI tools
TOOL_COUNT=$(ls "$BIN_DIR"/apex-* 2>/dev/null | wc -l)
echo "CLI tools: $TOOL_COUNT"

# Check core modules
CORE_COUNT=$(ls "$CONFIG_DIR/core/"*.py 2>/dev/null | wc -l)
echo "Core modules: $CORE_COUNT"

# Check scripts
SCRIPT_COUNT=$(find "$HOME/scripts" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Scripts: $SCRIPT_COUNT"

# Test browser adapter
echo ""
echo "Testing browser adapter..."
python3 -c "import sys; sys.path.insert(0, '$CONFIG_DIR/core'); from browser_adapter import get_backend; print('  ✅ Browser adapter loaded')" 2>/dev/null || echo "  ⚠️ Browser adapter needs dependencies"

# Test space monitor
echo ""
echo "Testing space monitor..."
bash "$BIN_DIR/apex-space-monitor" 2>/dev/null | head -5 || echo "  ⚠️ Space monitor needs bash"

echo ""
echo "=== INSTALL COMPLETE ==="
echo ""
echo "Installed:"
echo "  $TOOL_COUNT CLI tools → ~/bin/"
echo "  $CORE_COUNT core modules → ~/.apex/core/"
echo "  $SCRIPT_COUNT scripts → ~/scripts/"
echo ""
echo "Next steps:"
echo "  1. Ensure ~/bin/ is in PATH: export PATH=\"\$HOME/bin:\$PATH\""
echo "  2. Run: apex-space-monitor"
echo "  3. Run: apex-daemon"
