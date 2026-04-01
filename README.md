# Aptitude Resolver

Aptitude Resolver is a deterministic, package-manager-style resolver for AI skills.

The system is intentionally split in two:

- Aptitude Server owns registry data, metadata, immutable artifacts, and discovery indexes
- Aptitude Resolver owns intent interpretation, candidate selection, dependency resolution, governance, lock generation, and execution planning

## Current CLI

Primary commands:

- `aptitude install "<query>"`
- `aptitude sync --lock aptitude.lock.json`

Internal preview command:

- `aptitude resolve "<query>"`

`resolve` still exists for preview, debugging, and CI, but it is hidden from normal CLI help. The normal user-facing flow is `install`.

## How To Install

Install the resolver and its development dependencies with `uv`:

```bash
uv sync --extra dev
```

This creates the local environment from `pyproject.toml` and makes the `aptitude` entrypoint available through `uv run` or an activated environment.

## How To Use

Typical usage starts with one of these commands:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main --help
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main install "Postman Primary Skill"
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main sync --lock aptitude_resolver.lock.json
```

Use `install` for fresh planning from a query and `sync --lock` for replaying an existing lockfile. The help text and examples still use the logical `aptitude` command name, but the verified repo-local entrypoint is the module invocation above.

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
- resolver owns policy and candidate selection
- governance is split into:
  - candidate-policy filtering before final ranking and final root selection
  - full graph governance after resolution and before lock generation
- ranking compares only policy-compliant candidates
- phase 1 checksum verification uses server-published `sha256` checksum metadata and fails fast on mismatch

Current code now implements Governance Phase 1, profile-aware ranking, and explainability snapshots. The canonical source of truth for remaining evolution lives under [docs/README.md](docs/README.md).

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
aptitude_resolver install "Postman Primary Skill"
```

Install as JSON for automation:

```bash
aptitude_resolver install "Postman Primary Skill" --json
```

Sync from an existing lockfile:

```bash
aptitude_resolver sync --lock aptitude_resolver.lock.json
```

Preview the resolved graph, lock, and execution plan without materializing:

```bash
uv run python -m aptitude_resolver.interfaces.cli.main resolve "Postman Primary Skill"
```

## Current Package Map

```text
src/aptitude_resolver/
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

## Current Registry Contract Used By The Resolver

The resolver currently talks to the live registry through `registry/` using these runtime paths:

- `POST /discovery`
- `GET /skills/{slug}`
- `GET /skills/{slug}/{version}`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/{version}/content`

The resolver treats the server as a source of immutable facts and candidate generation only. Final ranking, version choice, solving, policy enforcement, lock generation, and execution planning remain resolver-owned.

## Development

Requirements:

- Python `>=3.9`

Run the CLI:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main --help
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main install "Postman Primary Skill"
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main sync --lock aptitude_resolver.lock.json
```

Or via Python:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver.interfaces.cli.main --help
```

Developer workflow:

```bash
make help
make format
make format-check
make lint
make typecheck
make test
make check
```

## Source Of Truth Docs

Start with the docs index:

- [docs/README.md](docs/README.md)

The canonical architecture pair for future implementation work is:

- [docs/architecture/system-overview.md](docs/architecture/system-overview.md)
- [docs/architecture/decision-rules.md](docs/architecture/decision-rules.md)

Before any non-trivial implementation or refactor, read both.

Supporting docs:

- [docs/contributors/README.md](docs/contributors/README.md)
- [docs/reference/recommended-libraries.md](docs/reference/recommended-libraries.md)
- [docs/roadmap/README.md](docs/roadmap/README.md)

The `docs/reference/openapi/` directory is kept as raw server reference material, not as the sole source of truth for runtime behavior.
