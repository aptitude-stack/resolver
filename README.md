# Aptitude Resolver

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-6E56CF?style=for-the-badge&logo=uv&logoColor=white)
![Pydantic](https://img.shields.io/badge/pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=111111)
[![DeepWiki](https://img.shields.io/badge/Ask-DeepWiki-0A66C2?style=for-the-badge&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAsVBMVEVHcEwmWMYZy38Akt0gwZoSaFIbYssUmr4gwJkBlN4WbNE4acofwZkBj9k4aMkBk94WgM0bsIM4aMkewJc2ZMM3Z8cbvIwYpHsewJYAftgBkt0fvpgBkt0cv44cv5wzYckAjtsCk90pasUboXsgwJkfwpYfwJg4aMoct44yXswAkd0BkN84Z8cBktwduZIjcO85lM4hwZo5acoBleA6a88iyaABmOQ8b9QhxZ0CnOoizaOW4DOvAAAAMHRSTlMAKCfW%2FAgWA%2F7%2FDfvMc9j7MU%2Frj3XBcRW%2FJMbe7kUxjI%2FlUzzz6tPQkJ%2BjVmW1oeulmmslAAAByUlEQVQ4y32Tia6jIBSGUVFcqliXtlq73rm3d50ERNC%2B%2F4PNQetoptMeE0PgC%2F9%2FFhCaBSH9Hz2J%2BONgPDl2DolSUWY%2FPL8oEQRCfPxHpFc3Ah5wHoiI6I05NXgjAOgQF3Jn1Dlo4XMPDDes09UE2d%2BREvl3lijBg4CrHNmrbcM2u9u5nwsRcAFfFHFY5sZ607Yua3GqpQiKE6G9cZHZThblZ4T2mLnMxde3ATASMUj72o0Pbs1fADDcLHqAjEDugJ3lC%2BztMGYTADcoLaFyH%2B02DP9%2BWS4ahrXE4laALFKcq8vZfscNY8312mxfr27bLJZjnsYhSDIHmUxLu9h9N%2Fep%2B7pazwoZQw%2B1Nwi33epu7c2p8RooeqCdAHMGoOJIq3CUwIMEniRIaHVe3ZVnO2Vgsh1MstEkQUXVUc%2BjXfk3zbemxS6%2BpQmlPtUeALJ8VKj4JHvAelBqFFdSS3h1SPzQKr%2F%2BaRa0%2B0cCIWtJLauG5U%2FfbgyG01uiNqQhyzA8ddKj1OvK28AsZyN3DKE4X6AEWrU1jJx9N7RFpdPxpHU%2FtMOQG9SjfTp3Yz8KgRVKpfx88Dqhpseq606h%2F%2Bzxfh6LJ8eEDKWbxx9XEDwqzP1SVgAAAABJRU5ErkJggg%3D%3D)](https://deepwiki.com/y0ncha/aptitude-client)
![Last Commit](https://img.shields.io/github/last-commit/aptitude-stack/resolver?style=for-the-badge)

Aptitude is a deterministic, package-manager-style resolver for AI skills.

The system is intentionally split in two:

- Aptitude Server owns registry data, metadata, immutable artifacts, and discovery indexes
- Aptitude owns intent interpretation, candidate selection, dependency resolution, governance, lock generation, and execution planning

## Current CLI

Primary commands:

- `aptitude install "<query>"`
- `aptitude policy show`
- `aptitude sync --lock aptitude.lock.json`
- `aptitude manifest`

Internal preview command:

- `aptitude resolve "<query>"`

Running `aptitude` with no arguments launches the install-first wizard. `install` and `sync` stay as the promoted task commands, `policy show` exposes the effective local client policy and config layers, and `manifest` exposes the complete command and flag surface. `resolve` still exists for preview, debugging, and CI, but it is hidden from normal CLI help.

## How To Install

Install the resolver and its development dependencies with `uv`:

```bash
uv sync --extra dev
```

This creates the local environment from `pyproject.toml` and makes the published CLI available through `uv run` or an activated environment.

## Packaging And Publishing

This project builds and publishes as a normal Python package. `uv` is the build and publish tool, and the release registry is PyPI. There is no separate special "uv registry" format.

The packaging metadata lives in `pyproject.toml`:

- `[project]` defines the package name, version, dependencies, and console entry point
- `[project.scripts]` exposes both `aptitude-resolver` and `aptitude`, both mapped to `aptitude_resolver.interfaces.cli.main:main`
- `[build-system]` tells `uv` to build the package with `uv_build`

Build the package artifacts locally:

```bash
make build
```

`make build` runs `uv build --no-sources` and creates:

```text
dist/*.whl
dist/*.tar.gz
```

The wheel is the main installable artifact. It contains the `aptitude_resolver` package, its dependency metadata, and both console scripts.

For a local manual publish with a PyPI API token:

```bash
export PYPI_API_TOKEN=your-pypi-token
make build-publish
```

`make build-publish`:

- requires `PYPI_API_TOKEN`
- builds fresh artifacts into `.build-publish-dist/`
- publishes with `uv publish`
- defaults to the production PyPI upload endpoint

To rehearse the local flow against TestPyPI instead of production PyPI:

```bash
export PYPI_API_TOKEN=your-testpypi-token
make build-publish REPOSITORY=testpypi
```

For the normal release path, publish to PyPI through GitHub Actions trusted publishing:

```bash
uv version --bump patch
git tag v$(uv version --short)
git push origin v$(uv version --short)
```

The release workflow lives at `.github/workflows/publish.yml` and:

- triggers on tags matching `v*`
- builds the wheel and sdist with `uv build --no-sources`
- publishes with `pypa/gh-action-pypi-publish`
- authenticates to PyPI with GitHub OIDC trusted publishing
- does not use PyPI API tokens or repository secrets for the CI release path

The publish job uses the GitHub Environment `pypi`. That is not required by PyPI itself, but it is recommended because it gives releases a dedicated protection boundary in GitHub.

Install and run after publishing:

```bash
uv tool install aptitude-resolver
aptitude --help
```

For one-off execution without a persistent install:

```bash
uvx aptitude-resolver --help
```

Use this mental model:

- `make build` builds the distributable artifacts
- `make build-publish` performs a local token-based publish to PyPI or TestPyPI
- pushing a `v*` tag triggers the trusted publishing workflow
- `uv tool install aptitude-resolver` installs the published package
- `uvx aptitude-resolver ...` runs the published package ephemerally
- `aptitude ...` is the command end users run after installation

## How To Use

For repo-local development, typical usage starts with one of these commands:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver
PYTHONPATH=src .venv/bin/python -m aptitude_resolver --help
PYTHONPATH=src .venv/bin/python -m aptitude_resolver install "Postman Primary Skill"
PYTHONPATH=src .venv/bin/python -m aptitude_resolver policy show
PYTHONPATH=src .venv/bin/python -m aptitude_resolver sync --lock aptitude.lock.json
PYTHONPATH=src .venv/bin/python -m aptitude_resolver manifest
```

The no-args entrypoint launches the install-first wizard. Use `install` for fresh planning from a query, `policy show` to inspect the effective local client policy and config layers, `sync --lock` for replaying an existing lockfile, and `manifest` for the full capability map. For development, `python -m aptitude_resolver` is the canonical module entrypoint.

For published usage, prefer the installed CLI:

```bash
aptitude --help
aptitude install "Postman Primary Skill"
aptitude policy show
aptitude sync --lock aptitude.lock.json
aptitude manifest
```

For one-off published usage without installation:

```bash
uvx aptitude-resolver
uvx aptitude-resolver install "Postman Primary Skill"
uvx aptitude-resolver policy show
uvx aptitude-resolver sync
```

## What Works Today

- discovery-backed query resolution from human-readable input
- resolver-owned candidate version selection
- deterministic recursive dependency graph resolution
- candidate-policy filtering and graph governance before lock generation
- system, user, and workspace policy loading from `aptitude.toml`
- hard policy CLI overrides for fresh planning
- `aptitude policy show` for effective policy and config-layer inspection
- rich lockfile generation, serialization, parsing, and replay
- lock-driven execution plan generation
- local materialization from either a fresh plan or an existing lockfile
- archive-based skill installs from verified `tar.zst` artifacts
- separate execution tuning for artifact downloads and local archive extraction
- `sync --lock` as the lock-replay equivalent of `uv sync`
- registry caching and bounded transient retry
- additive telemetry for planning and materialization stages
- deterministic lockfiles for identical logical inputs
- trace output for discovery, selection, resolver, lock, and execution steps

## What Is Still Incomplete

- remote or centrally managed policy services are not implemented
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
- materialization verifies downloaded compressed artifact bytes before archive extraction

Current code now implements Governance Phase 1, profile-aware ranking, and explainability snapshots. The canonical source of truth for remaining evolution lives under [docs/README.md](docs/README.md).

## Materialization And Execution Config

Install and sync commands are unchanged, but the payload format is now archive-based. Aptitude downloads `tar.zst` skill artifacts, verifies the checksum from the lock metadata, extracts safe archive members into a staging directory, and promotes the target only after all locked skills succeed.

Workspace `aptitude.toml` can tune materialization concurrency:

```toml
[execution]
concurrent_downloads = 8
concurrent_installs = 4
```

Defaults:

- `concurrent_downloads = 8`
- `concurrent_installs = min(os.cpu_count() or 1, 4)`

Environment overrides:

```bash
APTITUDE_CONCURRENT_DOWNLOADS=8
APTITUDE_CONCURRENT_INSTALLS=4
```

There are no CLI flags for these settings; they are operational config, not per-install selection options.

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

Inspect the complete CLI surface:

```bash
aptitude manifest
```

Sync from an existing lockfile:

```bash
aptitude sync --lock aptitude.lock.json
```

Preview the resolved graph, lock, and execution plan without materializing:

```bash
uv run python -m aptitude_resolver resolve "Postman Primary Skill"
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
  resolution/
    conflict/
    graph/
    normalizer/
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
- `GET /skills/{slug}/versions`
- `GET /skills/{slug}/versions/{version}`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/versions/{version}/content`

The client keeps legacy fallbacks for older server deployments:

- `GET /skills/{slug}`
- `GET /skills/{slug}/{version}`
- `GET /skills/{slug}/{version}/content`

The `/content` endpoint name is preserved for compatibility, but install and sync now treat that response as binary `tar.zst` artifact bytes rather than markdown text.

The resolver treats the server as a source of immutable facts and candidate generation only. Final ranking, version choice, solving, policy enforcement, lock generation, and execution planning remain resolver-owned.

## Development

Requirements:

- Python `>=3.9`

Run the CLI:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver --help
PYTHONPATH=src .venv/bin/python -m aptitude_resolver install "Postman Primary Skill"
PYTHONPATH=src .venv/bin/python -m aptitude_resolver sync --lock aptitude.lock.json
```

Or via Python:

```bash
PYTHONPATH=src .venv/bin/python -m aptitude_resolver --help
```

Developer workflow:

```bash
make help
make format
make format-check
make lint
make typecheck
make test
make test-cov
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
- [docs/reference/archive-artifact-materialization.md](docs/reference/archive-artifact-materialization.md)
- [docs/roadmap/README.md](docs/roadmap/README.md)

The `docs/reference/openapi/` directory is kept as raw server reference material, not as the sole source of truth for runtime behavior.
