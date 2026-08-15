#!/usr/bin/env python3
"""Fail-closed truth checks for the bounded APEX CLI runtime surface."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUNTIME_COMMIT = "84a2907a316327e91dc0426f5407a34908aa4fc4"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"PUBLIC_TRUTH_FAIL: {message}")


def main() -> None:
    caps = json.loads((ROOT / "machine/capabilities.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "machine/excellence-state.json").read_text(encoding="utf-8"))

    allowed = {
        "repository-local-bash-command-dispatch",
        "pinned-sha256-canonical-runtime-projection",
        "fresh-install-canonical-runtime-bootstrap-and-status",
        "runtime-receipt-replay-and-attestation",
        "resumable-lifecycle-cursor",
        "idempotent-action-journal",
        "capability-ttl-and-eligibility-evaluation",
        "resource-governor-denial-and-provider-quota-state",
        "runtime-health-readback",
        "composition-receipt-separation",
    }
    require(set(caps.get("capabilities", [])) == allowed, "capability allowlist drift")
    authority = caps.get("canonical_runtime_authority", {})
    require(authority.get("repository") == "GlacierEQ/apex-boot-core", "canonical runtime repository drift")
    require(authority.get("commit") == CANONICAL_RUNTIME_COMMIT, "canonical runtime commit drift")
    require(caps.get("operational_authority") is False, "operational authority must be false")
    require(caps.get("external_job_app_checkout_bundled") is False, "external job-app checkout must remain a nonclaim")
    require(caps.get("casebuilder_or_red_helix_bundled") is False, "Casebuilder/Red Helix must remain a nonclaim")
    require(caps.get("dropbox_or_device_runtime_proven") is False, "Dropbox/device runtime must remain a nonclaim")
    require(caps.get("live_mcp_apex_mesh_integration_claim") is False, "live mesh integration must remain a nonclaim")
    require(caps.get("performance_or_scale_claim") is False, "performance/scale authority must remain a nonclaim")

    require(state.get("repository") == "GlacierEQ/apex-cli", "excellence repository identity drift")
    require("specialist component" in state.get("role", ""), "specialist role missing")
    state_authority = state.get("canonical_runtime_authority", {})
    require(state_authority.get("repository") == "GlacierEQ/apex-boot-core", "state canonical repository drift")
    require(state_authority.get("commit") == CANONICAL_RUNTIME_COMMIT, "state canonical commit drift")
    gates = state.get("gates", {})
    for gate in (
        "problem_verified",
        "unique_value_known",
        "canonical_identity_known",
        "security_authority_bounded",
        "reusable_capabilities_extracted",
        "evolution_cursor_defined",
    ):
        require(str(gates.get(gate, "")).startswith("PASS"), f"required excellence gate not passed: {gate}")
    require("PENDING_CURRENT_HEAD" in str(gates.get("deterministic_tests_pass", "")), "current-head deterministic proof must remain explicit until exact-head execution")
    require("PENDING_CURRENT_HEAD" in str(gates.get("adversarial_tests_pass", "")), "current-head adversarial proof must remain explicit until exact-head execution")
    require(state.get("rollback"), "rollback path missing")
    require(state.get("next_cursor"), "evolution cursor missing")

    print("PUBLIC_TRUTH_PASS")


if __name__ == "__main__":
    main()
