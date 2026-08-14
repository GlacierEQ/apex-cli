#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:-}"
[[ -n "$HOME_DIR" ]] || { echo "HOME is required for installation" >&2; exit 78; }
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME_DIR/bin"; CONFIG_DIR="$HOME_DIR/.apex"; SKILL_DIR="$HOME_DIR/.agents/skills"; SCRIPT_DIR="$HOME_DIR/scripts"
SEMANTICS="$BUNDLE_DIR/bundle/runtime-projection/CANONICAL_SEMANTICS.json"
PROJECTION_DIR="$CONFIG_DIR/runtime_projection"
ADAPTER_DIR="$BUNDLE_DIR/bundle/runtime-adapter"
CANONICAL_COMMIT="84a2907a316327e91dc0426f5407a34908aa4fc4"
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$SKILL_DIR" "$SCRIPT_DIR" "$HOME_DIR/.local/share/mimocode/memory"

# Public dispatcher and local tools.
cp "$BUNDLE_DIR/apex" "$BIN_DIR/apex"; chmod +x "$BIN_DIR/apex"
for tool in "$BUNDLE_DIR"/apex-*; do [[ -f "$tool" ]] || continue; cp "$tool" "$BIN_DIR/"; chmod +x "$BIN_DIR/$(basename "$tool")"; done
mkdir -p "$CONFIG_DIR/core"
for module in "$BUNDLE_DIR"/core/*.py; do [[ -f "$module" ]] || continue; cp "$module" "$CONFIG_DIR/core/"; done

# Host activation/startup config.
for f in MASTERSKILL_ACTIVATION.json startup.sh; do [[ -f "$BUNDLE_DIR/bundle/config/$f" ]] && cp "$BUNDLE_DIR/bundle/config/$f" "$CONFIG_DIR/$f"; done
chmod +x "$CONFIG_DIR/startup.sh"
[[ -f "$BUNDLE_DIR/bundle/config/AGENTS.md" ]] && cp "$BUNDLE_DIR/bundle/config/AGENTS.md" "$HOME_DIR/AGENTS.md"

# Baseline skill projections. Preserve richer existing copies.
for source in "$BUNDLE_DIR"/bundle/skills/*; do
  [[ -d "$source" ]] || continue
  name="$(basename "$source")"; target="$SKILL_DIR/$name"
  [[ -f "$target/SKILL.md" ]] && continue
  mkdir -p "$target"; cp -R "$source"/. "$target"/
done

# Host composition adapter.
for d in "$BUNDLE_DIR/scripts" "$BUNDLE_DIR/bundle/scripts"; do
  [[ -d "$d" ]] || continue
  for s in "$d"/*.py "$d"/*.sh; do [[ -f "$s" ]] || continue; cp "$s" "$SCRIPT_DIR/"; done
done

# Reconstruct only canonical semantics from transparent source fragments.
rm -rf "$PROJECTION_DIR"; mkdir -p "$PROJECTION_DIR/scripts"
python3 - "$SEMANTICS" "$PROJECTION_DIR" "$CANONICAL_COMMIT" <<'PY'
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
manifest_path=Path(sys.argv[1]); dest=Path(sys.argv[2]); commit=sys.argv[3]
meta=json.loads(manifest_path.read_text())
if meta.get('canonical_repository')!='GlacierEQ/apex-boot-core': raise SystemExit('canonical repository drift')
if meta.get('canonical_commit')!=commit: raise SystemExit('canonical commit drift')
parts=[]
for item in meta['parts']:
    path=manifest_path.parent/item['name']; data=path.read_bytes()
    git_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if git_sha!=item['git_blob_sha1']: raise SystemExit(f"fragment drift: {item['name']}")
    parts.append(data)
bundle=b''.join(parts); expected=meta['files']; found={}; pos=0
prefix=b'<<<GLACIEREQ_FILE '
while pos < len(bundle) and set(found)!=set(expected):
    if not bundle.startswith(prefix,pos): raise SystemExit(f'bad source boundary at {pos}')
    end=bundle.index(b'\n',pos); header=bundle[pos+len(prefix):end-3].decode('utf-8'); rel,size_s=header.rsplit(' ',1); size=int(size_s); start=end+1; payload=bundle[start:start+size]
    if len(payload)!=size: raise SystemExit(f'truncated source: {rel}')
    if rel in expected:
        actual=hashlib.sha256(payload).hexdigest()
        if actual!=expected[rel]: raise SystemExit(f'canonical checksum mismatch: {rel}')
        target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload); found[rel]=actual
    pos=start+size
missing=set(expected)-set(found)
if missing: raise SystemExit('missing canonical semantics: '+','.join(sorted(missing)))
projection={'schema':'glaciereq.runtime-projection.v2','canonical_repository':meta['canonical_repository'],'canonical_commit':commit,'files':expected,'generated_at':datetime.now(timezone.utc).isoformat(),'projection_law':'Canonical semantic bytes verified from transparent public mirror; invocation scripts are host adapters.'}
(dest/'RUNTIME_PROJECTION.json').write_text(json.dumps(projection,indent=2,sort_keys=True)+'\n')
PY

# Public invocation/verifier adapters. They do not redefine runtime semantics.
cp "$ADAPTER_DIR/runtime_cli.py" "$PROJECTION_DIR/scripts/runtime_cli.py"
cp "$ADAPTER_DIR/verify_projection.py" "$PROJECTION_DIR/scripts/verify_runtime_projection.py"
chmod +x "$PROJECTION_DIR/scripts/"*.py

python3 "$PROJECTION_DIR/scripts/verify_runtime_projection.py" --root "$PROJECTION_DIR" --expect-commit "$CANONICAL_COMMIT" >/dev/null
python3 "$PROJECTION_DIR/scripts/runtime_cli.py" --state-root "$CONFIG_DIR/runtime_state" --contract-dir "$PROJECTION_DIR/runtime/contracts" --canonical-commit "$CANONICAL_COMMIT" --compiler-path "$PROJECTION_DIR/runtime/compiler.py" validate-contract >/dev/null

# Executable acceptance: boot, canonical receipt, replay.
HOME="$HOME_DIR" "$BIN_DIR/apex" help >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" boot "install verification" >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" runtime-status >/dev/null
HOME="$HOME_DIR" "$BIN_DIR/apex" replay "$CONFIG_DIR/last_runtime_receipt.json" >/dev/null

echo "APEX runtime install VERIFIED canonical=$CANONICAL_COMMIT receipt=$CONFIG_DIR/last_runtime_receipt.json"
