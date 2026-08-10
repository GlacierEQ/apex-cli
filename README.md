# APEX CLI

**Repository-local command collection and bounded execution helpers for the APEX/AKOS portfolio.**

This repository contains shell and Python utilities for local dispatch, path/credential configuration, pipeline sequencing, monitoring, recovery, and optional adapters. The presence of a command or connector file **does not prove** that an external service, sibling repository, account, browser, provider, credential, case system, or deployment target is currently connected or operational.

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

A repository link or local executable lookup is not evidence of live cross-repository integration.

## Configurable local paths

`core/paths.py` resolves local directories from `APEX_*` environment variables before local configuration/defaults. For example:

```bash
export APEX_BASE_DIR="$HOME/automation"
export APEX_TASKLET_DIR="$APEX_BASE_DIR/tasklet"
export APEX_WORKSPACE_DIR="$APEX_BASE_DIR/workspace"
export APEX_TMP_DIR="$APEX_BASE_DIR/tmp"
```

Credential loading supports environment variables or a configured local connections file. No credential value is part of the public capability claim.

## External integration harness

`tests/test_end_to_end_casebuild.py` is an **opt-in external harness**, not repository-local proof. It requires both:

```bash
export APEX_CASEBUILDER_ROOT=/path/to/casebuilder
export APEX_RED_HELIX_ROOT=/path/to/red-helix
python tests/test_end_to_end_casebuild.py
```

The harness imports sibling code only after those roots are explicitly configured and verified as directories. Public CI does not infer that those private/external systems exist.

## CI and proof boundaries

`.github/workflows/public-truth.yml` binds proof to the exact pull-request head or push SHA on Python 3.11 and 3.13.

`.github/workflows/ci.yml` pins its reusable CI dependency to an exact commit of `GlacierEQ/public-actions-runner-host`. Its external benchmark is isolated to scheduled/manual runs so pull-request proof does not depend on external service credentials.

A green public truth gate establishes only the repository-local behavior listed above. It does not establish:

- a live 61-node mesh or agent fleet;
- production browser automation;
- live memory/MCP/Dropbox/Neo4j/provider connectivity;
- deployment authority or successful external deployment;
- access to private legal/case data;
- automatic credential availability;
- runtime operation of AKOS or sibling repositories merely because they are referenced.

## Historical command inventory

The repository preserves many `apex-*` tools and recovery/operations documents. They remain available for inspection and separate verification, but command names such as `deploy`, `legal`, `memory`, `stealth`, `forensics`, or `daemon` are not promoted as current external capabilities without their own evidence.

## Portfolio relationship

- Architecture reference: `GlacierEQ/AKOS`
- Portfolio classification: `HELIX_STRAND.md`
- Fleet/integrity notes: `SECURITY_AND_FLEET_OPS.md`

Those relationships are topology/context, not inherited runtime proof.
