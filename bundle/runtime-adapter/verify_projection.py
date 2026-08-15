#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def h(path: Path) -> str:
    x=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): x.update(chunk)
    return x.hexdigest()

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--root',required=True); p.add_argument('--expect-commit'); a=p.parse_args()
    root=Path(a.root).resolve(); mf=root/'RUNTIME_PROJECTION.json'; errors=[]
    if not mf.is_file(): errors.append(f'missing {mf}'); data={}
    else: data=json.loads(mf.read_text())
    if data.get('schema')!='glaciereq.runtime-projection.v2': errors.append('projection schema drift')
    if data.get('canonical_repository')!='GlacierEQ/apex-boot-core': errors.append('canonical repository drift')
    if a.expect_commit and data.get('canonical_commit')!=a.expect_commit: errors.append('canonical commit drift')
    for rel,expected in data.get('files',{}).items():
        path=root/rel
        if not path.is_file(): errors.append(f'missing projected file: {rel}'); continue
        actual=h(path)
        if actual!=expected: errors.append(f'checksum drift: {rel}')
    print(json.dumps({'schema':'glaciereq.runtime-projection-verification.v2','status':'VERIFIED' if not errors else 'FAILED','canonical_commit':data.get('canonical_commit'),'files_checked':len(data.get('files',{})),'errors':errors},indent=2,sort_keys=True))
    return 1 if errors else 0

if __name__=='__main__': raise SystemExit(main())
