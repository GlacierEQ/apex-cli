#!/usr/bin/env python3
"""
Route litigation memories, plans, and tiered archive evidence into BY_ACTOR folders.

Sources: Mem0 cloud, Supermemory search, MEM0_ACTIVE_CONTEXT_ORGANIZED.md,
         ACTORS/*.md, CONSOLIDATED_ARCHIVE BY_ACTOR trees
Target:  MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/EVIDENCE/BY_ACTOR/<Actor>/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
BY_ACTOR = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/EVIDENCE/BY_ACTOR"
ACTORS_PLANS = HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/ACTORS"
ORGANIZED_MD = (
    HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/MEM0_ACTIVE_CONTEXT_ORGANIZED.md"
)
PORTFOLIOS = (
    HOME / "MISSIONS/AEON_777/Pro-AEON-777/1FDV-23-0001009_MASTER/ACTOR_PORTFOLIOS"
)
STATE_PATH = HOME / ".supermemory/ops/actor-organize-state.json"
VAULT = (
    HOME
    / "MISSIONS/AEON_777/CORE_MISSION/AEON-BRAIN-777/02_EVIDENCE_VAULT/CONSOLIDATED_ARCHIVE"
)

ARCHIVE_BY_ACTOR_SOURCES = [
    VAULT / "FINAL_FEDERAL_STRIKE_PACKAGE/EVIDENCE/BY_ACTOR",
    VAULT / "CASE_STRUCTURE/EVIDENCE/BY_ACTOR",
    VAULT / "Pro-AEON-777/02_EVIDENCE/BY_ACTOR",
    VAULT / "Pro-AEON-777/02_EVIDENCE/THE_CATACLYSM/EVIDENCE/BY_ACTOR",
]

# Archive folder names that are not actor slugs
ARCHIVE_SKIP_DIRS = {"00_INGEST", ".git", "__pycache__"}

# slug -> display name, keywords, portfolio dir name, plan file prefixes
ACTOR_REGISTRY: dict[str, dict] = {
    "Teresa": {
        "name": "Teresa Del Carpio",
        "keywords": [
            "teresa",
            "del carpio",
            "exh-a-01-teresa",
            "petitioner",
            "plaintiff motion",
        ],
        "portfolio": "TERESA_DEL_CARPIO",
        "plans": ["01_TERESA", "TERESA_DEL_CARPIO", "DISMANTLE_TERESA"],
    },
    "Brower": {
        "name": "Scot Brower",
        "keywords": [
            "brower",
            "scot brower",
            "scot stuart brower",
            "odc breach",
            "odc confidentiality",
            "opposing counsel",
        ],
        "portfolio": "BROWER_SCOT",
        "plans": ["02_BROWER", "BROWER", "SCOT_BROWER", "SCOT_STUART", "STRIKE_02"],
    },
    "Naso": {
        "name": "Judge Courtney Naso",
        "keywords": [
            "naso",
            "courtney naso",
            "judge naso",
            "plan_03_judge_naso",
            "smash_04",
        ],
        "portfolio": "JUDGE_COURTNEY_NASO",
        "plans": ["03_JUDGE_NASO", "NASO", "COURTNEY_NASO"],
    },
    "Shaw": {
        "name": "Judge Natasha Shaw",
        "keywords": [
            "natasha shaw",
            "judge shaw",
            "shaw coordination",
            "brower-shaw",
            "brower‑shaw",
            "100% denial",
            "ruling pattern",
        ],
        "portfolio": "JUDGE_NATASHA_SHAW",
        "plans": [
            "04_JUDGE_SHAW",
            "JUDGE_NATASHA_SHAW",
            "SMASH_03_JUDGE_NATASHA",
            "SHAW",
            "NATASHA_SHAW",
        ],
    },
    "Park": {
        "name": "Judge Andrew Park",
        "keywords": ["judge park", "andrew park", "plan_05_judge_park"],
        "portfolio": "JUDGE_ANDREW_PARK",
        "plans": ["05_JUDGE_PARK", "SMASH_14_JUDGE_ANDREW", "PARK", "ANDREW_PARK"],
    },
    "Dowd": {
        "name": "Judge Kyle Dowd",
        "keywords": ["judge dowd", "kyle dowd", "plan_15_judge_dowd"],
        "portfolio": "JUDGE_KYLE_DOWD",
        "plans": ["15_JUDGE_DOWD", "DOWD", "KYLE_DOWD"],
    },
    "CWS": {
        "name": "CWS Agency",
        "keywords": ["cws agency", "child welfare", "plan_06_cws", "smash_10_cws"],
        "portfolio": "CWS_AGENCY",
        "plans": ["06_CWS", "CWS", "DISMANTLE_CWS"],
    },
    "CSEA": {
        "name": "CSEA Agency",
        "keywords": ["csea", "plan_07_csea", "smash_07_csea"],
        "portfolio": "CSEA_AGENCY",
        "plans": ["07_CSEA", "CSEA", "DISMANTLE_CSEA"],
    },
    "PACT": {
        "name": "PACT Services",
        "keywords": [
            "pact services",
            "through pact",
            "supervised visitation",
            "plan_08_pact",
            "smash_11_pact",
        ],
        "portfolio": "PACT_SERVICES",
        "plans": ["08_PACT", "PACT", "DISMANTLE_PACT"],
    },
    "HPD": {
        "name": "HPD Department",
        "keywords": [
            "hpd department",
            "honolulu police",
            "police escort",
            "plan_09_hpd",
            "smash_08_hpd",
        ],
        "portfolio": "HPD_DEPARTMENT",
        "plans": ["09_HPD", "HPD"],
    },
    "Yamatani": {
        "name": "Micky Yamatani",
        "keywords": [
            "yamatani",
            "micky yamatani",
            "plan_11_yamatani",
            "smash_12_micky",
        ],
        "portfolio": "MICKY_YAMATANI",
        "plans": ["11_YAMATANI", "YAMATANI", "MICKY"],
    },
    "Smith": {
        "name": "Daniel Smith",
        "keywords": ["daniel smith", "dhhi", "plan_10_daniel", "smash_13_daniel"],
        "portfolio": "DANIEL_SMITH_DHHI",
        "plans": ["10_DANIEL", "SMITH", "DHHI", "DANIEL_SMITH", "SMASH_13"],
    },
    "Castillo": {
        "name": "Clerk Castillo",
        "keywords": [
            "clerk castillo",
            "castillo",
            "plan_12_clerk_castillo",
            "smash_05_clerk_castillo",
        ],
        "portfolio": "CLERK_CASTILLO",
        "plans": ["12_CLERK_CASTILLO", "CASTILLO", "CLERK_CASTILLO"],
    },
    "Le": {
        "name": "Clerk Le",
        "keywords": [
            "clerk le",
            "smash_06_clerk_le",
            "plan_13_clerk_le",
            "court clerk coordination",
        ],
        "portfolio": "CLERK_LE",
        "plans": ["13_CLERK_LE", "CLERK_LE", "SMASH_06_CLERK_LE"],
    },
    "QueensHospital": {
        "name": "Queens Hospital",
        "keywords": ["queens hospital", "plan_14_queens", "smash_09_queens"],
        "portfolio": "QUEENS_HOSPITAL",
        "plans": ["14_QUEENS", "QUEENS_HOSPITAL"],
    },
    "Unemployment": {
        "name": "Unemployment Agency",
        "keywords": [
            "unemployment agency",
            "plan_16_unemployment",
            "smash_16_unemployment",
        ],
        "portfolio": "UNEMPLOYMENT_AGENCY",
        "plans": ["16_UNEMPLOYMENT", "UNEMPLOYMENT"],
    },
    "Doe1": {
        "name": "Doe Defendant 1",
        "keywords": ["doe defendant 1", "smash_17_doe", "plan_17_actor", "actor_17"],
        "portfolio": "DOE_DEFENDANT_1",
        "plans": ["17_ACTOR_17", "DOE_DEFENDANT_1", "ACTOR_17"],
    },
    "Doe2": {
        "name": "Doe Defendant 2",
        "keywords": ["doe defendant 2", "smash_18", "plan_18_actor", "actor_18"],
        "portfolio": "DOE_DEFENDANT_2",
        "plans": ["18_ACTOR_18", "DOE_DEFENDANT_2", "ACTOR_18"],
    },
    "Doe3": {
        "name": "Doe Defendant 3",
        "keywords": ["doe defendant 3", "smash_19", "plan_19_actor", "actor_19"],
        "portfolio": "DOE_DEFENDANT_3",
        "plans": ["19_ACTOR_19", "DOE_DEFENDANT_3", "ACTOR_19"],
    },
    "Doe4": {
        "name": "Doe Defendant 4",
        "keywords": ["doe defendant 4", "smash_20", "plan_20_actor", "actor_20"],
        "portfolio": "DOE_DEFENDANT_4",
        "plans": ["20_ACTOR_20", "DOE_DEFENDANT_4", "ACTOR_20"],
    },
    "Doe5": {
        "name": "Doe Defendant 5",
        "keywords": ["doe defendant 5", "smash_21", "plan_21_actor", "actor_21"],
        "portfolio": "DOE_DEFENDANT_5",
        "plans": ["21_ACTOR_21", "DOE_DEFENDANT_5", "ACTOR_21"],
    },
    "Kekoa": {
        "name": "Kekoa Barton",
        "keywords": [
            "kekoa",
            "kekoa barton",
            "victim node",
            "smash_22_kekoa",
            "barton v casey",
            "1fda",
        ],
        "portfolio": "KEKOA_BARTON",
        "plans": ["22_KEKOA", "KEKOA", "KEKOA_BARTON"],
    },
    "Brysacher": {
        "name": "Erik Brysacher",
        "keywords": ["erik brysacher", "brysacher"],
        "portfolio": "ERIK_BRYSACHER",
        "plans": ["BRYSACHER", "ERIK_BRYSACHER"],
    },
    "Martin": {
        "name": "Nainoa Martin",
        "keywords": ["nainoa martin", "martin theft", "nainoa"],
        "portfolio": "NAINOA_MARTIN",
        "plans": ["MARTIN", "NAINOA", "NAINOA_MARTIN", "SMASH_23"],
    },
}

# High-value reference docs → symlink into actor EVIDENCE/references/
REFERENCE_LINKS: dict[str, list[Path]] = {
    "Brower": [
        HOME
        / "MISSIONS/THE_CATACLYSM/SUPERLUMINAL_CASE_MATRIX/background/investigations/SCOT_BROWER_INVESTIGATIVE_REPORT.md",
        HOME
        / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/ACTORS/CONTINGENCY_COMPLETE_PER_ACTOR_STRATEGY.md",
        HOME
        / "MISSIONS/APEX_INFRASTRUCTURE/aspen-grove-operator-v7/research/intelligence/actors/brower_complete_profile.md",
    ],
    "Yamatani": [
        HOME
        / "MISSIONS/APEX_INFRASTRUCTURE/aspen-grove-operator-v7/research/intelligence/actors/yamatani_profile.md",
    ],
    "Shaw": [
        HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/ACTORS/THE_22_ACTOR_MATRIX.md",
    ],
    "_CASE": [
        HOME
        / "MISSIONS/THE_CATACLYSM/SUPERLUMINAL_CASE_MATRIX/MASTER_EVIDENCE_INVENTORY.md",
        HOME
        / "MISSIONS/THE_CATACLYSM/SUPERLUMINAL_CASE_MATRIX/AEON-777/DRAFT_1983_FEDERAL_COMPLAINT.md",
        HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/MEM0_ACTIVE_CONTEXT_ORGANIZED.md",
        HOME / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/ACTORS/THE_22_ACTOR_MATRIX.md",
        HOME
        / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/MASTER_INDEX.md",
        HOME
        / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/ADMISSIBILITY_FRAME.md",
        HOME
        / "MISSIONS/THE_CATACLYSM/CASE_STRUCTURE/CHATGPT_LIFE_RECORD/NOTION_AI_TOOLKIT.md",
    ],
}

SLUG_ALIASES = {"Nos": "Naso"}

# Section context from organized MD -> default actors when fact text is case-wide
SECTION_ACTORS: dict[str, list[str]] = {
    "federal_claims": ["Brower", "Shaw", "_CASE"],
    "fraud_matrix": ["Naso", "Shaw", "Brower", "_CASE"],
    "exhibits": ["_CASE"],
    "family_court": ["Kekoa", "Teresa", "PACT", "HPD", "_CASE"],
    "infrastructure": ["_INFRA"],
    "uncategorized": ["_CASE"],
}

# Regex rules applied before keyword scan (pattern -> actors)
TEXT_RULES: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"brower[\s‑\-]+shaw", re.I), ["Brower", "Shaw"]),
    (re.compile(r"court clerk", re.I), ["Castillo", "Le"]),
    (re.compile(r"clerical correction", re.I), ["Castillo", "Le"]),
    (re.compile(r"1fda", re.I), ["Kekoa"]),
    (re.compile(r"barton v casey", re.I), ["Kekoa", "Teresa"]),
    (re.compile(r"f-00[1-9]|fraud event", re.I), ["Naso", "Shaw", "Brower", "_CASE"]),
    (re.compile(r"1fdv-23-0001009|1fdv‑23‑0001009", re.I), ["_CASE"]),
    (
        re.compile(r"goose|aspen grove|motherduck|supabase|notion|github|swarm", re.I),
        ["_INFRA"],
    ),
    (re.compile(r"vincent ai|api operations", re.I), ["_INFRA"]),
]

# Filename hints for evidence routing
FILENAME_ACTOR_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"brower|scot stuart", re.I), "Brower"),
    (re.compile(r"teresa|del carpio", re.I), "Teresa"),
    (re.compile(r"kekoa|barton", re.I), "Kekoa"),
    (re.compile(r"naso|courtney", re.I), "Naso"),
    (re.compile(r"natasha|judge shaw", re.I), "Shaw"),
    (re.compile(r"judge park|andrew park", re.I), "Park"),
    (re.compile(r"dowd", re.I), "Dowd"),
    (re.compile(r"yamatani|micky", re.I), "Yamatani"),
    (re.compile(r"daniel smith|dhhi", re.I), "Smith"),
    (re.compile(r"castillo", re.I), "Castillo"),
    (re.compile(r"clerk le", re.I), "Le"),
    (re.compile(r"nainoa|martin theft", re.I), "Martin"),
    (re.compile(r"brysacher|erik b", re.I), "Brysacher"),
    (re.compile(r"\bcsea\b", re.I), "CSEA"),
    (re.compile(r"\bcws\b", re.I), "CWS"),
    (re.compile(r"\bpact\b", re.I), "PACT"),
    (re.compile(r"\bhpd\b|honolulu police", re.I), "HPD"),
    (re.compile(r"queens hospital", re.I), "QueensHospital"),
    (re.compile(r"unemployment", re.I), "Unemployment"),
    (
        re.compile(
            r"hawaii divorce|family court|1fdv|procedural violation|habeas|mandamus|tro",
            re.I,
        ),
        "_CASE",
    ),
    (
        re.compile(
            r"casual|greeting|api keys|slack token|student email|car rental|notion.*sync|google drive",
            re.I,
        ),
        "_UNROUTED",
    ),
]


def load_keys() -> None:
    keys = HOME / ".gemini_keys"
    if keys.is_file():
        for line in keys.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def classify(text: str, section: str = "") -> list[str]:
    t = text.lower()
    hits: set[str] = set()

    for pattern, actors in TEXT_RULES:
        if pattern.search(text):
            hits.update(actors)

    for slug, meta in ACTOR_REGISTRY.items():
        for kw in meta["keywords"]:
            if kw in t:
                hits.add(slug)
                break

    # Exhibit-specific routing
    if "exhibit i" in t or "odc complaint" in t:
        hits.add("Brower")
    if "exhibit l" in t and "shaw" in t:
        hits.add("Shaw")
    if "exhibit" in t and "tro" in t:
        hits.update(["_CASE", "Teresa"])

    if not hits and section:
        hits.update(SECTION_ACTORS.get(section, ["_CASE"]))
    if not hits:
        if re.search(r"1fdv|family court|tro|decree|docket|void ground|fraud", t):
            return ["_CASE"]
        if re.search(r"infra|swarm|notion|github|vercel|mem0|supermemory", t):
            return ["_INFRA"]
        return ["_UNROUTED"]

    # Drop meta buckets if we also have concrete actors
    concrete = {h for h in hits if not h.startswith("_")}
    if concrete:
        hits -= {"_CASE", "_UNROUTED"}
    return sorted(hits)


def parse_organized_md(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    section = "uncategorized"
    blocks = re.split(r"(?=### Fact Node)", text)
    facts = []
    for block in blocks:
        sec_m = re.search(r'<a name="([^"]+)"></a>', block)
        if sec_m:
            section = sec_m.group(1)
        m_id = re.search(r"### Fact Node `\[([^\]]+)\]`.*?\(Fact #(\d+)\)", block)
        m_fact = re.search(r"- \*\*Fact\*\*: (.+)", block)
        if not m_fact:
            continue
        fact_text = m_fact.group(1).strip()
        facts.append(
            {
                "id": m_id.group(1) if m_id else "unknown",
                "num": m_id.group(2) if m_id else "?",
                "text": fact_text,
                "source": "mem0_organized_md",
                "section": section,
                "actors": classify(fact_text, section),
            }
        )
    return facts


def fetch_mem0(user_id: str = "casey") -> list[dict]:
    key = os.environ.get("MEM0_API_KEY")
    if not key:
        return []
    try:
        r = httpx.get(
            "https://api.mem0.ai/v1/memories/",
            params={"user_id": user_id, "page_size": 200},
            headers={"Authorization": f"Token {key}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = (
            data
            if isinstance(data, list)
            else data.get("results", data.get("memories", []))
        )
    except Exception:
        return []
    out = []
    for item in items or []:
        text = (item.get("memory") or item.get("text") or "").strip()
        if not text or "API_KEY" in text or "sm-ops" in text.lower():
            continue
        out.append(
            {
                "id": item.get("id", ""),
                "text": text,
                "source": f"mem0_cloud:{user_id}",
                "actors": classify(text),
                "created": item.get("created_at", ""),
            }
        )
    return out


def fetch_supermemory(actor_name: str, limit: int = 5) -> list[dict]:
    query = f"{actor_name} litigation case 1FDV-23-0001009 evidence Hawaii family court"
    try:
        proc = subprocess.run(
            [
                "sm-ops",
                "recall",
                query,
                "--limit",
                str(limit),
                "--no-rerank",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PATH": f"{HOME}/bin:{os.environ.get('PATH', '')}"},
        )
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
    except Exception:
        return []
    out = []
    for r in data.get("results", []):
        text = (r.get("memory") or "").strip()
        meta = r.get("metadata") or {}
        if meta.get("source") == "supermemory-sitemap":
            continue
        if not text or len(text) < 40:
            continue
        if "sm-ops" in text.lower() and "token savings" in text.lower():
            continue
        actors = classify(text)
        out.append(
            {
                "id": r.get("id", ""),
                "text": text,
                "source": "supermemory",
                "similarity": r.get("similarity", 0),
                "actors": actors,
            }
        )
    return out


def classify_filename(name: str) -> str | None:
    for pattern, slug in FILENAME_ACTOR_HINTS:
        if pattern.search(name):
            return slug
    return None


def count_plans(actor_dir: Path) -> int:
    plans_dir = actor_dir / "PLANS"
    if not plans_dir.is_dir():
        return 0
    return sum(1 for x in plans_dir.iterdir() if x.is_file() or x.is_symlink())


def link_plans(actor_dir: Path, slug: str, dry_run: bool) -> int:
    if slug.startswith("_"):
        return 0
    plans_dir = actor_dir / "PLANS"
    if not dry_run:
        plans_dir.mkdir(parents=True, exist_ok=True)
    meta = ACTOR_REGISTRY.get(slug, {})
    prefixes = meta.get("plans", [slug.upper()])
    count = 0
    if not ACTORS_PLANS.is_dir():
        return 0
    for f in ACTORS_PLANS.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        name = f.name.upper()
        if any(p in name for p in prefixes):
            dest = plans_dir / f.name
            if dest.exists() or dest.is_symlink():
                continue
            if not dry_run:
                dest.symlink_to(f.resolve())
            count += 1
    return count


def write_actor_index(
    actor_dir: Path,
    slug: str,
    memories: list[dict],
    plan_count: int,
    evidence_count: int,
) -> None:
    meta = ACTOR_REGISTRY.get(slug, {"name": slug.replace("_", " ").strip() or slug})
    lines = [
        f"# {meta.get('name', slug)}",
        "",
        f"**Slug:** `{slug}`  ",
        f"**Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Memories:** {len(memories)}  ",
        f"**Plans linked:** {plan_count}  ",
        f"**Evidence files:** {evidence_count}",
        "",
        "## Sources",
        "",
    ]
    sources = defaultdict(int)
    for m in memories:
        sources[m.get("source", "unknown")] += 1
    if sources:
        for src, cnt in sorted(sources.items()):
            lines.append(f"- {src}: {cnt}")
    else:
        lines.append("- (no routed memories yet)")
    lines.extend(
        [
            "",
            "## Quick files",
            "",
            "- `MEMORIES.md` — routed facts from Mem0 + Supermemory + organized index",
            "- `PLANS/` — symlinks to ACTORS strike/smash/plan docs",
            "- `EVIDENCE/` — litigation files + consolidated archive copies",
        ]
    )
    actor_dir.joinpath("ACTOR_INDEX.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_memories_md(actor_dir: Path, slug: str, memories: list[dict]) -> None:
    meta = ACTOR_REGISTRY.get(slug, {"name": slug})
    lines = [
        f"# Memories — {meta.get('name', slug)}",
        "",
        f"*Generated {datetime.now(timezone.utc).isoformat()}*",
        "",
    ]
    if not memories:
        lines.append("*No memories routed to this actor yet.*")
        lines.append("")
    seen = set()
    n = 0
    for m in memories:
        text = m["text"].strip()
        key = text[:120].lower()
        if key in seen:
            continue
        seen.add(key)
        n += 1
        lines.append(f"## {n}. [{m.get('source', '?')}]")
        if m.get("id"):
            lines.append(f"ID: `{m['id']}`")
        if m.get("section"):
            lines.append(f"Section: `{m['section']}`")
        lines.append("")
        lines.append(text)
        lines.append("")
    actor_dir.joinpath("MEMORIES.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def migrate_aliases(dry_run: bool) -> None:
    for old, new in SLUG_ALIASES.items():
        old_p = BY_ACTOR / old
        new_p = BY_ACTOR / new
        if old_p.is_dir():
            if new_p.exists():
                if not dry_run:
                    for item in old_p.iterdir():
                        dest = new_p / item.name
                        if not dest.exists():
                            shutil.move(str(item), str(dest))
                    old_p.rmdir()
                print(f"MERGE {old} -> {new}")
            elif not dry_run:
                old_p.rename(new_p)
                print(f"MIGRATE {old} -> {new}")
            else:
                print(f"MIGRATE {old} -> {new}")


def archive_dest_slug(folder_name: str, filename: str) -> str:
    """Resolve target actor for an archive file (Le folder is a known catch-all)."""
    if folder_name in ARCHIVE_SKIP_DIRS:
        return "_UNROUTED"
    if folder_name == "Le":
        hint = classify_filename(filename)
        if hint:
            return hint
        if re.search(r"clerk le|clerk_le", filename, re.I):
            return "Le"
        return "_UNROUTED"
    return SLUG_ALIASES.get(folder_name, folder_name)


def consolidate_archives(dry_run: bool) -> dict[str, int]:
    """Copy archive BY_ACTOR files into primary EVIDENCE/archive/<source>/."""
    stats: dict[str, int] = defaultdict(int)
    for src_root in ARCHIVE_BY_ACTOR_SOURCES:
        if not src_root.is_dir():
            continue
        tag = src_root.parent.name
        if src_root.parent.parent.name not in ("EVIDENCE", "02_EVIDENCE"):
            tag = src_root.parent.parent.name
        for actor_dir in src_root.iterdir():
            if not actor_dir.is_dir() or actor_dir.name.startswith("."):
                continue
            if actor_dir.name in ARCHIVE_SKIP_DIRS:
                slug = "_UNROUTED"
            else:
                slug = None
            for f in actor_dir.rglob("*"):
                if not f.is_file() or f.name == ".gitkeep":
                    continue
                target = slug or archive_dest_slug(actor_dir.name, f.name)
                if target not in ACTOR_REGISTRY and not target.startswith("_"):
                    target = "_UNROUTED"
                dest_root = BY_ACTOR / target / "EVIDENCE" / "archive" / tag
                rel = f.relative_to(actor_dir)
                dest = dest_root / rel
                if dest.exists():
                    continue
                stats[target] += 1
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
    return dict(stats)


def link_references(dry_run: bool) -> dict[str, int]:
    """Symlink canonical reference docs into actor EVIDENCE/references/."""
    stats: dict[str, int] = defaultdict(int)
    for slug, paths in REFERENCE_LINKS.items():
        ref_dir = BY_ACTOR / slug / "EVIDENCE" / "references"
        if not dry_run:
            ref_dir.mkdir(parents=True, exist_ok=True)
        for src in paths:
            if not src.is_file():
                continue
            dest = ref_dir / src.name
            if dest.exists() or dest.is_symlink():
                continue
            stats[slug] += 1
            if not dry_run:
                dest.symlink_to(src.resolve())
    return dict(stats)


def triage_unrouted(dry_run: bool) -> dict[str, int]:
    """Second-pass: salvage litigation files from _UNROUTED by filename."""
    unrouted = BY_ACTOR / "_UNROUTED"
    if not unrouted.is_dir():
        return {}
    stats: dict[str, int] = defaultdict(int)
    noise = unrouted / "_NOISE"
    for f in list(unrouted.rglob("*")):
        if not f.is_file() or f.name in (".gitkeep",):
            continue
        if "_NOISE" in f.parts:
            continue
        target = classify_filename(f.name)
        if not target or target in ("_UNROUTED", "Le"):
            # Keep obvious noise segregated
            if re.search(
                r"casual|greeting|api key|slack token|student email|car rental|notion.*sync|google drive|middleware|mcp factory|codemaster|potato peeler|supermemory mcp",
                f.name,
                re.I,
            ):
                dest = noise / f.name
                stats["_NOISE"] += 1
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        shutil.move(str(f), str(dest))
            continue
        dest = BY_ACTOR / target / "EVIDENCE" / "salvaged" / f.name
        stats[target] += 1
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                f.unlink()
            else:
                shutil.move(str(f), str(dest))
    return dict(stats)


def write_manifest(stats: dict) -> None:
    """Master dashboard at BY_ACTOR/MANIFEST.md."""
    lines = [
        "# BY_ACTOR Data Manifest",
        "",
        f"*Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "| Actor | Memories | Plans | Evidence |",
        "|-------|----------|-------|----------|",
    ]
    for slug, info in sorted(stats.get("actors", {}).items()):
        if slug.startswith("_") and slug == "_CASE":
            name = "Case-wide"
        elif slug.startswith("_"):
            name = slug
        else:
            name = ACTOR_REGISTRY.get(slug, {}).get("name", slug)
        lines.append(
            f"| {name} | {info.get('memories', 0)} | {info.get('plans', 0)} | {info.get('evidence_files', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Commands",
            "",
            "```bash",
            "sm-ops actors                  # Re-sync memories + evidence",
            "sm-ops actors --skip-supermemory",
            "```",
            "",
            "## Meta folders",
            "",
            "- `_CASE` — cross-cutting litigation facts (fraud matrix, exhibits, dockets)",
            "- `_INFRA` — APEX/stack configuration (not court evidence)",
            "- `_UNROUTED/_NOISE` — chat/infra harvest excluded from actors",
        ]
    )
    BY_ACTOR.joinpath("MANIFEST.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def cleanup_le_archive_pollution(dry_run: bool) -> int:
    """Re-route files wrongly copied under Le/EVIDENCE/archive/."""
    le_archive = BY_ACTOR / "Le" / "EVIDENCE" / "archive"
    if not le_archive.is_dir():
        return 0
    moved = 0
    for f in list(le_archive.rglob("*")):
        if not f.is_file():
            continue
        target = archive_dest_slug("Le", f.name)
        if target == "Le":
            continue
        dest = BY_ACTOR / target / "EVIDENCE" / "archive" / "rerouted_from_le" / f.name
        moved += 1
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                f.unlink()
            else:
                shutil.move(str(f), str(dest))
    return moved


def reroute_loose_evidence(dry_run: bool) -> dict[str, int]:
    """Move misrouted root-level files into EVIDENCE/ or correct actor folder."""
    stats: dict[str, int] = defaultdict(int)
    if not BY_ACTOR.is_dir():
        return {}
    for actor_dir in BY_ACTOR.iterdir():
        if not actor_dir.is_dir():
            continue
        slug = actor_dir.name
        evidence_dir = actor_dir / "EVIDENCE"
        if not dry_run:
            evidence_dir.mkdir(exist_ok=True)
        for f in list(actor_dir.iterdir()):
            if not f.is_file() or f.name in (
                "ACTOR_INDEX.md",
                "MEMORIES.md",
                ".gitkeep",
            ):
                continue
            hint = classify_filename(f.name)
            if hint and hint != slug:
                target = BY_ACTOR / hint / "EVIDENCE" / "rerouted" / f.name
                stats[f"reroute:{hint}"] += 1
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(target))
                continue
            if hint == "_UNROUTED" or (
                slug == "Le"
                and hint is None
                and not re.search(r"clerk|le\b", f.name, re.I)
            ):
                target = BY_ACTOR / "_UNROUTED" / f.name
                stats["_UNROUTED"] += 1
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(target))
                continue
            # Keep litigation-relevant files under EVIDENCE/local/
            target = evidence_dir / "local" / f.name
            if f.parent == actor_dir:
                stats[f"local:{slug}"] += 1
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.move(str(f), str(target))
    return dict(stats)


def count_evidence(actor_dir: Path) -> int:
    ev = actor_dir / "EVIDENCE"
    if not ev.is_dir():
        return 0
    return sum(1 for f in ev.rglob("*") if f.is_file() and f.name != ".gitkeep")


def ensure_portfolio(slug: str, dry_run: bool) -> None:
    if slug.startswith("_"):
        return
    meta = ACTOR_REGISTRY.get(slug)
    if not meta or not PORTFOLIOS.is_dir():
        return
    pdir = PORTFOLIOS / meta["portfolio"]
    if not pdir.exists() and not dry_run:
        pdir.mkdir(parents=True, exist_ok=True)
        idx = BY_ACTOR / slug / "ACTOR_INDEX.md"
        if idx.exists():
            shutil.copy2(idx, pdir / "ACTOR_INDEX.md")


def run(
    dry_run: bool = False, skip_supermemory: bool = False, skip_archives: bool = False
) -> dict:
    load_keys()
    migrate_aliases(dry_run)

    bucket: dict[str, list[dict]] = defaultdict(list)

    for fact in parse_organized_md(ORGANIZED_MD):
        for slug in fact["actors"]:
            bucket[slug].append(fact)

    for fact in fetch_mem0("casey"):
        for slug in fact["actors"]:
            bucket[slug].append(fact)

    for fact in fetch_mem0("operator"):
        for slug in fact["actors"]:
            bucket[slug].append(fact)

    if not skip_supermemory:
        for slug, meta in ACTOR_REGISTRY.items():
            for sm in fetch_supermemory(meta["name"], limit=3):
                for target in sm["actors"]:
                    if target == slug or (
                        not target.startswith("_") and target in sm["actors"]
                    ):
                        bucket[slug].append(sm)
                        break
                else:
                    if slug in sm["actors"]:
                        bucket[slug].append(sm)

    le_cleanup = 0
    if not skip_archives and not dry_run:
        le_cleanup = cleanup_le_archive_pollution(dry_run=False)
    archive_stats = {} if skip_archives else consolidate_archives(dry_run)
    reroute_stats = reroute_loose_evidence(dry_run)
    ref_stats = link_references(dry_run)
    triage_stats = triage_unrouted(dry_run)

    all_slugs = sorted(
        set(ACTOR_REGISTRY) | set(bucket) | {"_CASE", "_INFRA", "_UNROUTED"}
    )
    stats: dict = {
        "actors": {},
        "total_memories": 0,
        "plans_linked": 0,
        "archive_copied": archive_stats,
        "le_archive_rerouted": le_cleanup,
        "evidence_rerouted": reroute_stats,
        "references_linked": ref_stats,
        "unrouted_triaged": triage_stats,
    }

    for slug in all_slugs:
        actor_dir = BY_ACTOR / slug
        if not dry_run:
            actor_dir.mkdir(parents=True, exist_ok=True)
            (actor_dir / "EVIDENCE").mkdir(exist_ok=True)

        memories = bucket.get(slug, [])
        stats["total_memories"] += len(memories)

        plan_count = link_plans(actor_dir, slug, dry_run=dry_run)
        if not dry_run:
            write_memories_md(actor_dir, slug, memories)
            ev_count = count_evidence(actor_dir)
            write_actor_index(actor_dir, slug, memories, plan_count, ev_count)
            ensure_portfolio(slug, dry_run=False)
            stats["plans_linked"] += plan_count

        stats["actors"][slug] = {
            "memories": len(memories),
            "plans": count_plans(actor_dir) if not dry_run else plan_count,
            "evidence_files": count_evidence(actor_dir) if not dry_run else 0,
            "archive_added": archive_stats.get(slug, 0),
            "dir": str(actor_dir),
        }

    if not dry_run:
        write_manifest(stats)
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(
                {**stats, "at": datetime.now(timezone.utc).isoformat()}, indent=2
            )
            + "\n"
        )

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Organize memories into BY_ACTOR folders"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-supermemory",
        action="store_true",
        help="Faster run, Mem0/organized only",
    )
    parser.add_argument(
        "--skip-archives", action="store_true", help="Skip vault archive consolidation"
    )
    args = parser.parse_args()
    stats = run(
        dry_run=args.dry_run,
        skip_supermemory=args.skip_supermemory,
        skip_archives=args.skip_archives,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
