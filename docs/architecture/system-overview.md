# Aptitude System Overview

## Identity

Aptitude is the local decision-making engine for AI skill planning and materialization.

The system is intentionally split:

- Aptitude Server owns registry data, immutable metadata, immutable artifacts, and indexed candidate retrieval.
- Aptitude owns intent interpretation, candidate selection, dependency solving, governance, locking, and execution planning.

The server returns facts.
The resolver makes decisions.

## Canonical Flows

### Fresh Planning

Use this when the input is a user query.

```text
query
-> interface
-> application
-> discovery
-> resolver
-> governance
-> lockfile
-> execution planning
-> materialization or result rendering
```

This is the flow behind:

- `aptitude install`
- hidden `aptitude resolve`

Fresh install materialization is internal Aptitude state. The user-facing install result is an agent-ready skill export. By default, Aptitude stores downloaded artifacts under the platform cache directory and lock/plan/trace/provenance state under the platform state directory. On Windows these are `%LOCALAPPDATA%\aptitude\cache` and `%LOCALAPPDATA%\aptitude\state`. Project-scope installs write a replayable, cumulative `aptitude.lock.json` to the project root; global-scope installs write the same cumulative lock to the Aptitude state directory. Each new install retains existing pins and adds its resolved root graph.

Interactive `install SLUG` prompts for omitted scope and agent targets using the
wizard UI, then reviews the resolved plan and confirms before materialization.
The install use case exposes an optional DTO-only review callback after planning,
governance, and destination validation; execution continues with that same plan.
The CLI owns the prompts and cancellation. `--yes` skips prompts; JSON, non-TTY,
and CI invocations retain unattended behavior and Codex/project defaults.

### Lock Replay

Use this when the input is an existing lockfile.

```text
lockfile
-> interface
-> application
-> lock parse + replay
-> execution planning
-> materialization
```

This is the flow behind:

- `aptitude sync --lock`

Lock replay is intentionally shorter. Once a valid lock exists, discovery and dependency solving must not run again.

### Config Inspection

Use this when the input is a request to inspect the effective local client policy.

```text
policy/config request
-> interface
-> application
-> config discovery + merge
-> result rendering
```

This is the flow behind:

- `aptitude policy show`

## Package Boundaries

The current package tree is rooted at `src/aptitude_resolver/`.

- `application/`: orchestration and DTO boundaries
- `cache/`: advisory caching helpers
- `discovery/`: intent parsing, query building, non-final candidate shaping and reranking
- `domain/`: models, policy types, tracing models, resolver-owned errors
- `execution/`: lock-driven execution planning, artifact verification, safe archive extraction, materialization, and agent export
- `governance/`: legality checks before lock generation
- `interfaces/`: CLI, MCP, wizard-oriented interface helpers, and shared interface support
- `lockfile/`: lock schema, serializer, parser, and replay helpers
- `registry/`: Aptitude Server transport boundary and transport-to-domain mapping
- `resolution/`: deterministic version choice, root selection, dependency expansion, and validation
- `shared/`: config, logging, and small shared utilities
- `telemetry/`: additive metrics and instrumentation

## Core Invariants

- Resolver logic must be deterministic for the same logical inputs.
- Discovery may shape and rerank candidates, but it must not make final root decisions.
- Execution must consume lock data only.
- Execution may materialize locked artifacts concurrently. Download concurrency
  and local archive extraction concurrency are separate controls, but observable
  results such as installed skill order, trace order, lockfiles, and execution
  plans must remain deterministic from the lock install order.
- Materialization fetches locked skill artifacts as compressed `tar.zst` bytes,
  verifies the compressed-byte checksum, extracts only safe archive members into
  staging, and promotes the target workspace only after every locked skill is
  materialized successfully.
- Agent export copies verified materialized skill content into selected
  agent skill roots as unversioned `SKILL.md` packages with an Aptitude sidecar.
- The server is a fact source, not the final decision-maker.
- Explainability, telemetry, cache, and retry remain additive; they must not change correctness.

## Current Technical Direction

The active hardening areas are:

- test hardening
- layered client policy for fresh planning
- cache and retry
- observability
- advanced governance
- archive artifact materialization using verified `tar.zst` skill artifacts

The currently deferred areas are:

- remote or centrally managed policy services
- broader governance and explanation refinement
- plugins
- SDK surface
