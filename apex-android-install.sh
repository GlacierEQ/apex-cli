#!/usr/bin/env bash
# apex-android-install.sh — Termux (Android Pixel Tablet) Installer
set -euo pipefail

echo "=== APEX TERMUX ANDROID INSTALLER ==="

# Install dependencies if pkg exists
if command -v pkg >/dev/null 2>&1; then
    echo "Updating Termux packages..."
    pkg update -y || true
    pkg install -y python git bash || true
fi

BIN_DIR="$HOME/bin"
mkdir -p "$BIN_DIR" "$HOME/.apex"

echo "Installing APEX CLI tools to Termux ~/bin/..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR"/apex-* "$BIN_DIR/" 2>/dev/null || true
chmod +x "$BIN_DIR"/apex-* 2>/dev/null || true

# Add to bashrc if not present
BASHRC="$HOME/.bashrc"
if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$BASHRC" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$BASHRC"
fi

echo "✅ APEX CLI installed cleanly on Termux Android!"
echo "Run 'source ~/.bashrc' and test with: apex-openclaw navigate 'https://github.com/GlacierEQ/openclaw'"
