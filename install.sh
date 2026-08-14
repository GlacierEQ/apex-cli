#!/usr/bin/env bash
# install.sh — APEX CLI installer
set -euo pipefail

HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
    echo "HOME is required for installation" >&2
    exit 78
fi

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME_DIR/bin"
CONFIG_DIR="$HOME_DIR/.apex"
MEMORY_DIR="$HOME_DIR/.local/share/mimocode/memory"
SKILL_DIR="$HOME_DIR/.agents/skills"
SCRIPT_DIR="$HOME_DIR/scripts"
PROJECTION_PACKAGE="$BUNDLE_DIR/bundle/runtime-projection"
PROJECTION_DIR="$CONFIG_DIR/runtime_projection"
PROJECTION_ARCHIVE="$CONFIG_DIR/runtime_projection.tar.gz"
CANONICAL_RUNTIME_COMMIT="1afda64498ddd90345231cdecec36cd85919a961"

echo "=== APEX CLI INSTALLER ==="
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$MEMORY_DIR" "$SKILL_DIR" "$SCRIPT_DIR"

# CLI dispatcher and repository-local tools.
if [[ -f "$BUNDLE_DIR/apex" ]]; then
    cp "$BUNDLE_DIR/apex" "$BIN_DIR/apex"
    chmod +x "$BIN_DIR/apex"
fi
for tool in "$BUNDLE_DIR"/apex-*; do
    [[ -f "$tool" ]] || continue
    cp "$tool" "$BIN_DIR/"
    chmod +x "$BIN_DIR/$(basename "$tool")"
done
[[ -x "$BIN_DIR/apex" ]] || { echo "APEX dispatcher installation failed" >&2; exit 1; }

