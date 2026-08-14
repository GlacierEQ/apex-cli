#!/usr/bin/env python3
# Projection of GlacierEQ/MiMo-Config scripts/dynamic_skill_activator.py.
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

HOME = Path(os.getenv("HOME", "/data/data/com.termux/files/home"))
MANIFEST_PATH = HOME / "SKILLS_MANIFEST.json"
STARTUP_STATE_PATH = HOME / ".apex" / "STARTUP_STATE.json"
ACTIVATION_PATH = Path(os.getenv("GLACIEREQ_MASTERSKILL_ACTIVATION", str(HOME / ".apex" / "MASTERSKILL_ACTIVATION.json")))
LIVE_CONTEXT_PATH = HOME / ".supermemory" / "ops" / "live-context.md"
RUNTIME_RECEIPT_PATH = HOME / ".apex" / "last_runtime_receipt.json"

MASTERSKILL = "glaciereq-nervous-system"
BASELINE_SKILLS = [MASTERSKILL, "apex-aspen-grove-bootup", "verification"]
DEFAULT_SKILL_ROOTS = [
    HOME / ".agents" / "skills",
    HOME / ".mimocode" / "skills",
    HOME / ".gemini" / "skills",
    HOME / ".grok" / "skills",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s_-]", "", text).lower()


