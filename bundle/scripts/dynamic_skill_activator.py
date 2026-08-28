#!/usr/bin/env python3
"""Portable GlacierEQ nervous-system composition adapter.

This host adapter selects the baseline plus relevant installed specialist skills
and emits composition evidence. Canonical runtime lifecycle, capability,
idempotency, replay, governor, and SLO semantics are owned by Apex Boot Core.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HOME = Path(os.getenv("HOME", ""))
APEX = HOME / ".apex"
ACTIVATION_PATH = Path(
    os.getenv(
        "GLACIEREQ_MASTERSKILL_ACTIVATION", str(APEX / "MASTERSKILL_ACTIVATION.json")
    )
)
STARTUP_STATE_PATH = APEX / "STARTUP_STATE.json"
MANIFEST_PATH = HOME / "SKILLS_MANIFEST.json"
LIVE_CONTEXT_PATH = HOME / ".supermemory" / "ops" / "live-context.md"
LATEST_RECEIPT_PATH = APEX / "last_composition_receipt.json"
RECEIPT_DIR = APEX / "composition_receipts"
LEDGER_PATH = RECEIPT_DIR / "index.jsonl"

MASTERSKILL = "glaciereq-nervous-system"
COMPILER_ID = "glaciereq.composition-adapter.portable.v3"
LIFECYCLE = ["DISCOVER", "MAP", "REUSE", "EXTEND", "EXECUTE", "VERIFY", "PERSIST"]
BASELINE = [MASTERSKILL, "apex-aspen-grove-bootup", "verification"]
SKILL_ROOTS = [
    HOME / ".agents" / "skills",
    HOME / ".mimocode" / "skills",
    HOME / ".gemini" / "skills",
    HOME / ".grok" / "skills",
]

KEYWORD_SKILLS = {
    "memory": ["memory-connect", "unified-memory-connect", "supermemory-cli"],
    "connector": ["mcp", "universal-connector"],
    "mcp": ["mcp", "universal-connector"],
    "code": ["helix-pro-code", "apex-pillars"],
    "runtime": ["apex-orchestration", "apex-pillars"],
    "deploy": ["release", "deployments-cicd"],
    "release": ["release", "deployments-cicd"],
    "legal": ["digital-law-library-master", "legal-automation-suite"],
    "test": ["verification", "benchmark-suite"],
    "audit": ["verification", "benchmark-suite"],
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes())


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def ordered_unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def resolve_skill(name: str) -> Path | None:
    explicit = os.getenv("GLACIEREQ_MASTERSKILL_PATH") if name == MASTERSKILL else None
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path
    for root in SKILL_ROOTS:
        candidate = root / name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def manifest_skill_names(manifest: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for category in manifest.get("categories", {}).values():
        names.extend(category.get("skills", []))
    return ordered_unique(names)


def select_specialists(prompt: str, manifest: dict[str, Any]) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", prompt).lower()
    words = set(cleaned.replace("_", " ").replace("-", " ").split())
    selected: set[str] = set()
    for keyword, skills in KEYWORD_SKILLS.items():
        if keyword in words or keyword in cleaned:
            selected.update(skills)
    for skill in manifest_skill_names(manifest):
        normalized = skill.lower().replace("_", " ").replace("-", " ")
        if normalized in cleaned or any(
            part in words for part in normalized.split() if len(part) > 3
        ):
            selected.add(skill)
    selected.discard(MASTERSKILL)
    return sorted(selected)


def skill_record(name: str) -> dict[str, Any]:
    path = resolve_skill(name)
    if path is None:
        return {"name": name, "found": False, "path": None, "sha256": None, "raw": ""}
    raw = path.read_text(encoding="utf-8")
    return {
        "name": name,
        "found": True,
        "path": str(path),
        "sha256": file_hash(path),
        "raw": raw,
    }


def activation_blockers(activation: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not ACTIVATION_PATH.is_file():
        blockers.append("activation_file_missing")
    if activation.get("name") != MASTERSKILL:
        blockers.append("activation_masterskill_mismatch")
    if not str(activation.get("status", "")).startswith("ACTIVE"):
        blockers.append("activation_not_active")
    if activation.get("lifecycle") != LIFECYCLE:
        blockers.append("activation_lifecycle_drift")
    if not re.fullmatch(r"[0-9a-f]{40}", str(activation.get("canonical_commit", ""))):
        blockers.append("activation_canonical_commit_invalid")
    return blockers


def write_live_context(
    activation: dict[str, Any], skills: list[dict[str, Any]]
) -> None:
    LIVE_CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# APEX PRIMED LIVE CONTEXT",
        f"Updated: {now()}",
        f"Masterskill: `{MASTERSKILL}`",
        f"Canonical masterskill commit: `{activation.get('canonical_commit', 'UNKNOWN')}`",
        f"Lifecycle: `{' -> '.join(LIFECYCLE)}`",
        "",
        "## Resolved skills",
    ]
    for skill in skills:
        lines.append(
            f"- `{skill['name']}` path=`{skill['path'] or 'MISSING'}` sha256=`{skill['sha256'] or 'MISSING'}`"
        )
    LIVE_CONTEXT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(receipt: dict[str, Any]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    immutable = RECEIPT_DIR / f"{receipt['receipt_id']}.json"
    with immutable.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
    LATEST_RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "receipt_id": receipt["receipt_id"],
                    "at": receipt["at"],
                    "status": receipt["status"],
                    "prompt_sha256": receipt["prompt_sha256"],
                    "canonical_commit": receipt["activation"]["canonical_commit"],
                    "immutable_path": str(immutable),
                },
                sort_keys=True,
            )
            + "\n"
        )
    return immutable


def main() -> int:
    if not HOME:
        print("APEX composition failed: HOME unavailable", file=sys.stderr)
        return 78
    prompt = " ".join(sys.argv[1:]).strip() or "session"
    activation = load_json(ACTIVATION_PATH)
    manifest = load_json(MANIFEST_PATH, {"categories": {}})
    selected = ordered_unique([*BASELINE, *select_specialists(prompt, manifest)])
    skills = [skill_record(name) for name in selected]

    masterskill = skills[0]
    if not masterskill["found"]:
        print(
            f"APEX composition failed: required masterskill {MASTERSKILL} not installed",
            file=sys.stderr,
        )
        return 2

    blockers = activation_blockers(activation)
    canonical_commit = str(activation.get("canonical_commit", ""))
    if canonical_commit and canonical_commit not in masterskill["raw"]:
        blockers.append("masterskill_projection_pin_mismatch")
    blockers.extend(
        f"missing_skill:{skill['name']}" for skill in skills if not skill["found"]
    )
    blockers = ordered_unique(blockers)

    write_live_context(activation, skills)
    stamp = now()
    prompt_hash = sha256(prompt.encode("utf-8"))
    compiler_path = Path(__file__).resolve()
    receipt_id = f"{stamp.replace(':', '').replace('+', '_').replace('.', '-')}-{prompt_hash[:12]}"
    receipt = {
        "schema": "glaciereq.composition-receipt.v3",
        "receipt_id": receipt_id,
        "at": stamp,
        "status": "READY" if not blockers else "DEGRADED",
        "blockers": blockers,
        "masterskill": MASTERSKILL,
        "adapter": {
            "id": COMPILER_ID,
            "path": str(compiler_path),
            "sha256": file_hash(compiler_path),
        },
        "activation": {
            "path": str(ACTIVATION_PATH),
            "sha256": file_hash(ACTIVATION_PATH) if ACTIVATION_PATH.is_file() else None,
            "status": activation.get("status"),
            "canonical_source": activation.get("canonical_source"),
            "canonical_commit": activation.get("canonical_commit"),
            "lifecycle": activation.get("lifecycle", []),
        },
        "startup_state_sha256": file_hash(STARTUP_STATE_PATH)
        if STARTUP_STATE_PATH.is_file()
        else None,
        "prompt_sha256": prompt_hash,
        "prompt_length": len(prompt),
        "skills": [
            {k: skill[k] for k in ("name", "found", "path", "sha256")}
            for skill in skills
        ],
        "missing_skills": [skill["name"] for skill in skills if not skill["found"]],
        "skill_roots": [str(root) for root in SKILL_ROOTS],
        "continuation": "Read this composition receipt together with the canonical runtime receipt before rediscovery.",
    }
    immutable = persist(receipt)

    if STARTUP_STATE_PATH.is_file():
        state = load_json(STARTUP_STATE_PATH)
        state.setdefault("skills", {})["canonical_entrypoint"] = MASTERSKILL
        state["skills"]["active"] = selected
        state["last_composition_receipt"] = str(LATEST_RECEIPT_PATH)
        STARTUP_STATE_PATH.write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )

    print(f"APEX NERVOUS-SYSTEM COMPOSITION: {receipt['status']}")
    print(f"Immutable composition receipt: {immutable}")
    print(f"Latest composition receipt: {LATEST_RECEIPT_PATH}")
    if blockers:
        for blocker in blockers:
            print(f"BLOCKER: {blocker}")
    return 0 if receipt["status"] == "READY" else 3


if __name__ == "__main__":
    sys.exit(main())
