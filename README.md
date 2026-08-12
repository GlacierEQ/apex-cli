# APEX CLI

APEX CLI is a bounded **Bash command dispatcher** for repository-local APEX tools plus a small set of explicitly external job-application commands.

The repository is intentionally fail-closed at dependency boundaries: it does not silently pretend sibling projects, external checkouts, or device-specific paths exist.

## Verified public surface

The exact-head Public Truth Gate verifies:

- `./apex help` from the repository checkout;
- shell syntax for the main `apex` dispatcher;
- repository-local command resolution for `apex-openclaw` and `apex-daemon`;
- fail-closed exit `78` when an external `job-app` dependency is absent;
- environment-controlled path resolution in `core/paths.py`;
- Python compilation for repository-local `core/` and `tests/` surfaces;
- bounded repository-local public tests;
- that the optional Casebuilder/Red-Helix integration harness requires explicit external roots instead of hard-coded device paths.

This proof **does not prove** that Casebuilder4000, Red Helix, the job-application checkout, Dropbox, Android/Termux, or any other external system is installed, authenticated, reachable, or operational.

## Main dispatcher

```bash
./apex help
```

Repository-local commands resolve an executable in this checkout first and then `~/bin`:

```bash
./apex daemon
./apex openclaw --help
```

If neither location contains the requested local executable, the dispatcher exits `78` with a dependency-unavailable message.

## External job-app commands

The following commands intentionally depend on a separate verified job-application checkout:

```bash
APEX_JOB_APP_DIR=/path/to/job-app ./apex highway
APEX_JOB_APP_DIR=/path/to/job-app ./apex hero
APEX_JOB_APP_DIR=/path/to/job-app ./apex status
```

When `APEX_JOB_APP_DIR` is unset, the dispatcher may use `$HOME/job-app`; if the required file is absent it refuses execution with exit `78` rather than manufacturing a success path.

## Optional Casebuilder / Red Helix integration

`tests/test_end_to_end_casebuild.py` is an **external integration harness**, not part of the repository-local self-contained proof. It requires:

```bash
export APEX_CASEBUILDER_ROOT=/verified/path/to/Casebuilder4000
export APEX_RED_HELIX_ROOT=/verified/path/to/REPO_1001_RED_HELIX
python tests/test_end_to_end_casebuild.py
```

`bundle/scripts/end_to_end_casebuild.py` provides the equivalent explicit CLI form:

```bash
python bundle/scripts/end_to_end_casebuild.py \
  --casebuilder-root /verified/path/to/Casebuilder4000 \
  --red-helix-root /verified/path/to/REPO_1001_RED_HELIX
```

Both paths import the external modules only after the caller supplies real roots.

## Repository-local verification

```bash
bash -n apex
./apex help
python -m compileall -q core tests bundle/scripts/verify_mem0_layers.py
python -m pytest -q tests/test_public_surface.py
```

Hosted workflows additionally check multiple supported Python versions and the public boundary.

## Architecture at a glance

| Surface | Language | Role |
|---|---|---|
| `apex` | Bash | top-level bounded command dispatcher |
| `core/` | Python | repository-local path/configuration helpers |
| `tests/` | Python | bounded public behavior tests plus explicit external harness |
| `apex-*` scripts | Bash/Python | specialized local operational commands |
| `bundle/` | mixed | portable/bundled integration and recovery utilities |

See `RECOVERY_GUIDE.md` and `SECURITY_AND_FLEET_OPS.md` for additional operational context.
