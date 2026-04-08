# Aptitude Resolver

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-6E56CF?style=for-the-badge&logo=uv&logoColor=white)
![Pydantic](https://img.shields.io/badge/pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=111111)
[![DeepWiki](https://img.shields.io/badge/Ask-DeepWiki-0A66C2?style=for-the-badge&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAsVBMVEVHcEwmWMYZy38Akt0gwZoSaFIbYssUmr4gwJkBlN4WbNE4acofwZkBj9k4aMkBk94WgM0bsIM4aMkewJc2ZMM3Z8cbvIwYpHsewJYAftgBkt0fvpgBkt0cv44cv5wzYckAjtsCk90pasUboXsgwJkfwpYfwJg4aMoct44yXswAkd0BkN84Z8cBktwduZIjcO85lM4hwZo5acoBleA6a88iyaABmOQ8b9QhxZ0CnOoizaOW4DOvAAAAMHRSTlMAKCfW%2FAgWA%2F7%2FDfvMc9j7MU%2Frj3XBcRW%2FJMbe7kUxjI%2FlUzzz6tPQkJ%2BjVmW1oeulmmslAAAByUlEQVQ4y32Tia6jIBSGUVFcqliXtlq73rm3d50ERNC%2B%2F4PNQetoptMeE0PgC%2F9%2FFhCaBSH9Hz2J%2BONgPDl2DolSUWY%2FPL8oEQRCfPxHpFc3Ah5wHoiI6I05NXgjAOgQF3Jn1Dlo4XMPDDes09UE2d%2BREvl3lijBg4CrHNmrbcM2u9u5nwsRcAFfFHFY5sZ607Yua3GqpQiKE6G9cZHZThblZ4T2mLnMxde3ATASMUj72o0Pbs1fADDcLHqAjEDugJ3lC%2BztMGYTADcoLaFyH%2B02DP9%2BWS4ahrXE4laALFKcq8vZfscNY8312mxfr27bLJZjnsYhSDIHmUxLu9h9N%2Fep%2B7pazwoZQw%2B1Nwi33epu7c2p8RooeqCdAHMGoOJIq3CUwIMEniRIaHVe3ZVnO2Vgsh1MstEkQUXVUc%2BjXfk3zbemxS6%2BpQmlPtUeALJ8VKj4JHvAelBqFFdSS3h1SPzQKr%2F%2BaRa0%2B0cCIWtJLauG5U%2FfbgyG01uiNqQhyzA8ddKj1OvK28AsZyN3DKE4X6AEWrU1jJx9N7RFpdPxpHU%2FtMOQG9SjfTp3Yz8KgRVKpfx88Dqhpseq606h%2F%2Bzxfh6LJ8eEDKWbxx9XEDwqzP1SVgAAAABJRU5ErkJggg%3D%3D)](https://deepwiki.com/y0ncha/aptitude-client)
![Last Commit](https://img.shields.io/github/last-commit/aptitude-stack/resolver?style=for-the-badge)

`Aptitude Resolver` is the local decision-making engine in the Aptitude ecosystem. It is a deterministic, package-manager-style resolver for AI skills that turns natural-language requests or existing lockfiles into governed dependency graphs, lockfiles, execution plans, and local materialization while staying intentionally separate from the server that stores immutable registry facts.

## Overview

- Owns intent interpretation, candidate reranking, version selection, dependency solving, governance, lock generation, execution planning, and local materialization.
- Does not own registry storage, immutable metadata, immutable content, indexed candidate retrieval, or published checksum facts. Those remain server concerns.
- Exposes a CLI-first interface with a wizard-first default entrypoint for humans and stable command paths for automation and CI.

The core boundary is simple: the server returns facts, the resolver makes decisions.

## System Design

```mermaid
flowchart LR
    User["User / CI / automation"]

    subgraph Resolver["Aptitude Resolver"]
        direction TB
        Interface["Interface layer<br/>CLI, wizard, shared support"]
        App["Application layer<br/>workflow orchestration + DTOs"]
        Engine["Decision engine<br/>discovery, resolution, governance,<br/>lockfile, execution"]
    end

    Server["Aptitude Server<br/>immutable metadata, content,<br/>candidate retrieval"]
    Workspace["Local workspace<br/>lockfile + materialized skills"]

    User --> Interface
    Interface --> App
    App --> Engine
    Engine <-->|read facts / candidates / content| Server
    Engine --> Workspace
```

The resolver is organized as a layered local system. The interface layer owns the human CLI, wizard routing, rendering, and error presentation. The application layer wires workflows and DTO boundaries. The decision engine owns discovery shaping, deterministic resolution, governance, lock generation, and execution planning. The server is a read boundary, not a decision-maker.

- Interface layer: Typer commands, wizard flows, help/manifest text, prompt handling, and user-facing error formatting.
- Application layer: workflow orchestration and stable request/result DTOs.
- Decision engine: discovery, reranking, resolution, governance, lockfile handling, and execution planning.
- Registry boundary: immutable metadata and content come from the server; final selection and solving remain local.

Canonical architecture and boundary details live in [docs/architecture/system-overview.md](docs/architecture/system-overview.md) and [docs/architecture/server-resolver-boundary.md](docs/architecture/server-resolver-boundary.md).

## CLI Surface

The current promoted CLI surface is:

- `aptitude install "<query>"`
- `aptitude sync --lock aptitude.lock.json`
- `aptitude manifest`

The current advanced preview surface is:

- hidden `aptitude resolve "<query>"`

Running `aptitude` with no arguments launches the install-first wizard. `install` and `sync` are the task commands, `manifest` exposes the full human-readable capability map, and `resolve` remains available for preview, debugging, and CI without materialization.

Representative examples:

```bash
aptitude --help
aptitude install "Postman Primary Skill"
aptitude install "Postman Primary Skill" --json
aptitude sync --lock aptitude.lock.json
aptitude manifest
uv run python -m aptitude_resolver resolve "Postman Primary Skill"
```

The normative CLI contract lives in [docs/architecture/cli-interface.md](docs/architecture/cli-interface.md).

## Quick Start

Requirements:

- Python `3.9+`
- [`uv`](https://docs.astral.sh/uv/)
- access to an Aptitude Server instance

Local development:

```bash
uv sync --extra dev
cp .env.example .env
# set APTITUDE_SERVER_BASE_URL and APTITUDE_READ_TOKEN
uv run python -m aptitude_resolver --help
uv run python -m aptitude_resolver
```

Repo-local command examples:

```bash
uv run python -m aptitude_resolver install "Postman Primary Skill"
uv run python -m aptitude_resolver sync --lock aptitude.lock.json
uv run python -m aptitude_resolver manifest
```

Published usage:

```bash
uv tool install aptitude-resolver
aptitude --help
```

One-off published usage:

```bash
uvx aptitude-resolver@latest --help
```

## Resolver Flows

Fresh planning:

```text
query
-> interface
-> discovery
-> resolver
-> governance
-> lockfile
-> execution planning
-> materialization or result rendering
```

Lock replay:

```text
lockfile
-> interface
-> lock parse + replay
-> execution planning
-> materialization
```

Lock replay is intentionally shorter. Once a valid lock exists, discovery and dependency solving must not run again.

## Current Registry Contract Used By The Resolver

The resolver currently talks to the live registry through these primary runtime paths:

- `POST /discovery`
- `GET /skills/{slug}/versions`
- `GET /skills/{slug}/versions/{version}`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/versions/{version}/content`

For backward compatibility, the client still accepts legacy fallback paths for version metadata and content reads.

Use [docs/reference/api-contract.md](docs/reference/api-contract.md) as the canonical route and payload reference.

## Documentation

- [docs/README.md](docs/README.md): documentation index and reading paths
- [docs/architecture/README.md](docs/architecture/README.md): canonical architecture reading order
- [docs/architecture/cli-interface.md](docs/architecture/cli-interface.md): current CLI command, wizard, and rendering contract
- [docs/architecture/server-resolver-boundary.md](docs/architecture/server-resolver-boundary.md): server facts vs resolver decisions
- [docs/architecture/decision-rules.md](docs/architecture/decision-rules.md): hard implementation and boundary rules
- [docs/reference/api-contract.md](docs/reference/api-contract.md): concrete registry contract used by the resolver
- [docs/contributors/README.md](docs/contributors/README.md): contributor workflow docs
- [docs/reference/README.md](docs/reference/README.md): stable technical reference
- [docs/roadmap/README.md](docs/roadmap/README.md): forward-looking technical direction
- [.agents/README.md](.agents/README.md): agent-facing operating context

## Packaging And Publishing

This project ships as a normal Python package built with `uv` and published to PyPI.

- `pyproject.toml` defines the package metadata, dependencies, and both console scripts: `aptitude-resolver` and `aptitude`
- `make build` creates local wheel and sdist artifacts with `uv build --no-sources`
- `make build-publish` performs a local token-based publish to PyPI or TestPyPI
- pushing a `v*` tag triggers `.github/workflows/publish.yml`, which builds and publishes through GitHub Actions trusted publishing

## Development

Common local commands:

```bash
make run
make debug
make lint
make typecheck
make test
make test-cov
```

If you change CLI behavior, architecture, or the server-resolver boundary, update the corresponding docs in the same change rather than treating the README as the only source of truth.
