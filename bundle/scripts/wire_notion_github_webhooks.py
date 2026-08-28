#!/usr/bin/env python3
"""Wire GlacierEQ repos → Notion Worker onGitHubEvent webhook."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
GATE = HOME / ".operator_key_vault/gatekeeper.env"
OUT = HOME / ".apex/NOTION_GITHUB_WEBHOOKS.json"

WEBHOOK_URL = (
    "https://www.notion.so/webhooks/worker/"
    "506d0b07-3284-4b63-a6c9-c5583176045c/"
    "019eb9e7-792b-76a2-89c5-cd52e3a1d4f9/"
    "aA6tTDpGkZxjXUim/onGitHubEvent"
)

OWNER = "GlacierEQ"
WORKER_ID = "019eb9e7-792b-76a2-89c5-cd52e3a1d4f9"

CORE_REPOS = [
    "apex-github-worker",
    "apex-stack",
    "Pro-comet-agent",
    "Pro-apex-fs-commander",
    "Pro_Code",
    "pro-code",
    "apex-workers-runtime",
]

EVENTS = [
    "push",
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "issues",
    "issue_comment",
    "release",
    "create",
    "delete",
    "repository",
    "workflow_run",
    "check_run",
    "commit_comment",
    "discussion",
    "discussion_comment",
    "deployment",
    "deployment_status",
    "status",
    "fork",
    "public",
    "package",
    "watch",
    "label",
    "milestone",
]

APEX_PATTERNS = re.compile(
    r"^(apex|pro[-_]|glacier|aspen|legal|notion|worker|nexus|comet|cataclysm|sovereign|"
    r"digital-law|fileboss|mega-pdf|stealth|mem0|supermemory|unified-memory|sm-ops|operator|"
    r"colossus|infra|mission|microwave|computer[-_]?user|qmo|omni-crawl|everything-mcp)",
    re.I,
)
LEGAL_PATTERNS = re.compile(
    r"legal|court|juris|brady|rico|forensic|dfir|evidence|pacer|eyecite|disclosure|scribe",
    re.I,
)
EXCLUDE = re.compile(
    r"^(Z-BACKUP-|chatgpt|claude-|openai-|langchain|n8n-|vscode$|selenium|ollama-|gemini-|copilot)",
    re.I,
)


def _load_token() -> str:
    found: dict[str, str] = {}
    if GATE.is_file():
        for line in GATE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line.startswith("export ") or "=" not in line:
                continue
            k, v = line[7:].split("=", 1)
            if k.startswith("GITHUB_"):
                found[k] = v.strip().strip('"').strip("'")
    for key in (
        "GITHUB_TOKEN_PRIMARY",
        "GITHUB_MASTER_TOKEN",
        "GITHUB_PAT",
        "GITHUB_TOKEN",
    ):
        if found.get(key):
            return found[key]
    token = (
        os.environ.get("GITHUB_TOKEN_PRIMARY") or os.environ.get("GITHUB_TOKEN") or ""
    )
    if token:
        return token
    raise SystemExit("No GITHUB_TOKEN — set GITHUB_TOKEN_PRIMARY in gatekeeper.env")


def _api(token: str, method: str, path: str, body: dict | None = None) -> dict | list:
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "apex-notion-webhook-wirer",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 3:
                time.sleep(2**attempt)
                continue
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"GitHub API {e.code}: {detail}") from e
        except Exception:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            raise
    return {}


def _paginate(token: str, path: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = _api(token, "GET", f"{path}{sep}per_page=100&page={page}")
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.25)
    return rows


def discover_repos(token: str, mode: str) -> list[str]:
    if mode == "core":
        return list(CORE_REPOS)

    public_rows = _paginate(token, f"/users/{OWNER}/repos?type=all&sort=pushed")
    owner_rows: list[dict] = []
    try:
        owner_rows = _paginate(token, "/user/repos?affiliation=owner&sort=pushed")
    except Exception:
        pass

    by_name: dict[str, dict] = {}
    for row in public_rows + owner_rows:
        if row.get("owner", {}).get("login", "").lower() != OWNER.lower():
            continue
        by_name[row["name"]] = row

    if mode == "private":
        return sorted(
            name
            for name, row in by_name.items()
            if row.get("private") and not row.get("archived")
        )

    if mode == "all":
        return sorted(name for name, row in by_name.items() if not row.get("archived"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    selected: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name not in seen and name in by_name and not by_name[name].get("archived"):
            selected.append(name)
            seen.add(name)

    for name in CORE_REPOS:
        add(name)

    for name, row in sorted(by_name.items()):
        if not row.get("fork"):
            add(name)

    for name, row in sorted(by_name.items()):
        if APEX_PATTERNS.search(name) or LEGAL_PATTERNS.search(name):
            add(name)

    for name, row in sorted(by_name.items()):
        if row.get("fork") or EXCLUDE.search(name):
            continue
        pushed = row.get("pushed_at")
        if not pushed:
            continue
        dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        if dt >= cutoff:
            add(name)

    return selected


def list_hooks(token: str, repo: str) -> list:
    return _api(token, "GET", f"/repos/{OWNER}/{repo}/hooks")


def hook_exists(hooks: list, url: str) -> dict | None:
    for h in hooks:
        if h.get("config", {}).get("url") == url:
            return h
    return None


def create_hook(token: str, repo: str) -> dict:
    return _api(
        token,
        "POST",
        f"/repos/{OWNER}/{repo}/hooks",
        {
            "name": "web",
            "active": True,
            "events": EVENTS,
            "config": {
                "url": WEBHOOK_URL,
                "content_type": "json",
                "insecure_ssl": "0",
            },
        },
    )


def update_hook(token: str, repo: str, hook_id: int) -> dict:
    return _api(
        token,
        "PATCH",
        f"/repos/{OWNER}/{repo}/hooks/{hook_id}",
        {
            "active": True,
            "events": EVENTS,
            "config": {
                "url": WEBHOOK_URL,
                "content_type": "json",
                "insecure_ssl": "0",
            },
        },
    )


def ping_hook(token: str, repo: str, hook_id: int) -> None:
    _api(token, "POST", f"/repos/{OWNER}/{repo}/hooks/{hook_id}/pings", {})


def wire_repo(token: str, repo: str) -> dict:
    entry = {"repo": f"{OWNER}/{repo}", "status": "pending"}
    try:
        hooks = list_hooks(token, repo)
        existing = hook_exists(hooks, WEBHOOK_URL)
        if existing:
            updated = update_hook(token, repo, existing["id"])
            ping_hook(token, repo, existing["id"])
            entry.update(
                {
                    "status": "updated",
                    "hook_id": existing["id"],
                    "events": updated.get("events", EVENTS),
                }
            )
        else:
            created = create_hook(token, repo)
            ping_hook(token, repo, created["id"])
            entry.update(
                {
                    "status": "created",
                    "hook_id": created["id"],
                    "events": created.get("events", EVENTS),
                }
            )
    except Exception as e:
        entry.update({"status": "error", "detail": str(e)[:200]})
    time.sleep(0.35)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wire GlacierEQ repos to Notion GitHub worker"
    )
    parser.add_argument(
        "--mode",
        choices=("core", "max", "private", "all"),
        default="max",
        help="core=7 Pro repos | max=originals+APEX/legal/recent | private=all private | all=non-archived",
    )
    parser.add_argument("--dry-run", action="store_true", help="List targets only")
    args = parser.parse_args()

    token = _load_token()
    repos = discover_repos(token, args.mode)
    print(f"Mode={args.mode} targets={len(repos)} events={len(EVENTS)}")

    if args.dry_run:
        for repo in repos:
            print(f"  {OWNER}/{repo}")
        return 0

    results = []
    for repo in repos:
        entry = wire_repo(token, repo)
        results.append(entry)
        mark = entry["status"].upper()
        suffix = (
            f" hook={entry.get('hook_id')}"
            if entry.get("hook_id")
            else f" — {entry.get('detail', '')}"
        )
        print(f"[{mark}] {entry['repo']}{suffix}")

    try:
        owner_rows = _paginate(token, "/user/repos?affiliation=owner&sort=pushed")
        glacier = {
            r["name"]: r
            for r in owner_rows
            if r.get("owner", {}).get("login", "").lower() == OWNER.lower()
        }
        wired_ok = [
            r["repo"].split("/", 1)[1]
            for r in results
            if r["status"] in ("created", "updated")
        ]
        visibility = {
            "private_wired": sum(
                1 for n in wired_ok if glacier.get(n, {}).get("private")
            ),
            "public_wired": sum(
                1 for n in wired_ok if n in glacier and not glacier[n].get("private")
            ),
            "private_total_owner": sum(
                1
                for r in glacier.values()
                if r.get("private") and not r.get("archived")
            ),
            "public_total_owner": sum(
                1
                for r in glacier.values()
                if not r.get("private") and not r.get("archived")
            ),
        }
    except Exception:
        visibility = {}

    payload = {
        "at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "webhook_url": WEBHOOK_URL,
        "worker_id": WORKER_ID,
        "events": EVENTS,
        "repos": results,
        "stats": {
            "targets": len(repos),
            "ok": sum(1 for r in results if r["status"] in ("created", "updated")),
            "errors": sum(1 for r in results if r["status"] == "error"),
            **visibility,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nManifest: {OUT}")
    print(
        f"OK {payload['stats']['ok']}/{len(repos)} | errors {payload['stats']['errors']}"
    )
    return 0 if payload["stats"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