def ordered_unique(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def ordered_unique_paths(paths: Iterable[Path]) -> List[Path]:
    seen: set[str] = set()
    output: List[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            output.append(path)
    return output


def skill_roots() -> List[Path]:
    configured = os.getenv("APEX_SKILL_ROOTS", "").strip()
    roots = [Path(p).expanduser() for p in configured.split(os.pathsep) if p] if configured else []
    return ordered_unique_paths([*roots, *DEFAULT_SKILL_ROOTS])


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_activation() -> Dict[str, Any]:
    if ACTIVATION_PATH.is_file():
        return load_json(ACTIVATION_PATH)
    return {
        "name": MASTERSKILL,
        "status": "ACTIVATION_FILE_MISSING",
        "lifecycle": ["DISCOVER", "MAP", "REUSE", "EXTEND", "EXECUTE", "VERIFY", "PERSIST"],
    }


def match_specialists(prompt: str, manifest: Dict[str, Any]) -> List[str]:
    matched: set[str] = set()
    cleaned_prompt = clean_text(prompt)
    prompt_words = set(cleaned_prompt.split())
    keyword_map = {
        "mcp": ["apex-orchestration", "unified-memory-connect", "memory-connect"],
        "connector": ["mcp", "universal-connector"],
        "memory": ["memory-unified", "memory-connect", "unified-memory-connect"],
        "mem0": ["memory-unified", "memory-connect", "unified-memory-connect"],
        "supermemory": ["memory-unified", "memory-connect", "unified-memory-connect"],
        "notion": ["memory-unified", "memory-connect", "unified-memory-connect"],
        "vercel": ["ai-gateway", "ai-sdk", "auth", "env-vars", "marketplace", "vercel-agent", "vercel-firewall", "vercel-functions", "vercel-platform-ops", "vercel-sandbox", "vercel-storage"],
        "next": ["nextjs-ecosystem", "frontend-ui-toolkit", "microfrontends", "turbopack"],
        "react": ["frontend-ui-toolkit", "microfrontends"],
        "ui": ["frontend-ui-toolkit"],
        "css": ["frontend-ui-toolkit"],
        "tailwind": ["frontend-ui-toolkit"],
        "legal": ["legal-automation-suite", "digital-law-library-master"],
        "rico": ["legal-automation-suite", "digital-law-library-master"],
        "forensic": ["legal-automation-suite", "digital-law-library-master"],
        "court": ["legal-automation-suite", "digital-law-library-master"],
        "audit": ["legal-automation-suite", "digital-law-library-master", "benchmark-suite"],
        "test": ["benchmark-suite", "verification"],
        "workflow": ["workflow", "bootstrap"],
        "runtime": ["apex-orchestration", "apex-pillars", "verification"],
        "boot": ["bootstrap", "apex-aspen-grove-bootup"],
        "deploy": ["release", "deployments-cicd", "verification"],
        "release": ["release", "deployments-cicd", "verification"],
        "piston": ["apex-orchestration", "apexruntime", "apex-pillars"],
        "gate": ["apex-orchestration", "apexruntime"],
        "routing": ["routing-middleware", "runtime-cache"],
        "cache": ["runtime-cache", "routing-middleware"],
        "omniverse": ["sovereign-ascension", "sovereign-operator", "apex-gemma4-omni-node"],
        "apex": ["apex-orchestration", "apexruntime", "apex-pillars", "sovereign-ascension", "sovereign-operator"],
        "gemma": ["apex-gemma4-omni-node"],
        "link": ["library-of-links"],
    }
    for keyword, skills in keyword_map.items():
        if keyword in cleaned_prompt:
            matched.update(skills)
    for category_info in manifest.get("categories", {}).values():
        for skill in category_info.get("skills", []):
            skill_clean = skill.replace("-", " ").replace("_", " ")
            if skill_clean in cleaned_prompt or any(word in skill.split("-") for word in prompt_words):
                matched.add(skill)
    matched.discard(MASTERSKILL)
    return sorted(matched)


def resolve_skill_file(skill_name: str) -> Path | None:
    explicit = os.getenv("GLACIEREQ_MASTERSKILL_PATH") if skill_name == MASTERSKILL else None
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path
    for root in skill_roots():
        candidate = root / skill_name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def get_skill_details(skill_name: str) -> Dict[str, Any]:
    skill_file = resolve_skill_file(skill_name)
    if skill_file is None:
        return {"name": skill_name, "description": "(SKILL.md missing across configured host roots)", "content": "", "path": None, "found": False}
    try:
        content = skill_file.read_text(encoding="utf-8")
        desc_match = re.search(r"description:\s*[\"']?(.*?)[\"']?\n", content, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else "No description available."
        clean_content = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                clean_content = parts[2].strip()
        return {"name": skill_name, "description": description, "content": clean_content, "path": str(skill_file), "found": True}
    except Exception as exc:
        return {"name": skill_name, "description": f"Error loading skill: {exc}", "content": "", "path": str(skill_file), "found": False}


def get_bundled_connectors(skills: List[str]) -> List[Dict[str, str]]:
    connectors: List[Dict[str, str]] = []
    memory_skills = {"memory-unified", "memory-connect", "unified-memory-connect"}
    vercel_skills = {"ai-gateway", "ai-sdk", "auth", "env-vars", "marketplace", "vercel-agent", "vercel-firewall", "vercel-functions", "vercel-platform-ops", "vercel-sandbox", "vercel-storage"}
    if any(s in memory_skills for s in skills):
        connectors.extend([
            {"name": "unified-memory", "type": "MCP / REST API", "description": "Semantic memory router.", "usage": "Recover durable state before rediscovery."},
            {"name": "supermemory-cli", "type": "Local Tool / CLI", "description": "Persistent priming and durable-save interface.", "usage": "Prime before mission reconstruction and persist verified continuation state."},
        ])
    if any(s in vercel_skills for s in skills):
        connectors.append({"name": "vercel-cli", "type": "CLI Integration", "description": "Deployment and runtime management.", "usage": "Use for verified deployment/build/environment operations."})
    connectors.append({"name": "desktop-commander", "type": "MCP Command Runner", "description": "Execution node when available in the active host.", "usage": "Use for execution loops and persistent session tracking."})
    return connectors


def write_live_context(activation: Dict[str, Any], skills_info: List[Dict[str, Any]], connectors: List[Dict[str, str]]) -> None:
    LIVE_CONTEXT_PATH.parent.mkdir(exist_ok=True, parents=True)
    lifecycle = activation.get("lifecycle") or ["DISCOVER", "MAP", "REUSE", "EXTEND", "EXECUTE", "VERIFY", "PERSIST"]
    lines = ["# APEX PRIMED LIVE CONTEXT", f"Updated: {utc_now()}", "", f"Masterskill: `{MASTERSKILL}`", f"Lifecycle: `{' -> '.join(lifecycle)}`", "", "## ACTIVE BUNDLED CONNECTORS"]
    for conn in connectors:
        lines.extend([f"### `{conn['name']}` ({conn['type']})", f"- **Description:** {conn['description']}", f"- **Strategic Usage:** {conn['usage']}", ""])
    lines.extend(["## ACTIVE SKILL SPECIFICATIONS", ""])
    for skill in skills_info:
        lines.extend([f"### Skill: {skill['name']}", f"- **Purpose:** {skill['description']}", f"- **Resolved path:** `{skill['path'] or 'MISSING'}`", "", "#### Instructions:", skill["content"], "", "---", ""])
    LIVE_CONTEXT_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_startup_state(active_skills: List[str], receipt_path: Path) -> None:
    if not STARTUP_STATE_PATH.is_file():
        return
    state = load_json(STARTUP_STATE_PATH)
    skills = state.setdefault("skills", {})
    skills["canonical_entrypoint"] = MASTERSKILL
    skills["active"] = active_skills
    state["last_runtime_receipt"] = str(receipt_path)
    state["workflow"] = {**state.get("workflow", {}), "phases": ["boot", "discover", "map", "reuse", "extend", "execute", "verify", "persist"]}
    STARTUP_STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def write_runtime_receipt(prompt: str, activation: Dict[str, Any], skills_info: List[Dict[str, Any]], connectors: List[Dict[str, str]]) -> Dict[str, Any]:
    RUNTIME_RECEIPT_PATH.parent.mkdir(exist_ok=True, parents=True)
    missing = [skill["name"] for skill in skills_info if not skill["found"]]
    receipt = {
        "schema": "glaciereq.runtime-composition-receipt.v1",
        "at": utc_now(),
        "status": "READY" if not missing else "DEGRADED",
        "masterskill": MASTERSKILL,
        "activation_status": activation.get("status", "UNKNOWN"),
        "lifecycle": activation.get("lifecycle", []),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_length": len(prompt),
        "skills": [{"name": skill["name"], "path": skill["path"], "found": skill["found"]} for skill in skills_info],
        "missing_skills": missing,
        "connectors": [connector["name"] for connector in connectors],
        "skill_roots": [str(root) for root in skill_roots()],
        "continuation": "Read this receipt, then current startup state and live context before rediscovery.",
    }
    RUNTIME_RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 dynamic_skill_activator.py '<user prompt or task>'")
        return 1
    prompt = sys.argv[1]
    manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.is_file() else {"categories": {}}
    activation = load_activation()
    specialists = match_specialists(prompt, manifest)
    active_skills = ordered_unique([*BASELINE_SKILLS, *specialists])
    skills_info = [get_skill_details(skill) for skill in active_skills]
    masterskill_info = next(skill for skill in skills_info if skill["name"] == MASTERSKILL)
    if not masterskill_info["found"]:
        print(f"Error: required masterskill {MASTERSKILL!r} is not installed in any configured skill root.")
        return 2
    connectors = get_bundled_connectors(active_skills)
    write_live_context(activation, skills_info, connectors)
    receipt = write_runtime_receipt(prompt, activation, skills_info, connectors)
    update_startup_state(active_skills, RUNTIME_RECEIPT_PATH)
    print(f"APEX NERVOUS-SYSTEM COMPOSITION: {receipt['status']}")
    print(f"Runtime receipt: {RUNTIME_RECEIPT_PATH}")
    return 0 if receipt["status"] == "READY" else 3


if __name__ == "__main__":
    sys.exit(main())
