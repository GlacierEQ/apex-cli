#!/usr/bin/env bash
set -euo pipefail
HOME_DIR="${HOME:-}"; [[ -n "$HOME_DIR" ]] || { echo "HOME is required for installation" >&2; exit 78; }
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"; BIN_DIR="$HOME_DIR/bin"; CONFIG_DIR="$HOME_DIR/.apex"; SKILL_DIR="$HOME_DIR/.agents/skills"; SCRIPT_DIR="$HOME_DIR/scripts"; SEMANTICS="$BUNDLE_DIR/bundle/runtime-projection/CANONICAL_SEMANTICS.json"; PROJECTION_DIR="$CONFIG_DIR/runtime_projection"; ADAPTER_DIR="$BUNDLE_DIR/bundle/runtime-adapter"; CANONICAL_COMMIT="84a2907a316327e91dc0426f5407a34908aa4fc4"
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$SKILL_DIR" "$SCRIPT_DIR" "$HOME_DIR/.local/share/mimocode/memory"; cp "$BUNDLE_DIR/apex" "$BIN_DIR/apex"; chmod +x "$BIN_DIR/apex"
for tool in "$BUNDLE_DIR"/apex-*; do [[ -f "$tool" ]] || continue; cp "$tool" "$BIN_DIR/"; chmod +x "$BIN_DIR/$(basename "$tool")"; done
mkdir -p "$CONFIG_DIR/core"; for module in "$BUNDLE_DIR"/core/*.py; do [[ -f "$module" ]] || continue; cp "$module" "$CONFIG_DIR/core/"; done
for f in MASTERSKILL_ACTIVATION.json startup.sh; do [[ -f "$BUNDLE_DIR/bundle/config/$f" ]] && cp "$BUNDLE_DIR/bundle/config/$f" "$CONFIG_DIR/$f"; done; chmod +x "$CONFIG_DIR/startup.sh"; [[ -f "$BUNDLE_DIR/bundle/config/AGENTS.md" ]] && cp "$BUNDLE_DIR/bundle/config/AGENTS.md" "$HOME_DIR/AGENTS.md"
for source in "$BUNDLE_DIR"/bundle/skills/*; do [[ -d "$source" ]] || continue; name="$(basename "$source")"; target="$SKILL_DIR/$name"; [[ -f "$target/SKILL.md" ]] && continue; mkdir -p "$target"; cp -R "$source"/. "$target"/; done
for d in "$BUNDLE_DIR/scripts" "$BUNDLE_DIR/bundle/scripts"; do [[ -d "$d" ]] || continue; for s in "$d"/*.py "$d"/*.sh; do [[ -f "$s" ]] || continue; cp "$s" "$SCRIPT_DIR/"; done; done
PROJECTION_STAGE="$(mktemp -d "$CONFIG_DIR/.runtime_projection.stage.XXXXXX")"
PROJECTION_BACKUP="$CONFIG_DIR/.runtime_projection.backup.$$"
cleanup_projection_stage() { rm -rf "$PROJECTION_STAGE"; }
trap cleanup_projection_stage EXIT
mkdir -p "$PROJECTION_STAGE/scripts"
python3 - "$SEMANTICS" "$PROJECTION_STAGE" "$CANONICAL_COMMIT" <<'PY'
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
manifest_path=Path(sys.argv[1]); dest=Path(sys.argv[2]); commit=sys.argv[3]; meta=json.loads(manifest_path.read_text())
if meta.get('canonical_repository')!='GlacierEQ/apex-boot-core': raise SystemExit('canonical repository drift')
if meta.get('canonical_commit')!=commit: raise SystemExit('canonical commit drift')
bundle=b''.join((manifest_path.parent/item['name']).read_bytes() for item in meta['parts']); expected=meta['files']; candidates={name:[] for name in expected}; prefix=b'<<<GLACIEREQ_FILE '; pos=0
while True:
    pos=bundle.find(prefix,pos)
    if pos<0: break
    try:
        end=bundle.index(b'\n',pos); header=bundle[pos+len(prefix):end-3].decode('utf-8'); rel,size_s=header.rsplit(' ',1); size=int(size_s); start=end+1; payload=bundle[start:start+size]
    except (ValueError,UnicodeDecodeError): pos+=len(prefix); continue
    if len(payload)==size and rel in expected and hashlib.sha256(payload).hexdigest()==expected[rel]: candidates[rel].append(payload)
    pos=start+max(size,1)
for rel,digest in expected.items():
    matches=candidates[rel]
    if len(matches)!=1: raise SystemExit(f'canonical payload cardinality mismatch: {rel} matches={len(matches)}')
    target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(matches[0])
projection={'schema':'glaciereq.runtime-projection.v2','canonical_repository':meta['canonical_repository'],'canonical_commit':commit,'files':expected,'generated_at':datetime.now(timezone.utc).isoformat(),'projection_law':'Only the unique payload matching each pinned canonical SHA-256 is materialized; transport framing and nonmatching historical records have no authority.'}; (dest/'RUNTIME_PROJECTION.json').write_text(json.dumps(projection,indent=2,sort_keys=True)+'\n')
PY
cp "$ADAPTER_DIR/runtime_cli.py" "$PROJECTION_STAGE/scripts/runtime_cli.py"; cp "$ADAPTER_DIR/verify_projection.py" "$PROJECTION_STAGE/scripts/verify_runtime_projection.py"; chmod +x "$PROJECTION_STAGE/scripts/"*.py
python3 "$PROJECTION_STAGE/scripts/verify_runtime_projection.py" --root "$PROJECTION_STAGE" --expect-commit "$CANONICAL_COMMIT" >/dev/null
python3 "$PROJECTION_STAGE/scripts/runtime_cli.py" --state-root "$CONFIG_DIR/runtime_state" --contract-dir "$PROJECTION_STAGE/runtime/contracts" --canonical-commit "$CANONICAL_COMMIT" --compiler-path "$PROJECTION_STAGE/runtime/compiler.py" validate-contract >/dev/null
rm -rf "$PROJECTION_BACKUP"
if [[ -d "$PROJECTION_DIR" ]]; then mv "$PROJECTION_DIR" "$PROJECTION_BACKUP"; fi
mv "$PROJECTION_STAGE" "$PROJECTION_DIR"
PROJECTION_STAGE="$CONFIG_DIR/.runtime_projection.stage.consumed.$$"
if ! { HOME="$HOME_DIR" "$BIN_DIR/apex" help >/dev/null && HOME="$HOME_DIR" "$BIN_DIR/apex" boot "install verification" >/dev/null && HOME="$HOME_DIR" "$BIN_DIR/apex" runtime-status >/dev/null && HOME="$HOME_DIR" "$BIN_DIR/apex" replay "$CONFIG_DIR/last_runtime_receipt.json" >/dev/null; }; then
  rm -rf "$PROJECTION_DIR"
  if [[ -d "$PROJECTION_BACKUP" ]]; then mv "$PROJECTION_BACKUP" "$PROJECTION_DIR"; fi
  echo "APEX runtime acceptance failed; previous projection restored" >&2
  exit 1
fi
rm -rf "$PROJECTION_BACKUP"
trap - EXIT
echo "APEX runtime install VERIFIED canonical=$CANONICAL_COMMIT receipt=$CONFIG_DIR/last_runtime_receipt.json"
