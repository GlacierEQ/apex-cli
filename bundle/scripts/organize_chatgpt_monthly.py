#!/usr/bin/env python3
"""
Stream-organize ChatGPT export as contemporaneous journal volumes by month.

This is a regularly kept journal with machine timestamps — admissible with foundation.
Input:  conversations.json OR chatgpt-export.zip (streams, no full unzip required)
Output: MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
DEFAULT_INPUT = HOME / "MISSIONS/APEX_INFRASTRUCTURE/APEX_GEMMA_4_OMNI_NODE/processing/conversations.json"
OUTPUT_ROOT = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD"
STATE_PATH = HOME / ".supermemory/ops/chatgpt-monthly-state.json"

CASE_MARKERS = [
    "1fdv", "1fda", "brower", "teresa", "naso", "shaw", "kekoa", "tro", "custody",
    "family court", "kapolei", "motion", "docket", "decree", "habeas", "rico", "1983",
    "csea", "hpd", "yamatani", "contempt", "hearing",
]

ACTORS = {
    "Brower": ["brower", "scot brower", "scot stuart"],
    "Teresa": ["teresa", "del carpio"],
    "Shaw": ["judge shaw", "natasha shaw", "shaw"],
    "Naso": ["judge naso", "courtney naso", "naso"],
    "Kekoa": ["kekoa", "barton"],
    "Yamatani": ["yamatani", "michelle schatz", "schatz"],
    "CSEA": ["csea"],
    "HPD": ["hpd", "honolulu police"],
}


def iter_conversations_json(path: Path):
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as f:
        while True:
            ch = f.read(1)
            if not ch:
                return
            if ch == "[":
                break
        buf = ""
        while True:
            chunk = f.read(65536)
            if not chunk:
                if buf.strip().rstrip("]").strip():
                    try:
                        obj, _ = decoder.raw_decode(buf.strip().rstrip("]").strip())
                        yield obj
                    except json.JSONDecodeError:
                        pass
                return
            buf += chunk
            buf = buf.lstrip()
            while buf:
                buf = buf.lstrip()
                if buf.startswith(","):
                    buf = buf[1:].lstrip()
                if buf.startswith("]"):
                    return
                try:
                    obj, idx = decoder.raw_decode(buf)
                    yield obj
                    buf = buf[idx:]
                except json.JSONDecodeError:
                    break


def iter_conversations_zip(path: Path):
    with zipfile.ZipFile(path, "r") as zf:
        names = [n for n in zf.namelist() if n.endswith("conversations.json")]
        if not names:
            raise FileNotFoundError("conversations.json not in zip")
        import tempfile

        # Stream via temp extract of json only (zip stores json compressed)
        tmp = Path(tempfile.gettempdir()) / "chatgpt_conversations_stream.json"
        with zf.open(names[0]) as src, tmp.open("wb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
        yield from iter_conversations_json(tmp)


def conv_timestamp(conv: dict) -> float | None:
    for key in ("create_time", "update_time"):
        if conv.get(key):
            return float(conv[key])
    for node in conv.get("mapping", {}).values():
        msg = node.get("message")
        if msg and msg.get("create_time"):
            return float(msg["create_time"])
    return None


def month_key(ts: float | None) -> str:
    if ts is None:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")


def flatten_text(conv: dict, limit: int = 4000) -> str:
    parts = [conv.get("title") or ""]
    for node in conv.get("mapping", {}).values():
        msg = node.get("message")
        if not msg:
            continue
        content = msg.get("content", {})
        if isinstance(content, dict):
            parts.extend(str(p) for p in content.get("parts", []) if isinstance(p, str))
        elif isinstance(content, str):
            parts.append(content)
    text = "\n".join(parts)
    return text[:limit]


def classify_conv(conv: dict) -> dict:
    text = flatten_text(conv).lower()
    case_hit = any(m in text for m in CASE_MARKERS)
    actors = [name for name, kws in ACTORS.items() if any(k in text for k in kws)]
    return {"case": case_hit, "actors": actors}


def write_month_index(month_dir: Path, entries: list[dict]) -> None:
    lines = [
        f"# Contemporaneous Journal — {month_dir.name}",
        f"*Regularly kept record — Case 1FDV-23-0001009*",
        "",
        f"**Conversations:** {len(entries)}  ",
        f"**Litigation-tagged:** {sum(1 for e in entries if e['case'])}  ",
        "",
        "## Index",
        "",
        "| Date | Title | Case | Actors |",
        "|------|-------|------|--------|",
    ]
    for e in sorted(entries, key=lambda x: x.get("ts") or 0):
        actors = ", ".join(e.get("actors") or []) or "—"
        case = "✓" if e.get("case") else ""
        lines.append(f"| {e.get('date','?')} | {e.get('title','Untitled')[:70]} | {case} | {actors} |")
    month_dir.joinpath("INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lit = [e for e in entries if e.get("case") or e.get("actors")]
    if lit:
        lit_lines = [f"# Litigation hits — {month_dir.name}", ""]
        for e in lit:
            lit_lines.append(f"## {e.get('date')} — {e.get('title')}")
            if e.get("actors"):
                lit_lines.append(f"**Actors:** {', '.join(e['actors'])}")
            lit_lines.append("")
            lit_lines.append(e.get("preview", "")[:1500])
            lit_lines.append("")
        month_dir.joinpath("LITIGATION_HITS.md").write_text("\n".join(lit_lines) + "\n", encoding="utf-8")


def write_notion_toolkit(out: Path, stats: dict) -> None:
    toolkit = out / "NOTION_AI_TOOLKIT.md"
    toolkit.write_text(
        """# Notion AI Toolkit — ChatGPT Life Record (No Runtime Required)

