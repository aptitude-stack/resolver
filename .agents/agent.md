# Aptitude Client Agent Contract

## Source And Instruction Files

Use these as the primary repository guidance set:

1. `../README.md`
2. `../docs/ARCHITECTURE.md`
3. `../docs/RULES.md`
4. `rules/repo.md`
5. `memory/meta.md`

Historical plan files under `.agents/plans/` are implementation history, not the architecture source of truth.

Before any non-trivial change, agents must read `docs/ARCHITECTURE.md` and `docs/RULES.md` first.

## Current Repository Reality

Aptitude Client is a Python client for:

- discovery-backed skill lookup
- deterministic dependency resolution
- governance before lock generation
- lock generation, parse, and replay
- lock-driven execution planning and materialization

Current public CLI commands:

- `install`
- `sync`

Current hidden internal CLI command:

- `resolve`

Current main packages:

- `application/`
- `discovery/`
- `domain/`
- `execution/`
- `governance/`
- `interfaces/`
- `lockfile/`
- `registry/`
- `resolver/`
- `shared/`

Planned but not yet implemented as packages:

- `plugins/`
- `cache/`
- `telemetry/`
- `interfaces/mcp`
- `interfaces/sdk`

## Core Invariants

- keep behavior deterministic for the same logical inputs
- keep interfaces thin
- keep application orchestration-focused
- keep discovery separate from final selection and solving
- keep execution lock-driven
- treat the server as a source of facts, not the final decision-maker

## Documentation Discipline

- update `memory/meta.md` when stable repository facts change
- update `rules/repo.md` when workflow rules change
- update `docs/ARCHITECTURE.md` when architecture or boundaries change
- update `docs/RULES.md` when implementation rules change
- keep historical plans for history, but do not treat them as the current source of truth
