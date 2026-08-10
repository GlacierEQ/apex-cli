#!/usr/bin/env bash
# install.sh — APEX CLI installer
# Run: bash install.sh

set -euo pipefail

HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
    echo "HOME is required for installation" >&2
    exit 78
fi

echo "=== APEX CLI INSTALLER ==="
echo ""

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME_DIR/bin"
CONFIG_DIR="$HOME_DIR/.apex"
MEMORY_DIR="$HOME_DIR/.local/share/mimocode/memory"

# Create directories
echo "Creating directories..."
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$MEMORY_DIR"

# Install CLI tools and the canonical dispatcher.
echo "Installing CLI tools..."
if [[ -f "$BUNDLE_DIR/apex" ]]; then
    cp "$BUNDLE_DIR/apex" "$BIN_DIR/apex"
    chmod +x "$BIN_DIR/apex"
fi
for tool in "$BUNDLE_DIR"/apex-*; do
    [[ -f "$tool" ]] || continue
    cp "$tool" "$BIN_DIR/"
    chmod +x "$BIN_DIR/$(basename "$tool")"
done
if [[ ! -x "$BIN_DIR/apex" ]]; then
    echo "APEX dispatcher installation failed" >&2
    exit 1
fi
echo "  CLI tools installed to ~/bin/"

# Install core modules
echo "Installing core modules..."
mkdir -p "$CONFIG_DIR/core"
for module in "$BUNDLE_DIR"/core/*.py; do
    [[ -f "$module" ]] || continue
    cp "$module" "$CONFIG_DIR/core/"
done
echo "  Core modules installed"

# Install config
echo "Installing config..."
if [[ -f "$BUNDLE_DIR/config/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/config/AGENTS.md" "$HOME_DIR/"
elif [[ -f "$BUNDLE_DIR/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/AGENTS.md" "$HOME_DIR/"
fi
echo "  AGENTS.md checked"

# Install scripts
echo "Installing scripts..."
mkdir -p "$HOME_DIR/scripts"
for script_dir in "$BUNDLE_DIR/scripts" "$BUNDLE_DIR/bundle/scripts"; do
    [[ -d "$script_dir" ]] || continue
    for script in "$script_dir"/*.py "$script_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        cp "$script" "$HOME_DIR/scripts/"
    done
done
chmod +x "$HOME_DIR/scripts/"*.sh 2>/dev/null || true
echo "  Scripts installed"

# Install Janus neural link (synthesizer + client) when present.
echo "Installing neural link (optional)..."
mkdir -p "$HOME_DIR/servers"
if [[ -d "$BUNDLE_DIR/servers/synthesizer" ]]; then
    ln -sfn "$BUNDLE_DIR/servers/synthesizer" "$HOME_DIR/servers/synthesizer"
    touch "$HOME_DIR/servers/__init__.py"
fi
if [[ -f "$BUNDLE_DIR/scripts/establish_neural_link.py" ]]; then
    ln -sfn "$BUNDLE_DIR/scripts/establish_neural_link.py" "$HOME_DIR/scripts/establish_neural_link.py"
fi
if [[ -f "$BUNDLE_DIR/apex-neural-link" ]]; then
    cp "$BUNDLE_DIR/apex-neural-link" "$BIN_DIR/apex-neural-link"
    chmod +x "$BIN_DIR/apex-neural-link"
fi

# Install tests as preserved local utilities.
echo "Installing tests..."
mkdir -p "$HOME_DIR/tests"
for test_file in "$BUNDLE_DIR"/tests/*.py; do
    [[ -f "$test_file" ]] || continue
    cp "$test_file" "$HOME_DIR/tests/"
done

# Verify the public dispatcher rather than inferring optional integrations.
echo ""
echo "=== VERIFICATION ==="
"$BIN_DIR/apex" help >/dev/null
printf 'Dispatcher: %s\n' "$BIN_DIR/apex"
TOOL_COUNT=$(find "$BIN_DIR" -maxdepth 1 -type f -name 'apex*' | wc -l | tr -d ' ')
CORE_COUNT=$(find "$CONFIG_DIR/core" -maxdepth 1 -type f -name '*.py' | wc -l | tr -d ' ')
SCRIPT_COUNT=$(find "$HOME_DIR/scripts" -maxdepth 1 -type f | wc -l | tr -d ' ')
printf 'CLI tools: %s\nCore modules: %s\nScripts: %s\n' "$TOOL_COUNT" "$CORE_COUNT" "$SCRIPT_COUNT"

echo ""
echo "=== INSTALL COMPLETE ==="
echo "Ensure ~/bin is on PATH, then run: apex help"