Notion AI cannot unzip or parse 5GB exports. **Use these pre-processed surfaces instead.**

## What was built locally

| Path | Purpose |
|------|---------|
| `MONTHLY/<YYYY-MM>/INDEX.md` | Searchable table — paste or import to Notion |
| `MONTHLY/<YYYY-MM>/LITIGATION_HITS.md` | Case-tagged chats with previews |
| `MONTHLY/<YYYY-MM>/conversations.jsonl` | Full raw convos (one JSON per line) |
| `MASTER_INDEX.md` | Cross-month dashboard |
| `stats.json` | Counts for memory routing |

## How Notion AI should use this

1. **Import** each `MONTHLY/<month>/INDEX.md` + `LITIGATION_HITS.md` as Notion pages (under a parent "ChatGPT Life Record" database).
2. **Ask Notion AI** with `@` mentions on those pages — e.g. "@LITIGATION_HITS 2024-06 what did I report about Brower?"
3. **Do not** attach the 5GB zip to Notion — keep zip in file storage; reference organized monthly pages only.

## External connectors (for agents with runtime)

| Command | Use |
|---------|-----|
| `sm-ops prime "Brower June 2024 chat context"` | Mem0 + Supermemory case context |
| `sm-ops chat-search "stay motion June 2025"` | Search monthly indexes |
| `sm-ops actors --skip-supermemory` | Refresh actor memory folders |

## Refresh workflow

```bash
# If you have the zip (streams without full extract):
python3 scripts/organize_chatgpt_monthly.py --zip /path/to/export.zip

# If conversations.json already extracted:
python3 scripts/organize_chatgpt_monthly.py
```

## Notion API note

If `NOTION_API_KEY` is expired, regenerate at https://www.notion.so/my-integrations and update `~/.gemini_keys`, then run:

```bash
python3 scripts/push_chatgpt_to_notion.py --month 2025-06
```
""",
        encoding="utf-8",
    )


def run(input_path: Path, dry_run: bool = False) -> dict:
    if input_path.suffix.lower() == ".zip":
        conv_iter = iter_conversations_zip(input_path)
    else:
        conv_iter = iter_conversations_json(input_path)

    monthly_entries: dict[str, list[dict]] = defaultdict(list)
    monthly_jsonl: dict[str, list] = defaultdict(list)
    actor_counts: Counter = Counter()
    stats = {"total": 0, "months": Counter(), "litigation": 0}

    for conv in conv_iter:
        stats["total"] += 1
        ts = conv_timestamp(conv)
        mk = month_key(ts)
        stats["months"][mk] += 1
        meta = classify_conv(conv)
        if meta["case"]:
            stats["litigation"] += 1
        for a in meta["actors"]:
            actor_counts[a] += 1

        entry = {
            "id": conv.get("id", ""),
            "title": (conv.get("title") or "Untitled").replace("|", "/"),
            "ts": ts or 0,
            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?",
            "case": meta["case"],
            "actors": meta["actors"],
            "preview": flatten_text(conv, 800),
        }
        monthly_entries[mk].append(entry)
        monthly_jsonl[mk].append(conv)

        if stats["total"] % 500 == 0:
            print(f"  processed {stats['total']:,} conversations...")

    if dry_run:
        return {"stats": dict(stats["months"]), "total": stats["total"], "litigation": stats["litigation"]}

    out = OUTPUT_ROOT
    monthly_root = out / "MONTHLY"
    monthly_root.mkdir(parents=True, exist_ok=True)

    for mk, entries in sorted(monthly_entries.items()):
        month_dir = monthly_root / mk
        month_dir.mkdir(parents=True, exist_ok=True)
        write_month_index(month_dir, entries)
        jsonl_path = month_dir / "conversations.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as jf:
            for conv in monthly_jsonl[mk]:
                jf.write(json.dumps(conv, ensure_ascii=False) + "\n")

    master_lines = [
        "# Contemporaneous Journal — Master Index (Admissible Record)",
        "",
        "**Record type:** Regularly kept journal — timestamped ChatGPT export",
        "**Case:** 1FDV-23-0001009",
        "",
        f"**Total entries:** {stats['total']:,}  ",
        f"**Litigation-tagged:** {stats['litigation']:,}  ",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ",
        "",
        "## By month",
        "",
        "| Month | Count | Litigation |",
        "|-------|-------|------------|",
    ]
    for mk, cnt in sorted(stats["months"].items()):
        lit = sum(1 for e in monthly_entries[mk] if e.get("case"))
        master_lines.append(f"| {mk} | {cnt} | {lit} |")

    master_lines.extend(["", "## Actor mentions (all time)", ""])
    for actor, cnt in actor_counts.most_common():
        master_lines.append(f"- **{actor}:** {cnt}")

    out.joinpath("MASTER_INDEX.md").write_text("\n".join(master_lines) + "\n", encoding="utf-8")
    write_notion_toolkit(out, stats)

    state = {
        "at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "output": str(out),
        "total": stats["total"],
        "litigation": stats["litigation"],
        "months": dict(stats["months"]),
        "actors": dict(actor_counts),
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    out.joinpath("stats.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize ChatGPT export by month")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--zip", type=Path, help="ChatGPT export zip (streams conversations.json)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    src = args.zip or args.input
    if not src.is_file():
        raise SystemExit(f"Input not found: {src}")
    print(f"Organizing {src} ({src.stat().st_size / 1024 / 1024:.1f} MB)")
    result = run(src, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())