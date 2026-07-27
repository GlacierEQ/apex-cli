#!/usr/bin/env bash
# apex-ish-install.sh — iSH App (iPhone 16 Pro Max) Installer
set -euo pipefail

echo "=== APEX ISH IPHONE INSTALLER ==="

# Install dependencies if apk exists
if command -v apk >/dev/null 2>&1; then
    echo "Installing Alpine Linux dependencies..."
    apk update || true
    apk add python3 bash git || true
fi

BIN_DIR="$HOME/bin"
mkdir -p "$BIN_DIR" "$HOME/.apex"

echo "Installing APEX CLI tools to iSH ~/bin/..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR"/apex-* "$BIN_DIR/" 2>/dev/null || true
chmod +x "$BIN_DIR"/apex-* 2>/dev/null || true

PROFILE="$HOME/.profile"
if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$PROFILE" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$PROFILE"
fi

echo "✅ APEX CLI installed cleanly on iSH iPhone 16 Pro Max!"
echo "Run 'source ~/.profile' and test with: apex-openclaw navigate 'https://github.com/GlacierEQ/openclaw'"
