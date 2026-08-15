#!/usr/bin/env python3
"""Fail-closed truth checks for the bounded APEX CLI surface."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"PUBLIC_TRUTH_FAIL: {message}")


def main() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    normalized = readme.replace("**", "").replace("`", "")
    caps = json.loads((ROOT / "machine/capabilities.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "machine/excellence-state.json").read_text(encoding="utf-8"))

    require(
        "bounded Bash command dispatcher" in normalized,
        "bounded dispatcher identity missing",
    )
    require(
        "fail-closed at dependency boundaries" in normalized,
        "fail-closed dependency boundary missing",
    )
    require(
        "does not prove" in normalized,
        "external-system nonclaim missing",
    )
    require(
        "external integration harness" in normalized,
        "explicit external harness boundary missing",
    )

    allowed = {
        "repository-local-bash-command-dispatch",
        "fail-closed-external-job-app-dependency-resolution",
        "environment-controlled-local-path-resolution",
        "fresh-install-bundled-runtime-bootstrap-and-status",
        "explicit-external-casebuild-harness-boundary",
    }
    require(set(caps.get("capabilities", [])) == allowed, "capability allowlist drift")
    require(caps.get("operational_authority") is False, "operational authority must be false")
    require(
        caps.get("external_job_app_checkout_bundled") is False,
        "external job-app checkout must not be claimed bundled",
    )
    require(
        caps.get("casebuilder_or_red_helix_bundled") is False,
        "Casebuilder/Red Helix must not be claimed bundled",
    )
    require(
        caps.get("dropbox_or_device_runtime_proven") is False,
        "Dropbox/device runtime must not be claimed proven",
    )
    require(
        caps.get("live_mcp_apex_mesh_integration_claim") is False,
        "live mesh integration must remain a nonclaim",
    )

    require(state.get("principal_state") == "FUNCTIONAL_CANDIDATE", "machine state drift")
    require(state.get("operational_authority") is False, "machine state grants authority")
    require(
        state.get("gates", {}).get("LEGACY_DEBT_VISIBLE", {}).get("status") == "PASS",
        "legacy debt visibility gate missing",
    )
    require(
        state.get("gates", {}).get("DETERMINISTIC_PROOF_GREEN", {}).get("status")
        == "PENDING_CANONICAL_CI",
        "fresh exact-head proof requirement missing",
    )

    print("PUBLIC_TRUTH_PASS")


if __name__ == "__main__":
    main()
