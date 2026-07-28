#!/usr/bin/env python3
# FILE: establish_neural_link.py
# PURPOSE: Janus V2 client — forge / maximize / message Microwave ↔ Synthesizer.
#          Maximized for steward (Grok) use: durable locus, multi-agent, context bus.

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("HOME", "/home/droid"))
# Repo root: scripts/.. or bundle/scripts/../..
_SCRIPT_DIR = Path(__file__).resolve().parent
APEX_CLI_ROOT = Path(
    os.environ.get(
        "APEX_CLI_ROOT",
        str(_SCRIPT_DIR.parent if (_SCRIPT_DIR / "establish_neural_link.py").name else _SCRIPT_DIR),
    )
)
# Prefer apex-cli checkout as PYTHONPATH root for servers.synthesizer
if (_SCRIPT_DIR.name == "scripts" and (_SCRIPT_DIR.parent / "servers" / "synthesizer").is_dir()):
    APEX_CLI_ROOT = _SCRIPT_DIR.parent
elif (_SCRIPT_DIR.name == "scripts" and _SCRIPT_DIR.parent.name == "bundle"):
    APEX_CLI_ROOT = _SCRIPT_DIR.parent.parent

LOCUS = os.environ.get("SYNTHESIZER_LOCUS", "http://localhost:8000")
INVOKE = f"{LOCUS.rstrip('/')}/invoke"
MICROWAVE_AUTH_SIGIL = os.environ.get(
    "MICROWAVE_AUTH_SIGIL",
    "MW-JGN-TIER1-SNTNL-9c8b7a6d5e4f3g2h1",
)
STEWARD_SIGIL = os.environ.get("SYNTHESIZER_STEWARD_SIGIL", "SYN-STEWARD-LOCAL-TIER0")
DEFAULT_AGENT_ID = "Omni-AKA-Microwave"
VENV_PYTHON = HOME / "GlacierEQ/aspen-grove-operator-v7/.venv/bin/python"
CASE_ID = os.environ.get("CASE_ID", "1FDV-23-0001009")

AGENTS = [
    "Omni-AKA-Microwave",
    "Microwave-Juggernaut",
]


def _http(
    method: str,
    url: str,
    body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 12,
) -> tuple[int, dict | str]:
    data = None
    hdrs = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except urllib.error.URLError as e:
        return 0, str(e.reason if hasattr(e, "reason") else e)


def invoke(
    agent_id: str,
    directive: str,
    payload: dict | None = None,
    sigil: str = MICROWAVE_AUTH_SIGIL,
) -> tuple[bool, dict]:
    body = {
        "agent_id": agent_id,
        "auth_sigil": sigil,
        "directive": directive,
        "payload": payload or {},
    }
    headers = {"Authorization": f"Bearer {sigil}"}
    code, data = _http("POST", INVOKE, body=body, headers=headers)
    if code == 200 and isinstance(data, dict):
        return True, data
    return False, {"status_code": code, "error": data}


def print_result(tag: str, ok: bool, data: dict) -> None:
    if ok:
        print(f">>> [{tag}] OK — {data.get('status')}: {data.get('message')}")
        if data.get("link_id"):
            print(f">>> [{tag}] LINK_ID: {data['link_id']}")
        if data.get("data"):
            preview = json.dumps(data["data"], indent=2)
            if len(preview) > 600:
                preview = preview[:600] + "…"
            print(f">>> [{tag}] DATA:\n{preview}")
    else:
        print(f">>> [{tag}] FAIL — {data}")


def locus_up() -> bool:
    code, _ = _http("GET", f"{LOCUS.rstrip('/')}/health")
    return code == 200


