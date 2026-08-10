
## Verified public surface

The exact-head Public Truth Gate verifies:

- `./apex help` from the repository checkout;
- fail-closed handling when an external `job-app` dependency is absent;
- environment-controlled path resolution in `core/paths.py`;
- Python compilation for repository-local `core/` and `tests/` surfaces;
- shell syntax for the main `apex` dispatcher;
- that the historical Casebuilder/Red-Helix integration harness requires explicit external roots rather than hard-coded device paths.

The public proof is intentionally narrower than the full historical command inventory.

## Main dispatcher

```bash
./apex help
```

Repository-local commands resolve a sibling executable first and then `~/bin`:

```bash
./apex daemon
./apex openclaw --help
```

Commands that depend on a separate job-application checkout require an explicit or default location and fail with exit `78` when their files are unavailable:

```bash
APEX_JOB_APP_DIR=/path/to/job-app ./apex highway
APEX_JOB_APP_DIR=/path/to/job-app ./apex hero
APEX_JOB_APP_DIR=/path/to/job-app ./apex status
```

See `RECOVERY_GUIDE.md` for details.
=======
[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![Shell](https://img.shields.io/badge/Shell-POSIX-green)]()
[![Domain](https://img.shields.io/badge/Domain-CLI%20Tooling-darkgreen)]()
>>>>>>> 4029ea9 (chore: Hyper Excellence Activation & structural matrix alignment)

## Configurable local paths

## 🎯 For Recruiters & Hiring Managers

This repository implements the **APEX Command Line Interface** — providing engineers and operators with unified terminal control over multi-agent workflows. It demonstrates:

- **Argparse & Rich terminal formatting** with colorized status tables and progress meters
- **Subcommand dispatch architecture** for seamless plugin extensibility
- **Async command execution** with non-blocking stdout/stderr streaming
- **Configuration management** with automatic environment resolution

**Why this matters**: High-quality CLI developer tools turn complex backend infrastructure into intuitive, high-velocity workflows for engineering teams.

---

## 🔬 For Engineers & Technical Reviewers

### Core Components

| Component | Language | Purpose |
|---|---|---|
| `apex` | Python | Primary CLI entry point and command dispatcher |
| `src/` | Python | Subcommand modules (status, run, sync, audit) |
| `tests/` | Python | Automated CLI test suite |

---

## 🤖 ML/AI & Programmatic Mesh Integration

- **MCP Tool**: `apex_cli_exec()` — programmatic CLI execution for autonomous AI agents
- **Mastermind Sidecar**: Telemetry bridge linking CLI commands to APEX Highway mesh
- **SHA-256 Integrity**: Hashes tracked in `.integrity/file_hashes.json`

---

## ⚡ Quick Start

```bash
python3 apex status
python3 tests/test_cli.py
```
