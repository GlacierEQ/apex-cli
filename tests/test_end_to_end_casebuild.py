"""Optional external Casebuilder/Red-Helix integration harness.

This file is intentionally not part of the repository-local proof surface. It
requires explicit external roots and imports those external modules only when the
harness is invoked, so normal test collection does not pretend those sibling
systems are present or connected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _required_root(env_name: str) -> Path:
    value = os.environ.get(env_name)
    if not value:
        raise RuntimeError(f"{env_name} is required for the external integration harness")
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"{env_name} does not resolve to a directory: {root}")
    return root


def run_end_to_end() -> None:
    casebuilder_root = _required_root("APEX_CASEBUILDER_ROOT")
    red_helix_root = _required_root("APEX_RED_HELIX_ROOT")

    sys.path.insert(0, str(casebuilder_root))
    sys.path.insert(0, str(casebuilder_root / ".cortex"))
    sys.path.insert(0, str(red_helix_root))

    from adversarial_forge import AdversarialForge
    from case_forge import CaseForge
    from exhibit_hasher import ExhibitHasher

    exhibit_name = "exhibit_demo_statement.pdf"
    exhibit_dir = casebuilder_root / "exhibits_binary"
    exhibit_dir.mkdir(parents=True, exist_ok=True)
    exhibit_path = exhibit_dir / exhibit_name
    exhibit_path.write_bytes(b"Synthetic integration-harness evidence payload.")

    hasher = ExhibitHasher(str(exhibit_dir))
    hasher.generate_hash_sidecar(exhibit_name)

    payload = {
        "is_finalized": True,
        "evidence": [exhibit_name],
        "analysis": "Synthetic integration-harness payload.",
    }
    forge = CaseForge(str(casebuilder_root))
    sealed_case_path = forge.build_case("CASE_DEMO_ALPHA", payload)

    adversary = AdversarialForge(str(red_helix_root))
    adversary.attack_case(sealed_case_path)


if __name__ == "__main__":
    run_end_to_end()
