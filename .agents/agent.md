# Aptitude Resolver Agent Contract

Agents should use canonical docs first and treat this directory as an operating layer.

## Required Reading Order

1. `../README.md`
2. `../docs/README.md`
3. `../docs/architecture/system-overview.md`
4. `../docs/architecture/decision-rules.md`
5. `rules/repo.md`
6. `memory/meta.md`

Historical plan files under `.agents/plans/` are implementation history, not the architecture source of truth.

Before any non-trivial change, agents must read the architecture docs first.

## Current Repository Reality

Aptitude Resolver is a Python resolver for:

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
- `cache/`
- `telemetry/`

Planned but not yet implemented as packages:

- `plugins/`
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
- update `rules/repo.md` when agent workflow rules change
- update canonical docs in `../docs/` when architecture, interfaces, or package boundaries change
- keep historical plans for history, but do not treat them as the current source of truth
