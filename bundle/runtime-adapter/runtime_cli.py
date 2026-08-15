#!/usr/bin/env python3
"""Public host adapter for the Apex Boot Core runtime semantics."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.compiler import ActionJournal, CapabilityPlane, LifecycleEngine, MetricsRecorder, RuntimePaths, read_json, validate_contracts
from runtime.hardening import AttestedReceiptManager, CapabilityInventory, ContractFallbackGraph, EconomicResourceGovernor, RuntimeHealthV2


def emit(value, code=0):
    print(json.dumps(value, indent=2, sort_keys=True))
    raise SystemExit(code)


def j(value, default):
    if value is None:
        return default
    path = Path(value)
    try:
        is_file = path.is_file()
    except OSError:
        is_file = False
    return json.loads(path.read_text(encoding="utf-8")) if is_file else json.loads(value)


def parser():
    p = argparse.ArgumentParser(prog="apex-runtime")
    p.add_argument("--state-root", default=os.getenv("APEX_RUNTIME_STATE_ROOT", "~/.apex/runtime_state"))
    p.add_argument("--contract-dir", default=os.getenv("APEX_RUNTIME_CONTRACT_DIR", str(ROOT / "runtime/contracts")))
    p.add_argument("--canonical-commit", default=os.getenv("APEX_RUNTIME_CANONICAL_COMMIT", "UNPINNED"))
    p.add_argument("--compiler-path", default=os.getenv("APEX_RUNTIME_COMPILER", str(ROOT / "runtime/compiler.py")))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate-contract")
    q=sub.add_parser("start"); q.add_argument("objective"); q.add_argument("--run-id"); q.add_argument("--metadata-json"); q.add_argument("--predicates-json")
    q=sub.add_parser("checkpoint"); q.add_argument("run_id"); q.add_argument("--stage"); q.add_argument("--complete-stage"); q.add_argument("--cursor-json"); q.add_argument("--dependencies-json")
    q=sub.add_parser("advance"); q.add_argument("run_id"); q.add_argument("--cursor-json"); q.add_argument("--dependencies-json")
    q=sub.add_parser("finalize"); q.add_argument("run_id"); q.add_argument("status", choices=["READY","DEGRADED","BLOCKED","FAILED"])
    q=sub.add_parser("resume"); q.add_argument("target")
    q=sub.add_parser("receipt"); q.add_argument("run_id"); q.add_argument("status", choices=["READY","DEGRADED","BLOCKED","FAILED"]); q.add_argument("--activation"); q.add_argument("--skills-json"); q.add_argument("--predicates-json"); q.add_argument("--blockers-json"); q.add_argument("--continuation-json")
    q=sub.add_parser("replay"); q.add_argument("receipt")
    q=sub.add_parser("capability-register"); q.add_argument("capability_id"); q.add_argument("kind"); q.add_argument("provider"); q.add_argument("--ttl",type=int,default=900); q.add_argument("--scopes",default=""); q.add_argument("--endpoint-ref"); q.add_argument("--metadata-json")
    q=sub.add_parser("capability-probe"); q.add_argument("capability_id"); [q.add_argument(f"--{x}",action="store_true") for x in ("connected","authenticated","authorized","invokable","verified")]; q.add_argument("--latency-ms",type=float); q.add_argument("--error"); q.add_argument("--metadata-json")
    q=sub.add_parser("capability-import"); q.add_argument("--inventory-json",required=True)
    q=sub.add_parser("capabilities"); q.add_argument("--kind"); q.add_argument("--provider"); q.add_argument("--minimum-state",default="DISCOVERED"); q.add_argument("--eligible-only",action="store_true")
    q=sub.add_parser("fallback"); q.add_argument("source"); q.add_argument("--graph",required=True); q.add_argument("--action",default="read"); q.add_argument("--requires-persistence",action="store_true"); q.add_argument("--minimum-state",default="VERIFIED"); q.add_argument("--no-degraded",action="store_true")
    q=sub.add_parser("action-begin"); q.add_argument("run_id"); q.add_argument("action"); q.add_argument("target"); q.add_argument("idempotency_key"); q.add_argument("--precondition-hash"); q.add_argument("--compensation-pointer"); q.add_argument("--provider"); q.add_argument("--metadata-json")
    q=sub.add_parser("action-complete"); q.add_argument("operation_id"); q.add_argument("--result-json"); q.add_argument("--readback-json"); q.add_argument("--postcondition-hash")
    q=sub.add_parser("action-fail"); q.add_argument("operation_id"); q.add_argument("error"); q.add_argument("--retryable",action="store_true"); q.add_argument("--retry-after",type=int)
    q=sub.add_parser("action-retry"); q.add_argument("operation_id"); q.add_argument("--reconciliation-json",required=True)
    q=sub.add_parser("governor-acquire"); q.add_argument("provider"); q.add_argument("operation"); q.add_argument("--run-id"); q.add_argument("--estimated-tokens",type=int,default=0); q.add_argument("--estimated-context-tokens",type=int,default=0); q.add_argument("--attempt",type=int,default=1); q.add_argument("--priority",type=int,default=0); q.add_argument("--config-json")
    q=sub.add_parser("governor-release"); q.add_argument("lease_id"); q.add_argument("--actual-tokens",type=int); q.add_argument("--actual-context-tokens",type=int); q.add_argument("--config-json")
    q=sub.add_parser("governor-backoff"); q.add_argument("provider"); q.add_argument("retry_after",type=int); q.add_argument("--quota-remaining",type=int); q.add_argument("--reason",default="rate_limit"); q.add_argument("--config-json")
    q=sub.add_parser("governor-provider-state"); q.add_argument("provider"); q.add_argument("--quota-remaining",type=int); q.add_argument("--reset-after",type=int); q.add_argument("--metadata-json"); q.add_argument("--config-json")
    q=sub.add_parser("governor-status"); q.add_argument("--config-json")
    q=sub.add_parser("metric"); q.add_argument("name"); q.add_argument("value",type=float); q.add_argument("--labels-json")
    q=sub.add_parser("health"); q.add_argument("--slo", default=str(ROOT / "runtime/contracts/slo.json"))
    return p


def manager(a, paths):
    return AttestedReceiptManager(paths, contract_dir=Path(a.contract_dir), canonical_commit=a.canonical_commit, compiler_path=Path(a.compiler_path))


def main():
    a=parser().parse_args(); paths=RuntimePaths(Path(a.state_root).expanduser()); cmd=a.cmd
    if cmd=="validate-contract":
        errors=validate_contracts(a.contract_dir); emit({"schema":"glaciereq.runtime-contract-validation.v2","status":"VERIFIED" if not errors else "FAILED","errors":errors},1 if errors else 0)
    if cmd=="start": emit(LifecycleEngine(paths).start(a.objective,run_id=a.run_id,metadata=j(a.metadata_json,{}),source_predicates=j(a.predicates_json,[])))
    if cmd=="checkpoint": emit(LifecycleEngine(paths).checkpoint(a.run_id,current_stage=a.stage,completed_stage=a.complete_stage,continuation_cursor=j(a.cursor_json,None),outstanding_dependencies=j(a.dependencies_json,None)))
    if cmd=="advance": emit(LifecycleEngine(paths).advance(a.run_id,cursor=j(a.cursor_json,None),dependencies=j(a.dependencies_json,None)))
    if cmd=="finalize": emit(LifecycleEngine(paths).finalize(a.run_id,a.status))
    if cmd=="resume":
        target=Path(a.target).expanduser(); emit(manager(a,paths).resume_from_receipt(target) if target.is_file() else LifecycleEngine(paths).resume(a.target))
    if cmd=="receipt": emit(manager(a,paths).create(a.run_id,status=a.status,activation_path=a.activation,skills=j(a.skills_json,[]),source_predicates=j(a.predicates_json,None),blockers=j(a.blockers_json,[]),continuation=j(a.continuation_json,None)))
    if cmd=="replay":
        result=manager(a,paths).replay(Path(a.receipt).expanduser()); emit(result,0 if result["status"]=="VERIFIED" else 2)
    if cmd=="capability-register": emit(CapabilityPlane(paths).register(a.capability_id,a.kind,a.provider,ttl_seconds=a.ttl,authorization_scopes=[x for x in a.scopes.split(",") if x],endpoint_ref=a.endpoint_ref,metadata=j(a.metadata_json,{})).to_dict())
    if cmd=="capability-probe": emit(CapabilityPlane(paths).record_probe(a.capability_id,{x:getattr(a,x) for x in ("connected","authenticated","authorized","invokable","verified")},latency_ms=a.latency_ms,error=a.error,metadata=j(a.metadata_json,{})).to_dict())
    if cmd=="capability-import": emit(CapabilityInventory(CapabilityPlane(paths)).import_inventory(j(a.inventory_json,{"capabilities":[]})))
    if cmd=="capabilities":
        plane=CapabilityPlane(paths); emit({"schema":"glaciereq.capability-selection.v2","capabilities":[x.to_dict() for x in plane.select(kind=a.kind,provider=a.provider,minimum_state=a.minimum_state)]} if a.eligible_only else plane.snapshot())
    if cmd=="fallback":
        edge=ContractFallbackGraph.from_path(CapabilityPlane(paths),Path(a.graph)).choose(a.source,action=a.action,requires_persistence=a.requires_persistence,minimum_state=a.minimum_state,allow_degraded=not a.no_degraded); emit({"schema":"glaciereq.fallback-selection.v2","source":a.source,"selected":edge},0 if edge else 3)
    journal=ActionJournal(paths)
    if cmd=="action-begin": emit(journal.begin(run_id=a.run_id,action=a.action,target_identity=a.target,idempotency_key=a.idempotency_key,precondition_hash=a.precondition_hash,compensation_pointer=a.compensation_pointer,provider=a.provider,metadata=j(a.metadata_json,{})))
    if cmd=="action-complete": emit(journal.complete(a.operation_id,result=j(a.result_json,{}),readback=j(a.readback_json,{}),postcondition_hash=a.postcondition_hash))
    if cmd=="action-fail": emit(journal.fail(a.operation_id,error=a.error,retryable=a.retryable,retry_after_seconds=a.retry_after))
    if cmd=="action-retry": emit(journal.retry(a.operation_id,reconciliation=j(a.reconciliation_json,{})))
    if cmd.startswith("governor-"):
        gov=EconomicResourceGovernor(paths,j(getattr(a,"config_json",None),{}))
        if cmd=="governor-acquire": emit(gov.acquire(provider=a.provider,operation=a.operation,estimated_tokens=a.estimated_tokens,estimated_context_tokens=a.estimated_context_tokens,priority=a.priority,run_id=a.run_id,attempt=a.attempt))
        if cmd=="governor-release": emit({"released":gov.release(a.lease_id,actual_tokens=a.actual_tokens,actual_context_tokens=a.actual_context_tokens)})
        if cmd=="governor-backoff": gov.record_provider_backoff(a.provider,a.retry_after,quota_remaining=a.quota_remaining,reason=a.reason); emit(gov.snapshot())
        if cmd=="governor-provider-state": gov.record_provider_state(a.provider,quota_remaining=a.quota_remaining,reset_after_seconds=a.reset_after,metadata=j(a.metadata_json,{})); emit(gov.snapshot())
        if cmd=="governor-status": emit(gov.snapshot())
    if cmd=="metric": MetricsRecorder(paths).record(a.name,a.value,j(a.labels_json,{})); emit({"recorded":True,"name":a.name,"value":a.value})
    if cmd=="health": emit(RuntimeHealthV2(paths,read_json(Path(a.slo),{})).report())

if __name__=="__main__": main()
