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
PROJECTION_PACKAGE="$BUNDLE_DIR/bundle/runtime-projection/PACKAGE.json"
PROJECTION_DIR="$CONFIG_DIR/runtime_projection"
CANONICAL_RUNTIME_COMMIT="84a2907a316327e91dc0426f5407a34908aa4fc4"

echo "=== APEX CLI INSTALLER ==="
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$MEMORY_DIR" "$SKILL_DIR" "$SCRIPT_DIR"

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

mkdir -p "$CONFIG_DIR/core"
for module in "$BUNDLE_DIR"/core/*.py; do
    [[ -f "$module" ]] || continue
    cp "$module" "$CONFIG_DIR/core/"
done

for runtime_file in MASTERSKILL_ACTIVATION.json startup.sh; do
    source_file="$BUNDLE_DIR/bundle/config/$runtime_file"
    [[ -f "$source_file" ]] || continue
    cp "$source_file" "$CONFIG_DIR/$runtime_file"
done
[[ -f "$CONFIG_DIR/startup.sh" ]] && chmod +x "$CONFIG_DIR/startup.sh"

if [[ -f "$BUNDLE_DIR/bundle/config/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/bundle/config/AGENTS.md" "$HOME_DIR/AGENTS.md"
elif [[ -f "$BUNDLE_DIR/config/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/config/AGENTS.md" "$HOME_DIR/AGENTS.md"
elif [[ -f "$BUNDLE_DIR/AGENTS.md" ]]; then
    cp "$BUNDLE_DIR/AGENTS.md" "$HOME_DIR/AGENTS.md"
fi

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

for script_dir in "$BUNDLE_DIR/scripts" "$BUNDLE_DIR/bundle/scripts"; do
    [[ -d "$script_dir" ]] || continue
    for script in "$script_dir"/*.py "$script_dir"/*.sh; do
        [[ -f "$script" ]] || continue
        cp "$script" "$SCRIPT_DIR/"
    done
done
chmod +x "$SCRIPT_DIR/"*.sh 2>/dev/null || true

# Transparent canonical distribution: download only the exact pinned Apex Boot
# Core source files and reject any byte that does not match PACKAGE.json.
[[ -f "$PROJECTION_PACKAGE" ]] || { echo "Canonical runtime package manifest missing" >&2; exit 20; }
rm -rf "$PROJECTION_DIR"
mkdir -p "$PROJECTION_DIR"
python3 - "$PROJECTION_PACKAGE" "$PROJECTION_DIR" "$CANONICAL_RUNTIME_COMMIT" <<'PY'
import hashlib, json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

package_path = Path(sys.argv[1])
dest = Path(sys.argv[2])
expected_commit = sys.argv[3]
meta = json.loads(package_path.read_text(encoding="utf-8"))
if meta.get("canonical_repository") != "GlacierEQ/apex-boot-core":
    raise SystemExit("canonical repository drift")
if meta.get("canonical_commit") != expected_commit:
    raise SystemExit("canonical commit drift")
raw_base = meta.get("raw_base", "")
expected_prefix = f"https://raw.githubusercontent.com/GlacierEQ/apex-boot-core/{expected_commit}/"
if raw_base != expected_prefix:
    raise SystemExit("raw source base is not pinned to canonical commit")
for rel, expected_hash in meta.get("files", {}).items():
    target = dest / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(raw_base + rel, timeout=30) as response:
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_hash:
        raise SystemExit(f"checksum mismatch: {rel} expected={expected_hash} actual={actual}")
    target.write_bytes(payload)
projection = {
    "schema": "glaciereq.runtime-projection.v2",
    "canonical_repository": meta["canonical_repository"],
    "canonical_commit": meta["canonical_commit"],
    "files": meta["files"],
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "projection_law": "Downloaded from exact canonical commit and SHA-256 verified at install time."
}
(dest / "RUNTIME_PROJECTION.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

python3 "$PROJECTION_DIR/scripts/verify_runtime_projection.py" --root "$PROJECTION_DIR" --expect-commit "$CANONICAL_RUNTIME_COMMIT" >/dev/null
python3 "$PROJECTION_DIR/scripts/runtime_cli.py" \
    --state-root "$CONFIG_DIR/runtime_state" \
    --contract-dir "$PROJECTION_DIR/runtime/contracts" \
    --canonical-commit "$CANONICAL_RUNTIME_COMMIT" \
    --compiler-path "$PROJECTION_DIR/runtime/compiler.py" \
    validate-contract >/dev/null

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

for required in \
    "$CONFIG_DIR/MASTERSKILL_ACTIVATION.json" \
    "$CONFIG_DIR/startup.sh" \
    "$SCRIPT_DIR/dynamic_skill_activator.py" \
    "$SKILL_DIR/glaciereq-nervous-system/SKILL.md" \
    "$SKILL_DIR/apex-aspen-grove-bootup/SKILL.md" \
    "$SKILL_DIR/verification/SKILL.md" \
    "$PROJECTION_DIR/RUNTIME_PROJECTION.json" \
    "$PROJECTION_DIR/runtime/compiler.py" \
    "$PROJECTION_DIR/runtime/hardening.py" \
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
