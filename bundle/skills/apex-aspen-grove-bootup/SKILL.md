---
name: apex-aspen-grove-bootup
description: Bootstrap projection for GlacierEQ boot and durable-state restoration. Prefer any richer host-installed canonical projection when present.
---

# APEX Aspen Grove Bootup — Bootstrap Projection

Role: boot/state restoration beneath `glaciereq-nervous-system`.

Required behavior:

1. Recover prior durable state before rediscovery.
2. Load current startup/checkpoint artifacts before specialist work.
3. Treat historical LIVE/ACTIVE labels as discovery context until revalidated.
4. Preserve exact continuation state after verified execution.

This bootstrap copy exists so a fresh `apex-cli` installation can satisfy the nervous-system baseline. Host-specific richer projections may supersede it without changing the authority boundary.
