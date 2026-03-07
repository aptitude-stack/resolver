# Aptitude Client (`aptitude-client`)

`aptitude-client` is the runtime-facing client/orchestration layer for the Aptitude skill ecosystem.

It sits in front of `aptitude-repository` and is responsible for turning runtime requests (prompt/tool calls) into executable plans, while preserving deterministic repository contracts.

This project follows:
- Product/system overview: [`docs/overview.md`](docs/overview.md)
- Resolver responsibilities: [`docs/resolver-prd.md`](docs/resolver-prd.md)
- Repository/resolver boundary: [`docs/scope.md`](docs/scope.md)

## Current Status

This repository currently contains a minimal FastAPI service scaffold (`main.py`) and is the starting point for the resolver/client implementation described in the PRD.

## Responsibilities (Resolver Side)

Per [`docs/resolver-prd.md`](docs/resolver-prd.md), this service is responsible for:
- Exposing runtime-facing interfaces (MCP + CLI, and optionally HTTP adapters).
- Normalizing incoming tool-call/prompt requests.
- Calling `aptitude-repository` APIs (resolve/fetch/report) via API contracts only.
- Running pluggable hooks:
  - Security scanners
  - Policy extensions
  - Overlap scoring against active runtime skills
- Building and returning an execution plan with trace metadata.
- Maintaining resolver-local cache and observability/diagnostics.

## Out of Scope (Owned by Repository)

Per [`docs/scope.md`](docs/scope.md), this service must not:
- Publish or mutate skill artifacts.
- Own canonical dependency graph or metadata authority.
- Write directly to repository persistence layers.
- Replace repository governance/versioning rules.

All authoritative artifact/graph/versioning operations stay in `aptitude-repository`.

## Target Request Flow

1. Client sends tool call/prompt to resolver (MCP/CLI).
2. Resolver normalizes request.
3. Resolver calls repository deterministic resolve API.
4. Repository returns `ResolvedBundle` + `ResolutionReport`.
5. Resolver executes plugin chain (security/policy/overlap).
6. Resolver returns execution plan + plugin decisions + trace ID.

## Planned Public Interfaces (from PRD)

- MCP tool: `resolve_and_plan`
- CLI command: `aptitude resolve "<prompt>"`
- Structured output includes:
  - `bundle_hash`
  - selected skills
  - plugin decisions
  - execution plan
  - trace ID

## Repository Dependency Contract

Resolver consumes repository via versioned APIs only. Expected repository APIs include:
- `POST /skills/publish` (repository-owned; resolver does not call for writes in normal runtime flow)
- `GET /skills/{id}/{version}`
- `POST /resolve`
- `GET /bundles/{bundle_id}`
- `GET /reports/{resolution_id}`

## Local Development

### Prerequisites

- Python `>=3.9`
- `uv` (recommended) or `pip`

### Install

Using `uv`:

```bash
uv sync
```

Using `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
uvicorn main:app --reload
```

Server default URL: `http://127.0.0.1:8000`

### Smoke Test

Use [`test_main.http`](test_main.http) or:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/hello/User
```

## MVP Roadmap (from PRD)

1. Implement request normalization + repository resolve integration.
2. Add plugin runtime (pre/post resolve + pre-execution hooks).
3. Build execution-plan assembler and trace output.
4. Add cache controls and observability.
5. Enforce architecture guardrails (no repository persistence coupling).

## Related Documents

- [Overview](docs/overview.md)
- [Resolver PRD](docs/resolver-prd.md)
- [Repository PRD](docs/repository-prd.md)
- [Scope and Boundary](docs/scope.md)
- [Changelog: Foundation Skeleton](docs/changelog/01-foundation-service-skeleton-changelog.md)
- [Changelog: Immutable Registry](docs/changelog/02-immutable-skill-registry-changelog.md)
