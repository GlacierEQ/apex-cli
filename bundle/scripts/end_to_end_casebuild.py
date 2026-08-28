#!/usr/bin/env python3
"""Run the optional Casebuilder4000 → Red Helix integration demo.

This script intentionally depends on two external repositories. They are supplied
at runtime rather than hardcoded to one Termux installation, so importing the
``apex-cli`` repository never pretends those projects are bundled dependencies.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any


class IntegrationDependencyError(RuntimeError):
    """Raised when an explicitly requested external integration is unavailable."""


def _require_root(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise IntegrationDependencyError(f"{label} root does not exist: {resolved}")
    return resolved


def _load_external(
    casebuilder_root: Path, red_helix_root: Path
) -> tuple[type[Any], type[Any], type[Any]]:
    casebuilder_root = _require_root(casebuilder_root, "Casebuilder4000")
    red_helix_root = _require_root(red_helix_root, "Red Helix")

    for path in (casebuilder_root, casebuilder_root / ".cortex", red_helix_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    modules = {
        "CaseForge": ("case_forge", "CaseForge"),
        "ExhibitHasher": ("exhibit_hasher", "ExhibitHasher"),
        "AdversarialForge": ("adversarial_forge", "AdversarialForge"),
    }
    loaded: dict[str, type[Any]] = {}
    failures: list[str] = []
    for public_name, (module_name, symbol_name) in modules.items():
        try:
            module = importlib.import_module(module_name)
            loaded[public_name] = getattr(module, symbol_name)
        except (ImportError, AttributeError) as exc:
            failures.append(f"{module_name}.{symbol_name}: {exc}")
    if failures:
        raise IntegrationDependencyError(
            "external Casebuilder/Red Helix contract is incomplete: "
            + "; ".join(failures)
        )
    return loaded["CaseForge"], loaded["ExhibitHasher"], loaded["AdversarialForge"]


def run_end_to_end(
    casebuilder_root: Path,
    red_helix_root: Path,
    *,
    case_id: str = "CASE_1010_ALPHA",
) -> dict[str, str]:
    CaseForge, ExhibitHasher, AdversarialForge = _load_external(
        casebuilder_root, red_helix_root
    )
    casebuilder_root = casebuilder_root.expanduser().resolve()
    red_helix_root = red_helix_root.expanduser().resolve()

    exhibits_dir = casebuilder_root / "exhibits_binary"
    exhibits_dir.mkdir(parents=True, exist_ok=True)
    exhibit_name = "exhibit_witness_statement.pdf"
    exhibit_path = exhibits_dir / exhibit_name
    exhibit_path.write_bytes(b"This is verified witness testimony for case 1010.")

    hasher = ExhibitHasher(str(exhibits_dir))
    exhibit_hash = hasher.generate_hash_sidecar(exhibit_name)
    payload = {
        "is_finalized": True,
        "evidence": [exhibit_name],
        "analysis": "Testimony verifies actor was present. Clear anomalies detected in transaction logs.",
    }

    forge = CaseForge(str(casebuilder_root))
    sealed_case_path = forge.build_case(case_id, payload)
    adversary = AdversarialForge(str(red_helix_root))
    red_report = adversary.attack_case(sealed_case_path)
    ledger_path = casebuilder_root / "chain_of_custody" / f"{case_id}_custody.jsonl"

    return {
        "case_id": case_id,
        "exhibit": str(exhibit_path),
        "exhibit_hash": str(exhibit_hash),
        "sealed_case": str(sealed_case_path),
        "red_report": str(red_report),
        "custody_ledger": str(ledger_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--casebuilder-root", type=Path, required=True)
    parser.add_argument("--red-helix-root", type=Path, required=True)
    parser.add_argument("--case-id", default="CASE_1010_ALPHA")
    args = parser.parse_args()
    try:
        result = run_end_to_end(
            args.casebuilder_root,
            args.red_helix_root,
            case_id=args.case_id,
        )
    except IntegrationDependencyError as exc:
        parser.error(str(exc))
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
