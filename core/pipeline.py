"""
Pipeline Runner — Enforced sequential execution with gates
GlacierEQ APEX | computer-user core

Every phase must pass before the next begins.
No skipping. No ignoring. No "we'll do it later."

Phases:
  1. BOOT     — deps, dirs, connectivity
  2. CREDENTIALS — validate all needed creds exist
  3. SKILL_LOAD — import and validate skill modules
  4. EXECUTE  — run the actual work
  5. PERSIST  — save results, update indices
  6. AUDIT    — log everything that happened

Usage:
  from pipeline import Pipeline
  p = Pipeline("linkedin-verify")
  p.phase("boot", boot_fn)
  p.phase("validate", validate_fn)
  p.phase("execute", execute_fn)
  p.run()
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from paths import SESSION_DIR


class PipelineError(Exception):
    """Raised when a pipeline phase fails — halts execution."""

    pass


class Phase:
    """A single pipeline phase with retry logic."""

    def __init__(
        self,
        name: str,
        fn: Callable,
        retries: int = 2,
        timeout: int = 300,
        required: bool = True,
    ):
        self.name = name
        self.fn = fn
        self.retries = retries
        self.timeout = timeout
        self.required = required
        self.status = "pending"
        self.result = None
        self.error = None
        self.attempts = 0
        self.duration_ms = 0

    def execute(self, context: dict) -> Any:
        """Run phase with retries. Raises on failure if required."""
        self.attempts = 0
        start = time.time()

        for attempt in range(self.retries + 1):
            self.attempts = attempt + 1
            try:
                self.result = self.fn(context)
                self.status = "passed"
                self.duration_ms = (time.time() - start) * 1000
                return self.result
            except Exception as e:
                self.error = str(e)
                if attempt < self.retries:
                    wait = 2**attempt
                    print(
                        f"  [{self.name}] attempt {attempt + 1} failed: {e} — retrying in {wait}s"
                    )
                    time.sleep(wait)
                else:
                    self.status = "failed" if self.required else "skipped"
                    self.duration_ms = (time.time() - start) * 1000
                    if self.required:
                        raise PipelineError(
                            f"Phase '{self.name}' failed after {self.attempts} attempts: {e}"
                        )
                    return None


class Pipeline:
    """Enforced sequential pipeline — no skipping, no ignoring."""

    def __init__(self, name: str, log_dir: Optional[Path] = None):
        self.name = name
        self.phases: List[Phase] = []
        self.context: Dict[str, Any] = {}
        self.started_at = None
        self.completed_at = None
        self.status = "pending"
        self.log_dir = log_dir or (SESSION_DIR / "pipeline-runs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def phase(
        self,
        name: str,
        fn: Callable,
        retries: int = 2,
        timeout: int = 300,
        required: bool = True,
    ) -> "Pipeline":
        """Add a phase. Required phases halt pipeline on failure."""
        self.phases.append(Phase(name, fn, retries, timeout, required))
        return self

    def set(self, key: str, value: Any) -> None:
        """Set a context value shared across phases."""
        self.context[key] = value

    def get(self, key: str, default=None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)

    def run(self) -> dict:
        """Execute all phases in order. Returns summary report."""
        self.started_at = datetime.now(timezone.utc)
        self.status = "running"
        results = []

        print(f"\n{'=' * 60}")
        print(f"PIPELINE: {self.name}")
        print(f"Started: {self.started_at.isoformat()}")
        print(f"Phases: {len(self.phases)}")
        print(f"{'=' * 60}\n")

        for i, phase in enumerate(self.phases, 1):
            print(f"[{i}/{len(self.phases)}] {phase.name}...", end=" ", flush=True)
            try:
                phase.execute(self.context)
                print(f"✅ ({phase.duration_ms:.0f}ms)")
                results.append(
                    {
                        "phase": phase.name,
                        "status": "passed",
                        "attempts": phase.attempts,
                        "duration_ms": round(phase.duration_ms),
                    }
                )
            except PipelineError as e:
                print(f"❌ FAILED: {e}")
                results.append(
                    {
                        "phase": phase.name,
                        "status": "failed",
                        "error": str(e),
                        "attempts": phase.attempts,
                        "duration_ms": round(phase.duration_ms),
                    }
                )
                self.status = "failed"
                break
            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append(
                    {
                        "phase": phase.name,
                        "status": "error",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                )
                self.status = "failed"
                break
        else:
            self.status = "passed"

        self.completed_at = datetime.now(timezone.utc)
        total_ms = (self.completed_at - self.started_at).total_seconds() * 1000

        report = {
            "pipeline": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "total_ms": round(total_ms),
            "phases": results,
            "context_keys": list(self.context.keys()),
        }

        # Save log
        ts = self.started_at.strftime("%Y%m%dT%H%M%SZ")
        log_path = self.log_dir / f"{self.name}_{ts}.json"
        log_path.write_text(json.dumps(report, indent=2))

        print(f"\n{'=' * 60}")
        print(f"RESULT: {self.status.upper()}")
        print(f"Duration: {total_ms:.0f}ms")
        print(f"Log: {log_path}")
        print(f"{'=' * 60}\n")

        return report


# ─── Common Phase Functions ──────────────────────────────────────────────────


def boot_phase(context: dict) -> dict:
    """Phase 1: Verify deps, dirs, connectivity."""
    import subprocess

    # Check Node.js
    result = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Node.js not found — required for Puppeteer backend")
    context["node_version"] = result.stdout.strip()

    # Check puppeteer-core
    result = subprocess.run(
        ["node", "-e", "require('puppeteer-core')"],
        capture_output=True,
        env={
            **__import__("os").environ,
            "NODE_PATH": "/data/data/com.termux/files/usr/lib/node_modules",
        },
    )
    if result.returncode != 0:
        raise RuntimeError(
            "puppeteer-core not installed — run: npm install -g puppeteer-core"
        )
    context["puppeteer"] = True

    # Check Chromium
    import shutil

    chrome = (
        shutil.which("chromium-browser")
        or shutil.which("chromium")
        or shutil.which("google-chrome")
    )
    if not chrome:
        raise RuntimeError("Chromium not found")
    context["chrome_path"] = chrome

    # Verify dirs
    from paths import ALL_DIRS

    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    context["dirs_created"] = len(ALL_DIRS)

    return {"node": context["node_version"], "chrome": chrome, "dirs": len(ALL_DIRS)}


def credentials_phase(context: dict) -> dict:
    """Phase 2: Validate credentials exist for requested services."""
    from paths import load_credentials

    services_needed = context.get("services_needed", [])
    missing = []

    for service in services_needed:
        creds = load_credentials(service)
        if not creds or all(not v for v in creds.values()):
            missing.append(service)
        else:
            context[f"creds_{service}"] = creds

    if missing:
        raise RuntimeError(
            f"Missing credentials for: {', '.join(missing)}. "
            f"Add to ~/.apex/connections.json or set env vars."
        )

    return {"validated": services_needed, "missing": missing}


def browser_test_phase(context: dict) -> dict:
    """Phase 3: Verify browser backend works."""
    from browser_adapter import get_backend

    backend_name = context.get("backend", None)
    b = get_backend(backend_name)
    b.navigate("https://httpbin.org/get")
    url = b.get_url()
    text = b.get_text()
    b.close()

    if "origin" not in text.lower() and "headers" not in text.lower():
        raise RuntimeError("Browser test failed — unexpected page content")

    return {"url": url, "backend": type(b).__name__}


def skill_load_phase(context: dict) -> dict:
    """Phase 4: Import and validate skill modules."""
    import importlib

    skills_dir = Path(__file__).parent / "skills"
    skills_needed = context.get("skills_needed", [])
    loaded = {}

    for skill_name in skills_needed:
        skill_path = skills_dir / skill_name
        if not skill_path.exists():
            raise RuntimeError(f"Skill not found: {skill_name}")

        # Find the main Python file
        py_files = list(skill_path.glob("*.py"))
        if not py_files:
            # Check for SKILL.md only (not implemented)
            if (skill_path / "SKILL.md").exists():
                loaded[skill_name] = "spec_only"
                continue
            raise RuntimeError(f"Skill '{skill_name}' has no Python files")

        # Try importing
        sys.path.insert(0, str(skill_path.parent))
        try:
            mod = importlib.import_module(skill_name.replace("-", "_"))
            loaded[skill_name] = "loaded"
        except Exception as e:
            loaded[skill_name] = f"import_error: {e}"
            raise RuntimeError(f"Failed to import skill '{skill_name}': {e}")

    context["skills_loaded"] = loaded
    return loaded


# ─── Quick Pipeline Builders ─────────────────────────────────────────────────


def make_boot_pipeline(extra_phases: Optional[List[tuple]] = None) -> Pipeline:
    """Standard boot pipeline: boot → credentials → browser test."""
    p = Pipeline("boot")
    p.phase("boot", boot_phase)
    p.phase("credentials", credentials_phase)
    p.phase("browser_test", browser_test_phase)
    if extra_phases:
        for name, fn, *args in extra_phases:
            p.phase(name, fn, *args)
    return p


def make_skill_pipeline(
    skill_name: str, services: Optional[List[str]] = None
) -> Pipeline:
    """Skill execution pipeline: boot → creds → load skill → execute."""
    p = Pipeline(f"skill:{skill_name}")
    p.set("skills_needed", [skill_name])
    p.set("services_needed", services or [])
    p.phase("boot", boot_phase)
    p.phase("credentials", credentials_phase)
    p.phase("skill_load", skill_load_phase)
    return p


if __name__ == "__main__":
    # Demo: run boot pipeline
    p = make_boot_pipeline()
    report = p.run()
    print(json.dumps(report, indent=2))
