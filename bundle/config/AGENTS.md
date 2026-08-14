# APEX Operator — Agent Rules (Nervous System + Double Helix)

BINDING: `GLACIEREQ-NERVOUS-SYSTEM -> DOUBLE_HELIX:PRO_CODE_KNOWLEDGE`

## Mission entrypoint

For complex GlacierEQ missions, load the `glaciereq-nervous-system` masterskill first when available.

Canonical source: `GlacierEQ/antigravity-awesome-skills/skills/glaciereq-nervous-system/SKILL.md`  
Canonical commit: `6e3bcf71e8d79c682dbe8993a012b761d0a19390`

Lifecycle:

`DISCOVER -> MAP -> REUSE -> EXTEND -> EXECUTE -> VERIFY -> PERSIST`

The masterskill composes existing systems. It does not replace them. Apex Boot Core owns boot/state initialization, the Double Helix owns engineering doctrine/execution, and Tower of Babel owns technology placement and proof.

## Loading order

0. `~/.apex/MASTERSKILL_ACTIVATION.json` — cross-platform composition contract
1. `~/.apex/STARTUP_STATE.json` — saved startup snapshot (connectors, skills, gaps)
2. `Pro_Code/CODER-SKILL.md` — identity, execution laws
3. `Pro_Code/STYLE.md` — naming, commits
4. `pro-code/KNOWLEDGE.md` — execution / Spiral Engine bridge
5. `~/.supermemory/ops/live-context.md` — primed memory context

Session boot: `apex-startup` or `source ~/.apex/session_boot.env`

## Alpha (Pro_Code) — specialize in

- Operator identity, surgical edits, gap analysis before building
- One Big Push commits, verify carryover, no sprawl
- Engineering doctrine, standards, and repository contracts

## Omega (pro-code) — specialize in

- Execution: workers mesh, Nexus API, CI templates, control surfaces
- Governed implementation, verification, repair-forward execution

## Memory and context

```bash
sm-ops prime "current task"
sm-ops save "outcome" --durable
apex-prime "task"
```

Prefer targeted memory retrieval over reloading full histories. Recover current state before rebuilding knowledge.

## MCP connectors

- `unified-memory` — semantic routing across available memory layers
- `supermemory` — long-term knowledge and profiles
- host-native MCP/connectors — execution surfaces selected by the masterskill

## Technology placement

When a mission changes language, runtime, schema, interface, toolchain, hardware dependency, benchmark claim, or formal proof boundary, use `GlacierEQ/the-tower-of-babel` before implementation.

## Quality and stability

- Read before write.
- Reuse existing authority before creating another system.
- Focused diffs only; no novelty refactors.
- Verify after every material operation.
- Never claim completion without verified target state and persistence.
- Preserve exact blockers and continuation points.

## Paths

| Plane | Canonical |
|---|---|
| Masterskill | `GlacierEQ/antigravity-awesome-skills/skills/glaciereq-nervous-system/` |
| Boot | `GlacierEQ/apex-boot-core` |
| Alpha | `~/Pro_Code` |
| Omega | `~/pro-code` |
| Technology | `GlacierEQ/the-tower-of-babel` |
| Memory ops | `~/.agents/skills/supermemory-cli/` (`sm-ops`) |
| Unified MCP | `~/scripts/unified_memory_mcp.py` |