# Core modules remain compatibility surfaces, not runtime authority.
mkdir -p "$CONFIG_DIR/core"
for module in "$BUNDLE_DIR"/core/*.py; do
    [[ -f "$module" ]] || continue
    cp "$module" "$CONFIG_DIR/core/"
done

# Nervous-system host config.
for runtime_file in MASTERSKILL_ACTIVATION.json startup.sh; do
    source_file="$BUNDLE_DIR/bundle/config/$runtime_file"
    [[ -f "$source_file" ]] || continue
    cp "$source_file" "$CONFIG_DIR/$runtime_file"
done
[[ -f "$CONFIG_DIR/startup.sh" ]] && chmod +x "$CONFIG_DIR/startup.sh"

# Operator instructions.
if [[ -f "$BUNDLE_DIR/bundle/config/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/bundle/config/AGENTS.md" "$HOME_DIR/AGENTS.md"
elif [[ -f "$BUNDLE_DIR/config/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/config/AGENTS.md" "$HOME_DIR/AGENTS.md"
elif [[ -f "$BUNDLE_DIR/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/AGENTS.md" "$HOME_DIR/AGENTS.md"
fi

# Baseline skills. Existing richer host projections win.
if [[ -d "$BUNDLE_DIR/bundle/skills" ]]; then
    for skill_source in "$BUNDLE_DIR"/bundle/skills/*; do
        [[ -d "$skill_source" ]] || continue
        skill_name="$(basename "$skill_source")"
        target="$SKILL_DIR/$skill_name"
        if [[ -f "$target/SKILL.md" ]]; then
            echo "preserving existing skill: $skill_name"
            continue
        fi
        mkdir -p "$target"
        cp -R "$skill_source"/. "$target"/
    done
fi

# Host adapter scripts.
for script_dir in "$BUNDLE_DIR/scripts" "$BUNDLE_DIR/bundle/scripts"; do
    [[ -d "$script_dir" ]] || continue
    for script in "$script_dir"/*.py "$script_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        cp "$script" "$SCRIPT_DIR/"
    done
done
chmod +x "$SCRIPT_DIR/"*.sh 2>/dev/null || true

# Install the exact checksum-bound Apex Boot Core runtime projection.
if [[ ! -f "$PROJECTION_PACKAGE/PACKAGE.json" ]]; then
    echo "Canonical runtime projection package missing" >&2
    exit 20
fi
python3 - "$PROJECTION_PACKAGE" "$PROJECTION_ARCHIVE" "$CANONICAL_RUNTIME_COMMIT" <<'PY'
import base64, hashlib, json, sys
from pathlib import Path
package_dir = Path(sys.argv[1])
out = Path(sys.argv[2])
expected_commit = sys.argv[3]
meta = json.loads((package_dir / "PACKAGE.json").read_text(encoding="utf-8"))
if meta.get("canonical_commit") != expected_commit:
    raise SystemExit("runtime projection package canonical commit drift")
encoded = "".join((package_dir / name).read_text(encoding="utf-8").strip() for name in meta["parts"])
if hashlib.sha256(encoded.encode()).hexdigest() != meta["base64_sha256"]:
    raise SystemExit("runtime projection base64 checksum mismatch")
payload = base64.b64decode(encoded, validate=True)
if hashlib.sha256(payload).hexdigest() != meta["archive_sha256"]:
    raise SystemExit("runtime projection archive checksum mismatch")
out.write_bytes(payload)
PY
rm -rf "$PROJECTION_DIR"
mkdir -p "$PROJECTION_DIR"
tar -xzf "$PROJECTION_ARCHIVE" -C "$PROJECTION_DIR"
rm -f "$PROJECTION_ARCHIVE"
python3 "$PROJECTION_DIR/scripts/verify_runtime_projection.py" \
    --root "$PROJECTION_DIR" \
    --expect-commit "$CANONICAL_RUNTIME_COMMIT" >/dev/null
python3 "$PROJECTION_DIR/scripts/runtime_cli.py" \
    --state-root "$CONFIG_DIR/runtime_state" \
    --contract-dir "$PROJECTION_DIR/runtime/contracts" \
    --canonical-commit "$CANONICAL_RUNTIME_COMMIT" \
    --compiler-path "$PROJECTION_DIR/runtime/compiler.py" \
    validate-contract >/dev/null

# Optional neural link and local tests are preserved.
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
mkdir -p "$HOME_DIR/tests"
for test_file in "$BUNDLE_DIR"/tests/*.py; do
    [[ -f "$test_file" ]] || continue
    cp "$test_file" "$HOME_DIR/tests/"
done

# Verification is executable: boot must reach a replay-attested canonical receipt.
for required in \
    "$CONFIG_DIR/MASTERSKILL_ACTIVATION.json" \
    "$CONFIG_DIR/startup.sh" \
    "$SCRIPT_DIR/dynamic_skill_activator.py" \
    "$SKILL_DIR/glaciereq-nervous-system/SKILL.md" \
    "$SKILL_DIR/apex-aspen-grove-bootup/SKILL.md" \
    "$SKILL_DIR/verification/SKILL.md" \
    "$PROJECTION_DIR/RUNTIME_PROJECTION.json" \
    "$PROJECTION_DIR/runtime/compiler.py" \
    "$PROJECTION_DIR/scripts/runtime_cli.py"
do
    [[ -e "$required" ]] || { echo "Runtime installation failed: missing $required" >&2; exit 21; }
done

"$BIN_DIR/apex" help >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" boot "install verification" >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" runtime-status >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" replay "$CONFIG_DIR/last_runtime_receipt.json" >/dev/null

printf 'Dispatcher: %s\n' "$BIN_DIR/apex"
printf 'Canonical runtime: %s @ %s\n' "GlacierEQ/apex-boot-core" "$CANONICAL_RUNTIME_COMMIT"
printf 'Projection: %s\n' "$PROJECTION_DIR/RUNTIME_PROJECTION.json"
printf 'Runtime receipt: %s\n' "$CONFIG_DIR/last_runtime_receipt.json"
echo "=== INSTALL COMPLETE ==="
echo "Ensure ~/bin is on PATH, then run: apex boot \"<objective>\""
