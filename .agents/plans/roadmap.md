# Aptitude Client Roadmap

## Current Baseline

The old exact-coordinate MVP is complete and superseded.

The current implemented baseline includes:

- discovery-backed query resolution
- deterministic recursive dependency solving
- governance before lock generation
- rich lockfile generation, parse, and replay
- lock-driven execution planning
- local materialization from fresh plans and existing lockfiles
- public `install` and `sync` CLI commands

## Current Priorities

1. strengthen the documentation source-of-truth and keep it synced with implementation
2. expand governance beyond lifecycle-only checks
3. introduce `plugins/`, `cache/`, and `telemetry/` only when they become real responsibilities
4. add richer external interfaces such as MCP or SDK surfaces when the product needs them
5. keep `install` and `sync` sharing one lock-driven execution path

## Roadmap Guardrails

- do not regress to graph-driven execution
- do not let the server become the final decision-maker
- do not add top-level packages speculatively
- keep determinism and traceability under test

## Source Of Truth

Use the canonical pair for current architecture and implementation rules:

- `docs/ARCHITECTURE.md`
- `docs/RULES.md`

Supporting docs:

- `README.md`
- `docs/Aptitude-Recommended-Libraries.md`

Historical milestone plans remain useful for implementation history, but they are not the active architecture source of truth.
