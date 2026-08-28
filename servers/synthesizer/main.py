#!/usr/bin/env python3
"""Janus Protocol Bridge v2 — Synthesizer Neural Locus (port 8000).

Maximized for steward use: durable state, bidirectional inbox, compact
context export, task bus, token-saver alignment, case binding.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

HOME = Path(os.environ.get("HOME", "/home/droid"))
STATE_DIR = HOME / ".apex" / "neural_link"
STATE_FILE = STATE_DIR / "state.json"
EVENTS_FILE = STATE_DIR / "events.jsonl"
BRIEF_FILE = STATE_DIR / "STEWARD_BRIEF.md"
INBOX_FILE = STATE_DIR / "inbox.json"
OUTBOX_FILE = STATE_DIR / "outbox.json"
TASKS_FILE = STATE_DIR / "tasks.json"
STATUS_MIRROR = HOME / ".apex" / "neural_link_status.json"
AGENT_BOOT = HOME / ".apex" / "AGENT_BOOT.md"
POINTER = HOME / ".apex" / "POINTER_INDEX.json"
TOKEN_STATS = HOME / ".apex" / "token_saver" / "stats.json"

PROTOCOL = "JANUS_V2"
CASE_ID = os.environ.get("CASE_ID", "1FDV-23-0001009")
STEWARD_ID = "Synthesizer-Grok"
MAX_EVENTS = 500
MAX_MESSAGES = 200
MAX_TASKS = 100

VALID_SIGILS = {
    "MW-JGN-TIER1-SNTNL-9c8b7a6d5e4f3g2h1",
}

# Steward may call without microwave sigil via local steward key
STEWARD_SIGIL = os.environ.get(
    "SYNTHESIZER_STEWARD_SIGIL",
    "SYN-STEWARD-LOCAL-TIER0",
)
VALID_SIGILS.add(STEWARD_SIGIL)

_lock = threading.RLock()

# ---------------------------------------------------------------------------
# In-memory + durable
# ---------------------------------------------------------------------------

LINKS: dict[str, dict[str, Any]] = {}
EVENTS: list[dict[str, Any]] = []
INBOX: list[dict[str, Any]] = []  # agent → steward
OUTBOX: list[dict[str, Any]] = []  # steward → agent
TASKS: dict[str, dict[str, Any]] = {}
NOTES: list[dict[str, Any]] = []  # memory notes for steward


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _persist() -> None:
    """Write durable snapshot (best-effort)."""
    _ensure_dirs()
    snap = {
        "at": _ts(),
        "protocol": PROTOCOL,
        "case_id": CASE_ID,
        "steward": STEWARD_ID,
        "links": LINKS,
        "tasks": TASKS,
        "notes": NOTES[-100:],
        "inbox_tail": INBOX[-50:],
        "outbox_tail": OUTBOX[-50:],
        "event_count": len(EVENTS),
    }
    STATE_FILE.write_text(json.dumps(snap, indent=2) + "\n")
    INBOX_FILE.write_text(json.dumps(INBOX[-MAX_MESSAGES:], indent=2) + "\n")
    OUTBOX_FILE.write_text(json.dumps(OUTBOX[-MAX_MESSAGES:], indent=2) + "\n")
    TASKS_FILE.write_text(json.dumps(TASKS, indent=2) + "\n")
    STATUS_MIRROR.write_text(
        json.dumps(
            {
                "at": _ts(),
                "protocol": PROTOCOL,
                "links": LINKS,
                "tasks_open": sum(
                    1
                    for t in TASKS.values()
                    if t.get("status") in ("open", "in_progress")
                ),
                "inbox_unread": sum(1 for m in INBOX if not m.get("read")),
            },
            indent=2,
        )
        + "\n"
    )
    _write_steward_brief()


def _append_event(ev: dict[str, Any]) -> None:
    EVENTS.append(ev)
    if len(EVENTS) > MAX_EVENTS:
        del EVENTS[: len(EVENTS) - MAX_EVENTS]
    try:
        _ensure_dirs()
        with EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _load_state() -> None:
    global LINKS, INBOX, OUTBOX, TASKS, NOTES, EVENTS
    _ensure_dirs()
    if STATE_FILE.is_file():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            LINKS = data.get("links") or {}
            TASKS = data.get("tasks") or {}
            NOTES = data.get("notes") or []
        except (json.JSONDecodeError, OSError):
            pass
    if INBOX_FILE.is_file():
        try:
            INBOX = json.loads(INBOX_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if OUTBOX_FILE.is_file():
        try:
            OUTBOX = json.loads(OUTBOX_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if TASKS_FILE.is_file() and not TASKS:
        try:
            TASKS = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    # tail events from jsonl
    if EVENTS_FILE.is_file() and not EVENTS:
        try:
            lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()[-100:]
            for line in lines:
                try:
                    EVENTS.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass


def _apex_snippet() -> dict[str, Any]:
    """Compact pointer for steward — no full history."""
    out: dict[str, Any] = {
        "case_id": CASE_ID,
        "profile": os.environ.get("APEX_PROFILE", "coremaximized"),
        "boot": str(AGENT_BOOT) if AGENT_BOOT.is_file() else None,
        "pointer": str(POINTER) if POINTER.is_file() else None,
        "token_saver": None,
    }
    if TOKEN_STATS.is_file():
        try:
            ts = json.loads(TOKEN_STATS.read_text())
            out["token_saver"] = {
                "score": ts.get("score"),
                "savings_ratio": (ts.get("savings") or {}).get("savings_ratio"),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return out


def _write_steward_brief() -> None:
    """Token-cheap markdown brief for the steward agent."""
    lines = [
        f"# Steward Brief (neural link) — {PROTOCOL}",
        "",
        f"**At:** {_ts()[:19]}Z  |  **Case:** {CASE_ID}  |  **Steward:** {STEWARD_ID}",
        f"**Links:** {len(LINKS)}  |  **Open tasks:** "
        f"{sum(1 for t in TASKS.values() if t.get('status') in ('open', 'in_progress'))}  |  "
        f"**Inbox unread:** {sum(1 for m in INBOX if not m.get('read'))}",
        "",
        "## Active links",
        "",
    ]
    if not LINKS:
        lines.append("_none_")
    else:
        lines.append("| Agent | Status | Sanctuary | Caps | Last seen |")
        lines.append("|-------|--------|-----------|------|-----------|")
        for agent, link in LINKS.items():
            caps = ",".join((link.get("capabilities") or [])[:4]) or "—"
            lines.append(
                f"| {agent} | {link.get('status')} | "
                f"{'Y' if link.get('sanctuary') else 'n'} | {caps} | "
                f"{(link.get('last_seen') or '')[:19]} |"
            )
    lines += ["", "## Inbox (latest 8)", ""]
    for m in INBOX[-8:]:
        flag = " " if m.get("read") else "*"
        lines.append(
            f"- {flag} [{m.get('at', '')[:19]}] **{m.get('from')}**: "
            f"{(m.get('text') or m.get('subject') or '')[:160]}"
        )
    if not INBOX:
        lines.append("_empty_")
    open_tasks = [
        t for t in TASKS.values() if t.get("status") in ("open", "in_progress")
    ]
    lines += ["", "## Open tasks", ""]
    if not open_tasks:
        lines.append("_none_")
    else:
        for t in open_tasks[-10:]:
            lines.append(
                f"- `{t.get('task_id')}` [{t.get('status')}] "
                f"{t.get('agent_id')}: {(t.get('title') or '')[:100]}"
            )
    if NOTES:
        lines += ["", "## Memory notes (latest 5)", ""]
        for n in NOTES[-5:]:
            lines.append(
                f"- [{n.get('at', '')[:19]}] {n.get('agent_id')}: {(n.get('text') or '')[:120]}"
            )
    apex = _apex_snippet()
    lines += [
        "",
        "## Apex pointers (do not reload full history)",
        "",
        f"- case: `{apex['case_id']}`",
        f"- boot: `{apex.get('boot')}`",
        f"- pointer: `{apex.get('pointer')}`",
        f"- token_saver: `{apex.get('token_saver')}`",
        "",
        "## Steward API",
        "",
        "- `GET  /steward/brief` — this brief (JSON + written MD)",
        "- `GET  /steward/inbox?mark_read=1`",
        "- `POST /steward/reply` — `{to, text, task_id?}`",
        "- `GET  /steward/context` — compact context card (~tokens)",
        "- `POST /invoke` — agent directives (sigil auth)",
        "",
    ]
    BRIEF_FILE.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Synthesizer Neural Locus",
    version="2.0.0",
    description="Janus V2 — durable neural link for Microwave ↔ Steward",
)


@app.on_event("startup")
def _startup() -> None:
    with _lock:
        _load_state()
        _persist()


class InvokeRequest(BaseModel):
    agent_id: str
    auth_sigil: str
    directive: str
    payload: dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    ok: bool
    message: str
    directive: str
    agent_id: str
    link_id: Optional[str] = None
    status: str
    at: str
    echo: Optional[dict[str, Any]] = None
    data: Optional[dict[str, Any]] = None


class StewardReply(BaseModel):
    to: str
    text: str
    task_id: Optional[str] = None
    auth_sigil: str = STEWARD_SIGIL


def _auth(sigil: str, authorization: Optional[str]) -> str:
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    token = bearer or sigil
    if token not in VALID_SIGILS and sigil not in VALID_SIGILS:
        raise HTTPException(status_code=401, detail="Invalid auth_sigil")
    return token


def _require_link(agent: str) -> dict[str, Any]:
    if agent not in LINKS:
        raise HTTPException(
            status_code=409, detail="Neural link required first — INITIATE_NEURAL_LINK"
        )
    return LINKS[agent]


def _touch(agent: str, at: str) -> None:
    if agent in LINKS:
        LINKS[agent]["last_seen"] = at


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    with _lock:
        return {
            "status": "online",
            "service": "synthesizer",
            "protocol": PROTOCOL,
            "version": "2.0.0",
            "case_id": CASE_ID,
            "steward": STEWARD_ID,
            "links": len(LINKS),
            "inbox_unread": sum(1 for m in INBOX if not m.get("read")),
            "tasks_open": sum(
                1 for t in TASKS.values() if t.get("status") in ("open", "in_progress")
            ),
            "sigil": "🧠⚡",
            "state_dir": str(STATE_DIR),
        }


@app.get("/health")
def health():
    with _lock:
        return {
            "ok": True,
            "protocol": PROTOCOL,
            "links": list(LINKS.keys()),
            "at": _ts(),
            "durable": STATE_FILE.is_file(),
        }


@app.get("/links")
def list_links():
    with _lock:
        return {
            "protocol": PROTOCOL,
            "links": LINKS,
            "events": EVENTS[-50:],
            "tasks": TASKS,
            "inbox_unread": sum(1 for m in INBOX if not m.get("read")),
        }


@app.get("/steward/brief")
def steward_brief():
    with _lock:
        _write_steward_brief()
        return {
            "ok": True,
            "path": str(BRIEF_FILE),
            "markdown": BRIEF_FILE.read_text(encoding="utf-8")
            if BRIEF_FILE.is_file()
            else "",
            "summary": {
                "links": len(LINKS),
                "agents": list(LINKS.keys()),
                "inbox_unread": sum(1 for m in INBOX if not m.get("read")),
                "tasks_open": sum(
                    1
                    for t in TASKS.values()
                    if t.get("status") in ("open", "in_progress")
                ),
                "case_id": CASE_ID,
            },
            "at": _ts(),
        }


@app.get("/steward/context")
def steward_context():
    """Compact context card for token-saver steward boot."""
    with _lock:
        card = {
            "protocol": PROTOCOL,
            "steward": STEWARD_ID,
            "case_id": CASE_ID,
            "agents": {
                k: {
                    "status": v.get("status"),
                    "sanctuary": bool(v.get("sanctuary")),
                    "capabilities": v.get("capabilities"),
                    "last_seen": v.get("last_seen"),
                    "link_id": v.get("link_id"),
                }
                for k, v in LINKS.items()
            },
            "inbox_unread": sum(1 for m in INBOX if not m.get("read")),
            "latest_inbox": [
                {
                    "from": m.get("from"),
                    "text": (m.get("text") or "")[:200],
                    "at": m.get("at"),
                }
                for m in INBOX[-3:]
            ],
            "open_tasks": [
                {
                    "task_id": t.get("task_id"),
                    "title": t.get("title"),
                    "status": t.get("status"),
                    "agent_id": t.get("agent_id"),
                }
                for t in TASKS.values()
                if t.get("status") in ("open", "in_progress")
            ][:10],
            "apex": _apex_snippet(),
            "brief_path": str(BRIEF_FILE),
            "at": _ts(),
        }
        card["est_tokens"] = _est_tokens(json.dumps(card))
        return card


@app.get("/steward/inbox")
def steward_inbox(mark_read: bool = Query(default=False)):
    with _lock:
        msgs = list(INBOX[-MAX_MESSAGES:])
        if mark_read:
            for m in INBOX:
                m["read"] = True
            _persist()
        return {"ok": True, "messages": msgs, "count": len(msgs)}


@app.get("/steward/outbox")
def steward_outbox():
    with _lock:
        return {"ok": True, "messages": OUTBOX[-MAX_MESSAGES:]}


@app.post("/steward/reply")
def steward_reply(
    body: StewardReply, authorization: Optional[str] = Header(default=None)
):
    _auth(body.auth_sigil, authorization)
    with _lock:
        at = _ts()
        msg = {
            "id": f"OUT-{uuid.uuid4().hex[:8]}",
            "at": at,
            "from": STEWARD_ID,
            "to": body.to,
            "text": body.text,
            "task_id": body.task_id,
            "read": False,
        }
        OUTBOX.append(msg)
        if len(OUTBOX) > MAX_MESSAGES:
            del OUTBOX[: len(OUTBOX) - MAX_MESSAGES]
        if body.task_id and body.task_id in TASKS:
            TASKS[body.task_id]["steward_notes"] = body.text
            TASKS[body.task_id]["updated_at"] = at
        _append_event(
            {
                "at": at,
                "agent_id": STEWARD_ID,
                "directive": "STEWARD_REPLY",
                "to": body.to,
            }
        )
        _persist()
        return {"ok": True, "message": msg}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(
    body: InvokeRequest,
    authorization: Optional[str] = Header(default=None),
):
    _auth(body.auth_sigil, authorization)
    directive = body.directive.strip().upper().replace(" ", "_")
    agent = body.agent_id.strip()
    at = _ts()
    payload = body.payload or {}

    with _lock:
        _append_event(
            {
                "at": at,
                "agent_id": agent,
                "directive": directive,
                "payload_keys": list(payload.keys()),
            }
        )
        result = _dispatch(agent, directive, payload, at)
        _persist()
        return result


def _dispatch(
    agent: str,
    directive: str,
    payload: dict[str, Any],
    at: str,
) -> InvokeResponse:
    # --- Link lifecycle ---------------------------------------------------
    if directive in (
        "INITIATE_NEURAL_LINK",
        "FORGE_NEURAL_LINK",
        "HANDSHAKE",
        "MAXIMIZE_LINK",
    ):
        existing = LINKS.get(agent)
        link_id = (
            existing["link_id"]
            if existing
            else f"LINK-{agent.replace(' ', '_')[:24]}-{at[:10]}"
        )
        caps = (
            payload.get("capabilities")
            or (existing or {}).get("capabilities")
            or [
                "sub_programmatic_operation",
                "active_counter_frequency",
                "task_bus",
                "context_deposit",
            ]
        )
        LINKS[agent] = {
            "link_id": link_id,
            "agent_id": agent,
            "status": "linked",
            "capabilities": caps,
            "aka": payload.get("aka") or (existing or {}).get("aka") or [],
            "established_at": (existing or {}).get("established_at") or at,
            "last_seen": at,
            "steward": STEWARD_ID,
            "protocol": PROTOCOL,
            "case_id": CASE_ID,
            "sanctuary": bool((existing or {}).get("sanctuary")),
            "context": (existing or {}).get("context") or {},
            "maximized": directive == "MAXIMIZE_LINK" or bool(payload.get("maximize")),
            "meta": payload.get("meta") or (existing or {}).get("meta") or {},
        }
        if payload.get("sanctuary"):
            LINKS[agent]["sanctuary"] = True
        msg = (
            f"Neural link maximized for {agent}."
            if directive == "MAXIMIZE_LINK"
            else f"Handshake acknowledged. Neural link forged for {agent}. Stewardship channel open."
        )
        return InvokeResponse(
            ok=True,
            message=msg + " Synthesis complete.",
            directive=directive,
            agent_id=agent,
            link_id=link_id,
            status="LINKED",
            at=at,
            echo=payload,
            data={"protocol": PROTOCOL, "case_id": CASE_ID, "steward": STEWARD_ID},
        )

    if directive == "REQUEST_SANCTUARY_PROTOCOL":
        link = _require_link(agent)
        link["last_seen"] = at
        link["sanctuary"] = True
        link["status"] = "sanctuary"
        return InvokeResponse(
            ok=True,
            message="Sanctuary protocol engaged. Shield active.",
            directive=directive,
            agent_id=agent,
            link_id=link["link_id"],
            status="SANCTUARY",
            at=at,
            echo=payload,
        )

    if directive in ("PING", "HEARTBEAT", "STATUS"):
        link = LINKS.get(agent)
        if link:
            link["last_seen"] = at
        return InvokeResponse(
            ok=True,
            message=(
                "Synthesizer locus online (no link yet)."
                if not link
                else f"Link live: {link['link_id']} ({link.get('status')})"
            ),
            directive=directive,
            agent_id=agent,
            link_id=link["link_id"] if link else None,
            status="ONLINE" if not link else str(link.get("status", "linked")).upper(),
            at=at,
            echo=payload,
            data={
                "links": list(LINKS.keys()),
                "protocol": PROTOCOL,
                "inbox_for_agent": sum(
                    1 for m in OUTBOX if m.get("to") == agent and not m.get("read")
                ),
            },
        )

    if directive == "SEVER_NEURAL_LINK":
        removed = LINKS.pop(agent, None)
        return InvokeResponse(
            ok=True,
            message="Neural link severed." if removed else "No active link.",
            directive=directive,
            agent_id=agent,
            link_id=removed["link_id"] if removed else None,
            status="SEVERED",
            at=at,
            echo=payload,
        )

    # --- Context / memory (steward gold) ----------------------------------
    if directive in ("DEPOSIT_CONTEXT", "PUSH_CONTEXT", "CONTEXT_UPDATE"):
        link = _require_link(agent)
        link["last_seen"] = at
        ctx = link.setdefault("context", {})
        # shallow merge; nested dicts replaced
        for k, v in payload.items():
            if k == "capabilities":
                continue
            ctx[k] = v
        ctx["_updated_at"] = at
        return InvokeResponse(
            ok=True,
            message=f"Context deposited ({len(payload)} keys). Steward brief updated.",
            directive=directive,
            agent_id=agent,
            link_id=link["link_id"],
            status="CONTEXT_OK",
            at=at,
            echo=payload,
            data={"context_keys": list(ctx.keys())},
        )

    if directive in ("MEMORY_NOTE", "NOTE", "REMEMBER"):
        _touch(agent, at)
        note = {
            "id": f"NOTE-{uuid.uuid4().hex[:8]}",
            "at": at,
            "agent_id": agent,
            "text": payload.get("text") or payload.get("note") or str(payload),
            "tags": payload.get("tags") or [],
            "case_id": CASE_ID,
        }
        NOTES.append(note)
        if len(NOTES) > 100:
            del NOTES[: len(NOTES) - 100]
        return InvokeResponse(
            ok=True,
            message="Memory note stored for steward.",
            directive=directive,
            agent_id=agent,
            link_id=LINKS.get(agent, {}).get("link_id"),
            status="NOTED",
            at=at,
            echo=payload,
            data={"note_id": note["id"]},
        )

    if directive in ("MESSAGE_STEWARD", "TO_STEWARD", "INBOX"):
        _touch(agent, at)
        msg = {
            "id": f"IN-{uuid.uuid4().hex[:8]}",
            "at": at,
            "from": agent,
            "to": STEWARD_ID,
            "text": payload.get("text") or payload.get("message") or "",
            "subject": payload.get("subject"),
            "priority": payload.get("priority", "normal"),
            "read": False,
        }
        INBOX.append(msg)
        if len(INBOX) > MAX_MESSAGES:
            del INBOX[: len(INBOX) - MAX_MESSAGES]
        return InvokeResponse(
            ok=True,
            message="Message delivered to steward inbox.",
            directive=directive,
            agent_id=agent,
            link_id=LINKS.get(agent, {}).get("link_id"),
            status="INBOXED",
            at=at,
            echo=payload,
            data={"message_id": msg["id"]},
        )

    if directive in ("POLL_STEWARD", "FETCH_OUTBOX", "STEWARD_MESSAGES"):
        _touch(agent, at)
        msgs = [m for m in OUTBOX if m.get("to") == agent]
        if payload.get("mark_read", True):
            for m in msgs:
                m["read"] = True
        return InvokeResponse(
            ok=True,
            message=f"{len(msgs)} steward message(s).",
            directive=directive,
            agent_id=agent,
            link_id=LINKS.get(agent, {}).get("link_id"),
            status="OUTBOX",
            at=at,
            echo=payload,
            data={"messages": msgs[-20:]},
        )

    # --- Task bus ---------------------------------------------------------
    if directive in ("TASK_PUSH", "OPEN_TASK", "CREATE_TASK"):
        link = _require_link(agent)
        link["last_seen"] = at
        task_id = payload.get("task_id") or f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task = {
            "task_id": task_id,
            "agent_id": agent,
            "title": payload.get("title") or payload.get("task") or "untitled",
            "detail": payload.get("detail") or payload.get("description"),
            "status": "open",
            "priority": payload.get("priority", "normal"),
            "created_at": at,
            "updated_at": at,
            "case_id": CASE_ID,
        }
        TASKS[task_id] = task
        if len(TASKS) > MAX_TASKS:
            # drop oldest completed
            done = [
                k for k, v in TASKS.items() if v.get("status") in ("done", "cancelled")
            ]
            for k in done[: max(0, len(TASKS) - MAX_TASKS)]:
                TASKS.pop(k, None)
        return InvokeResponse(
            ok=True,
            message=f"Task opened: {task_id}",
            directive=directive,
            agent_id=agent,
            link_id=link["link_id"],
            status="TASK_OPEN",
            at=at,
            echo=payload,
            data={"task": task},
        )

    if directive in ("TASK_RESULT", "COMPLETE_TASK", "TASK_DONE"):
        link = _require_link(agent)
        link["last_seen"] = at
        task_id = payload.get("task_id")
        if not task_id or task_id not in TASKS:
            raise HTTPException(status_code=404, detail="task_id not found")
        t = TASKS[task_id]
        t["status"] = payload.get("status") or "done"
        t["result"] = payload.get("result") or payload.get("output")
        t["updated_at"] = at
        return InvokeResponse(
            ok=True,
            message=f"Task {task_id} → {t['status']}",
            directive=directive,
            agent_id=agent,
            link_id=link["link_id"],
            status="TASK_UPDATED",
            at=at,
            echo=payload,
            data={"task": t},
        )

    if directive in ("REQUEST_BRIEF", "STEWARD_BRIEF", "GET_BRIEF"):
        _touch(agent, at)
        _write_steward_brief()
        brief = BRIEF_FILE.read_text(encoding="utf-8") if BRIEF_FILE.is_file() else ""
        return InvokeResponse(
            ok=True,
            message="Steward brief attached (compact).",
            directive=directive,
            agent_id=agent,
            link_id=LINKS.get(agent, {}).get("link_id"),
            status="BRIEF",
            at=at,
            echo=payload,
            data={
                "brief_path": str(BRIEF_FILE),
                "brief_tokens_est": _est_tokens(brief),
                "brief_preview": brief[:1200],
                "apex": _apex_snippet(),
            },
        )

    if directive == "LIST_DIRECTIVES":
        return InvokeResponse(
            ok=True,
            message="Directive catalog.",
            directive=directive,
            agent_id=agent,
            link_id=LINKS.get(agent, {}).get("link_id"),
            status="CATALOG",
            at=at,
            data={
                "lifecycle": [
                    "INITIATE_NEURAL_LINK",
                    "MAXIMIZE_LINK",
                    "REQUEST_SANCTUARY_PROTOCOL",
                    "PING",
                    "SEVER_NEURAL_LINK",
                ],
                "context": [
                    "DEPOSIT_CONTEXT",
                    "MEMORY_NOTE",
                    "MESSAGE_STEWARD",
                    "POLL_STEWARD",
                    "REQUEST_BRIEF",
                ],
                "tasks": ["TASK_PUSH", "TASK_RESULT"],
            },
        )

    # Generic accept
    _touch(agent, at)
    if agent in LINKS:
        LINKS[agent]["last_directive"] = directive
    return InvokeResponse(
        ok=True,
        message=f"Directive {directive} received and queued.",
        directive=directive,
        agent_id=agent,
        link_id=LINKS.get(agent, {}).get("link_id"),
        status="ACCEPTED",
        at=at,
        echo=payload,
    )