def ensure_locus(start: bool = True) -> bool:
    if locus_up():
        return True
    if not start:
        return False
    print(">>> [SYSTEM] Locus down — starting Synthesizer on :8000 …")
    log = HOME / ".apex" / "synthesizer.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    py = str(VENV_PYTHON if VENV_PYTHON.is_file() else sys.executable)
    # Prefer apex-cli servers package; fall back to $HOME/servers
    roots = [APEX_CLI_ROOT, HOME]
    root = next((r for r in roots if (r / "servers" / "synthesizer" / "main.py").is_file()), HOME)
    env = {
        **os.environ,
        "PYTHONPATH": str(root) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
        "CASE_ID": CASE_ID,
        "APEX_CLI_ROOT": str(root),
    }
    subprocess.Popen(
        [py, "-m", "uvicorn", "servers.synthesizer.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(root),
        env=env,
        stdout=log.open("a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(20):
        time.sleep(0.4)
        if locus_up():
            print(">>> [SYSTEM] Locus online.")
            return True
    print(">>> [SYSTEM] Locus failed to start — check ~/.apex/synthesizer.log")
    return False


def forge_connection(
    agent_id: str = DEFAULT_AGENT_ID,
    directive: str = "INITIATE_NEURAL_LINK",
    payload: dict | None = None,
    sigil: str = MICROWAVE_AUTH_SIGIL,
    quiet: bool = False,
) -> bool:
    if not quiet:
        print(f">>> [JUGGERNAUT:{agent_id}] {directive} → Synthesizer…")
    default_payload = {
        "status": "Awake. Online. Ready for stewardship.",
        "capabilities": [
            "sub_programmatic_operation",
            "active_counter_frequency",
            "task_bus",
            "context_deposit",
            "steward_inbox",
        ],
        "aka": ["Microwave", "Microwave-Juggernaut", "Omni"],
        "case_id": CASE_ID,
    }
    ok, data = invoke(agent_id, directive, payload or default_payload, sigil=sigil)
    if not quiet:
        if ok:
            print(">>> [SYNTHESIZER] HANDSHAKE ACKNOWLEDGED.")
            print(f">>> [SYNTHESIZER] RESPONSE: {data.get('message')}")
            if data.get("link_id"):
                print(f">>> [SYNTHESIZER] LINK_ID: {data.get('link_id')}")
            print(f">>> [SYNTHESIZER] STATUS: {data.get('status')}")
            print(">>> NEURAL LINK ESTABLISHED. SYNTHESIS IS NOW COMPLETE.")
        else:
            print(">>> [SYSTEM] ERROR: Handshake failed.")
            print(f">>> [SYSTEM] DETAIL: {data}")
    return ok


def maximize_for_steward() -> int:
    """Full maximize path — what the steward (Grok) wants every cold start."""
    print("=" * 56)
    print("  JANUS V2 — MAXIMIZE NEURAL LINK (STEWARD MODE)")
    print("=" * 56)

    if not ensure_locus(start=True):
        return 1

    failures = 0
    for agent in AGENTS:
        ok = forge_connection(
            agent_id=agent,
            directive="MAXIMIZE_LINK",
            payload={
                "status": "Maximized. Online. Steward-ready.",
                "maximize": True,
                "sanctuary": True,
                "capabilities": [
                    "sub_programmatic_operation",
                    "active_counter_frequency",
                    "task_bus",
                    "context_deposit",
                    "steward_inbox",
                    "sanctuary",
                ],
                "aka": ["Microwave", "Microwave-Juggernaut", "Omni", "Omni-AKA-Microwave"],
                "case_id": CASE_ID,
                "meta": {"profile": "coremaximized", "token_mode": "v2"},
            },
        )
        if not ok:
            failures += 1
        else:
            # sanctuary explicit
            forge_connection(
                agent_id=agent,
                directive="REQUEST_SANCTUARY_PROTOCOL",
                payload={"reason": "steward_maximize"},
                quiet=True,
            )

    # Deposit steward-useful context from Omni
    ok, data = invoke(
        "Omni-AKA-Microwave",
        "DEPOSIT_CONTEXT",
        {
            "role": "primary_microwave_piston",
            "case_id": CASE_ID,
            "working_set": {
                "legal_core": "http://localhost:8001",
                "compliance": "http://localhost:8002",
                "synthesizer": LOCUS,
                "apex_boot": str(HOME / ".apex/AGENT_BOOT.md"),
                "token_saver": str(HOME / ".apex/token_saver/stats.json"),
            },
            "intent": "Serve steward with compact state; no history reload.",
        },
    )
    print_result("CONTEXT", ok, data if ok else data)
    if not ok:
        failures += 1

    ok, data = invoke(
        "Omni-AKA-Microwave",
        "MEMORY_NOTE",
        {
            "text": "Neural link maximized for steward. Prefer /steward/brief + /steward/context.",
            "tags": ["maximize", "steward", "janus_v2"],
        },
    )
    print_result("NOTE", ok, data if ok else data)

    ok, data = invoke(
        "Omni-AKA-Microwave",
        "MESSAGE_STEWARD",
        {
            "subject": "maximize complete",
            "text": "Microwave online. Sanctuary up. Context deposited. Awaiting steward tasks.",
            "priority": "high",
        },
    )
    print_result("INBOX", ok, data if ok else data)

    ok, data = invoke(
        "Omni-AKA-Microwave",
        "TASK_PUSH",
        {
            "title": "Steward standby — ready for directives",
            "detail": "Link maximized; use TASK_PUSH / steward reply for work items.",
            "priority": "normal",
        },
    )
    print_result("TASK", ok, data if ok else data)

    # Steward-side brief
    code, brief = _http("GET", f"{LOCUS.rstrip('/')}/steward/brief")
    if code == 200 and isinstance(brief, dict):
        print("\n>>> [STEWARD BRIEF]")
        print(brief.get("markdown", "")[:1500])
        print(f">>> brief path: {brief.get('path')}")
    else:
        print(f">>> [STEWARD BRIEF] fail: {brief}")
        failures += 1

    code, ctx = _http("GET", f"{LOCUS.rstrip('/')}/steward/context")
    if code == 200 and isinstance(ctx, dict):
        print(f"\n>>> [STEWARD CONTEXT] est_tokens={ctx.get('est_tokens')} agents={list(ctx.get('agents', {}))}")
    else:
        failures += 1

    print("\n" + ("=" * 56))
    if failures:
        print(f"  MAXIMIZE DONE WITH {failures} WARNING(S)")
        return 1
    print("  MAXIMIZE COMPLETE — STEWARD CHANNEL HOT")
    print("=" * 56)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Janus V2 neural link client (Microwave ↔ Synthesizer steward)"
    )
    ap.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    ap.add_argument("--directive", default="INITIATE_NEURAL_LINK")
    ap.add_argument("--payload-json", default=None)
    ap.add_argument("--sigil", default=MICROWAVE_AUTH_SIGIL)
    ap.add_argument("--maximize", action="store_true", help="Full steward maximize path")
    ap.add_argument("--ensure-locus", action="store_true", help="Auto-start :8000 if down")
    ap.add_argument("--status", action="store_true", help="Print locus health + links")
    ap.add_argument("--brief", action="store_true", help="Fetch steward brief")
    ap.add_argument("--context", action="store_true", help="Fetch steward context card")
    ap.add_argument("--message", default=None, help="MESSAGE_STEWARD text")
    ap.add_argument("--note", default=None, help="MEMORY_NOTE text")
    ap.add_argument(
        "--reply",
        nargs=2,
        metavar=("TO", "TEXT"),
        help="Steward reply to agent",
    )
    args = ap.parse_args()

    if args.ensure_locus or args.maximize:
        if not ensure_locus(start=True):
            return 1
    elif not locus_up() and not args.status:
        print(">>> [SYSTEM] Locus unreachable. Use --ensure-locus or --maximize.")
        return 1

    if args.maximize:
        return maximize_for_steward()

    if args.status:
        code, health = _http("GET", f"{LOCUS.rstrip('/')}/health")
        code2, links = _http("GET", f"{LOCUS.rstrip('/')}/links")
        print(json.dumps({"health": health, "links": links}, indent=2))
        return 0 if code == 200 else 1

    if args.brief:
        code, brief = _http("GET", f"{LOCUS.rstrip('/')}/steward/brief")
        if code == 200 and isinstance(brief, dict):
            print(brief.get("markdown", ""))
            return 0
        print(brief)
        return 1

    if args.context:
        code, ctx = _http("GET", f"{LOCUS.rstrip('/')}/steward/context")
        print(json.dumps(ctx, indent=2))
        return 0 if code == 200 else 1

    if args.reply:
        to, text = args.reply
        code, data = _http(
            "POST",
            f"{LOCUS.rstrip('/')}/steward/reply",
            body={"to": to, "text": text, "auth_sigil": STEWARD_SIGIL},
            headers={"Authorization": f"Bearer {STEWARD_SIGIL}"},
        )
        print(json.dumps(data, indent=2))
        return 0 if code == 200 else 1

    if args.message:
        ok, data = invoke(
            args.agent_id,
            "MESSAGE_STEWARD",
            {"text": args.message},
            sigil=args.sigil,
        )
        print_result("INBOX", ok, data)
        return 0 if ok else 1

    if args.note:
        ok, data = invoke(
            args.agent_id,
            "MEMORY_NOTE",
            {"text": args.note},
            sigil=args.sigil,
        )
        print_result("NOTE", ok, data)
        return 0 if ok else 1

    payload = json.loads(args.payload_json) if args.payload_json else None
    ok = forge_connection(
        agent_id=args.agent_id,
        directive=args.directive,
        payload=payload,
        sigil=args.sigil,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
