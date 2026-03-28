# Aptitude Client

Aptitude Client is a deterministic, package-manager-style client for AI skills.

The system is intentionally split in two:

- Aptitude Server owns registry data, metadata, immutable artifacts, and discovery indexes
- Aptitude Client owns intent interpretation, candidate selection, dependency resolution, governance, lock generation, and execution planning

## Current CLI

Primary commands:

- `aptitude install "<query>"`
- `aptitude sync --lock aptitude.lock.json`

Internal preview command:

- `aptitude resolve "<query>"`

`resolve` still exists for preview, debugging, and CI, but it is hidden from normal CLI help. The normal user-facing flow is `install`.

## What Works Today

- discovery-backed query resolution from human-readable input
- resolver-owned candidate version selection
- deterministic recursive dependency graph resolution
- candidate-policy filtering and graph governance before lock generation
- workspace policy loading from `aptitude.toml`
- hard policy CLI overrides for fresh planning
- rich lockfile generation, serialization, parsing, and replay
- lock-driven execution plan generation
- local materialization from either a fresh plan or an existing lockfile
- `sync --lock` as the lock-replay equivalent of `uv sync`
- registry caching and bounded transient retry
- additive telemetry for planning and materialization stages
- deterministic lockfiles for identical logical inputs
- trace output for discovery, selection, resolver, lock, and execution steps

## What Is Still Incomplete

- organization-managed policy loading is not implemented yet
- broader organization-specific rules are not implemented yet
- winner-vs-runner-up explanation still derives from parallel explanation logic instead of directly from reranker output
- `plugins/` extensibility is not implemented yet
- MCP and SDK interfaces are not implemented yet

## Selection, Governance, And Integrity Direction

The canonical architecture now defines these required semantics:

- server provides immutable metadata such as lifecycle, trust, token, size, and checksum facts
- client owns policy and candidate selection
- governance is split into:
  - candidate-policy filtering before final ranking and final root selection
  - full graph governance after resolution and before lock generation
- ranking compares only policy-compliant candidates
- phase 1 checksum verification uses server-published `sha256` checksum metadata and fails fast on mismatch

Current code now implements Governance Phase 1, profile-aware ranking, and explainability snapshots. The canonical source of truth for remaining evolution is [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current User Flows

Fresh planning and install:

```text
install query
-> discovery
-> resolver
-> governance
-> lockfile
-> execution plan
-> materialization
```

Lock replay:

```text
sync --lock aptitude.lock.json
-> lockfile parse
-> lock replay
-> execution plan
-> materialization
```

## Example Commands

Install from a query:

```bash
aptitude install "Postman Primary Skill"
```

Install as JSON for automation:

```bash
aptitude install "Postman Primary Skill" --json
```

Sync from an existing lockfile:

```bash
aptitude sync --lock aptitude.lock.json
```

Preview the resolved graph, lock, and execution plan without materializing:

```bash
py -3 -m aptitude_client.interfaces.cli.main resolve "Postman Primary Skill"
```

## Current Package Map

```text
src/aptitude_client/
  application/
    dto/
    queries/
    use_cases/
  cache/
  discovery/
    intent/
    query_builder/
    reranking/
  domain/
    errors/
    models/
    policy/
    tracing/
  execution/
  governance/
  interfaces/
    cli/
  lockfile/
  registry/
  resolver/
    conflict/
    graph/
    normalizer/
    replay/
    solver/
    validation/
  shared/
    config/
    logging/
  telemetry/
```

## Current Registry Contract Used By The Client

The client currently talks to the live registry through `registry/` using these runtime paths:

- `POST /discovery`
- `GET /skills/{slug}`
- `GET /skills/{slug}/{version}`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/{version}/content`

The client treats the server as a source of immutable facts and candidate generation only. Final ranking, version choice, solving, policy enforcement, lock generation, and execution planning remain client-owned.

## Development

Requirements:

- Python `>=3.9`

Install:

```bash
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
py -3 -m pip install -e ".[dev]"
```

Run the CLI:

```bash
aptitude --help
aptitude install "Postman Primary Skill"
aptitude sync --lock aptitude.lock.json
```

Or via Python:

```bash
py -3 -m aptitude_client.interfaces.cli.main --help
```

Run tests:

```bash
py -3 -m pytest -v
```

## Source Of Truth Docs

The canonical pair for future implementation work is:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/RULES.md](docs/RULES.md)

Before any non-trivial implementation or refactor, read both.

Supporting docs:

- [docs/Aptitude-Recommended-Libraries.md](docs/Aptitude-Recommended-Libraries.md)

The `docs/openapi/` directory is kept as raw server reference material, not as the sole source of truth for runtime behavior.
