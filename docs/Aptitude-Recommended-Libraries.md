# Aptitude Client — Recommended Python Libraries

## Purpose

This document lists the Python libraries that are a good fit for building the **Aptitude Client**.
It is meant for the `docs/` folder and focuses on libraries that match the current architecture and flow of the project.

The current project already includes **FastAPI**, **Uvicorn**, and **Pydantic** in the lockfile, which confirms they are already part of the active stack. In the architecture notes, the client is also described as using **Typer** for CLI, **resolvelib** for dependency solving, **Pluggy** for plugins, and **networkx** for dependency graph handling.

---

## 1. Core libraries to use

### Pydantic
**Why use it**
- Strong typed models for requests, responses, manifests, lock files, and configuration
- Validation at boundaries between layers
- Very useful for DTOs, domain-safe parsing, and API schemas

**Where it fits**
- `application/dto/`
- `domain/model/`
- `lockfile/model/`
- `interfaces/mcp/` and `interfaces/sdk/`

**Suggested usage**
- Skill metadata model
- Version constraint model
- lock file schema
- execution plan schema

**Why it is especially important here**
Aptitude has many structured concepts: skill references, versions, dependencies, policies, lock entries, and execution plans. Pydantic is the cleanest way to model these objects safely and consistently.

---

### FastAPI
**Why use it**
- Clean API framework
- Native integration with Pydantic
- Great for typed request/response contracts
- Good fit if part of the client exposes a local HTTP API or adapter layer

**Where it fits**
- local service façade if the client exposes endpoints
- debug/admin endpoints
- internal local orchestration service if needed

**Important note**
If the Aptitude Client is mainly CLI + MCP and not a long-running HTTP service, FastAPI is useful mainly for optional adapters, not as the center of the client itself.

---

### Uvicorn
**Why use it**
- ASGI server for running FastAPI
- Lightweight and standard

**Where it fits**
- only if you keep a local API process
- local development server

**Important note**
Use Uvicorn only when there is an HTTP app to run. It is not needed for pure CLI-only flows.

---

### Typer
**Why use it**
- Excellent CLI framework for Python
- Very readable commands
- Great developer experience
- Built on Click, which is stable and mature

**Where it fits**
- `interfaces/cli/`

**Suggested commands**
- `aptitude resolve "..."`
- `aptitude search "..."`
- `aptitude lock`
- `aptitude explain`

**Why it fits Aptitude**
Your architecture already defines the CLI as a first-class interface, so Typer is the most natural choice.

---

## 2. Resolution and dependency solving

### resolvelib
**Why use it**
- Designed exactly for dependency resolution problems
- Good match for package-manager-like behavior
- Lets you implement deterministic solving rules

**Where it fits**
- `resolver/solver/`

**Suggested usage**
- version constraint solving
- backtracking when dependencies conflict
- stable selection strategy

**Why it fits Aptitude**
Aptitude behaves like a package manager for skills, so a real resolver library is much better than handwritten ad-hoc solving logic.

---

### packaging
**Why use it**
- Standard Python library for version parsing and specifier handling
- Safer than inventing your own version logic

**Where it fits**
- `domain/model/`
- `resolver/normalizer/`
- `resolver/validation/`

**Suggested usage**
- parse versions
- compare versions
- validate version constraints

**Why it matters**
If Aptitude versions behave like software versions, this library should be a default part of the core domain.

---

### networkx
**Why use it**
- Very useful for dependency graphs
- Easy traversal, cycle detection, and path explanation

**Where it fits**
- `resolver/graph/`
- `resolver/conflict/`
- `resolver/replay/`

**Suggested usage**
- build dependency graph
- detect cycles
- explain why a skill was included
- compute transitive dependencies

---

## 3. Plugin and extension system

### pluggy
**Why use it**
- Standard lightweight plugin framework
- Great for extension points and hooks
- Used successfully in mature ecosystems

**Where it fits**
- `plugins/hookspecs/`
- `plugins/manager/`
- `plugins/builtins/`
- `plugins/custom/`

**Suggested hook examples**
- score candidate
- validate selection
- estimate token cost
- enrich lock
- apply organization rule

**Why it fits Aptitude**
Your architecture already calls for a plugin system. Pluggy is probably the cleanest choice for this.

---

## 4. Configuration and environment handling

### pydantic-settings
**Why use it**
- Clean settings management on top of Pydantic
- Easy loading from environment variables and `.env`
- Keeps config typed and centralized

**Where it fits**
- `shared/config/`

**Suggested usage**
- server base URL
- cache paths
- feature flags
- trust policy toggles
- debug options

---

### python-dotenv
**Why use it**
- Helpful in local development
- Loads `.env` values simply

**Where it fits**
- local development only
- optional alongside `pydantic-settings`

---

## 5. HTTP communication and retries

### httpx
**Why use it**
- Modern HTTP client for Python
- Supports sync and async
- Cleaner API than older alternatives for typed modern codebases

**Where it fits**
- `discovery/registry_api/`
- `execution/fetch/`

**Suggested usage**
- search calls to Aptitude Server
- fetch exact metadata
- download manifests or artifact metadata

**Why it fits Aptitude**
The client-server split in Aptitude depends on clean communication with the registry. `httpx` is a strong fit for that layer.

---

### tenacity
**Why use it**
- Retry handling for unstable remote calls
- Good for transient failures

**Where it fits**
- `discovery/registry_api/`
- `execution/fetch/`

**Suggested usage**
- retry search requests
- retry metadata fetches
- apply backoff rules

---

## 6. Logging, tracing, and telemetry

### structlog
**Why use it**
- Structured logging
- Very useful for traces and decision explanations
- Better than plain string logging once the system grows

**Where it fits**
- `telemetry/`
- `domain/tracing/`
- `application/use_cases/`

**Suggested usage**
- resolution decisions
- plugin timing
- policy checks
- fetch/verify events

---

### loguru (optional alternative)
**Why use it**
- Very easy logging setup
- Nice during early development

**Important note**
If you want long-term structured observability, `structlog` is usually the better architectural fit.

---

### prometheus-client
**Why use it**
- Good for metrics if you expose them

**Where it fits**
- `telemetry/metrics/`

**Suggested usage**
- resolve duration
- cache hit ratio
- plugin runtime
- fetch failures

---

## 7. Caching and local storage

### diskcache
**Why use it**
- Simple persistent cache
- Good fit for local search results and metadata caching

**Where it fits**
- `cache/search/`
- `cache/metadata/`
- `cache/artifact/`
- `cache/replay/`

**Why it fits Aptitude**
You already plan local caching. `diskcache` is practical and much easier than building cache persistence from scratch.

---

### orjson
**Why use it**
- Very fast JSON serialization/deserialization
- Good for lock files, cache data, and API payloads

**Where it fits**
- `lockfile/serializer/`
- `cache/`
- `interfaces/`

**Important note**
This is an optimization library, not a must-have on day one.

---

## 8. Security and verification

### cryptography
**Why use it**
- Useful for signature verification and integrity-related work

**Where it fits**
- `governance/trust/`
- `execution/verify/`

**Suggested usage**
- verify signed metadata
- validate provenance information

---

### hashlib
**Why use it**
- Built into Python
- Enough for checksum verification in many cases

**Where it fits**
- `execution/verify/`

**Suggested usage**
- SHA256 checksum verification for artifacts and manifests

---

## 9. Testing libraries

### pytest
**Why use it**
- Best default testing framework for Python projects

**Where it fits**
- `tests/`

**Suggested usage**
- unit tests for resolver
- integration tests for registry API
- lock replay tests
- plugin hook tests

---

### pytest-asyncio
**Why use it**
- Needed if parts of the system are async

**Where it fits**
- async API and fetch tests

---

### respx
**Why use it**
- Mocking for `httpx`
- Excellent for API client tests

**Where it fits**
- `tests/discovery/`
- `tests/execution/`

---

## 10. Standard library features you should absolutely use

Do not forget that some important tools already exist in Python itself and should be preferred before adding packages.

### dataclasses
Useful for internal lightweight objects when full validation is not needed.

### pathlib
Use instead of raw path strings.

### typing
Essential for the whole codebase.

### enum
Very useful for lifecycle state, trust level, resolution outcome, and policy modes.

### abc / Protocol
Good for interfaces and pluggable abstractions.

### functools
Helpful for memoization and composition.

### hashlib
Useful for checksums.

### json
Enough for basic lock serialization early on.

---

## Recommended package groups by layer

## `interfaces/`
- `typer`
- `fastapi` (only if needed for local HTTP adapter)
- `uvicorn` (only with FastAPI)
- `pydantic`

## `application/`
- `pydantic`
- `structlog`

## `domain/`
- `pydantic`
- `packaging`
- standard `enum`, `typing`, `dataclasses`

## `discovery/`
- `httpx`
- `tenacity`
- `pydantic`

## `resolver/`
- `resolvelib`
- `packaging`
- `networkx`

## `plugins/`
- `pluggy`

## `governance/`
- `cryptography`
- `pydantic`

## `lockfile/`
- `pydantic`
- `orjson` (optional)

## `execution/`
- `httpx`
- `tenacity`
- `hashlib`
- `cryptography`

## `cache/`
- `diskcache`
- `orjson` (optional)

## `telemetry/`
- `structlog`
- `prometheus-client` (optional)

## `tests/`
- `pytest`
- `pytest-asyncio`
- `respx`

---

## My practical recommendation for the first implementation

If you want a clean first version, start with this stack:

### Must-have now
- `pydantic`
- `pydantic-settings`
- `typer`
- `httpx`
- `resolvelib`
- `packaging`
- `pluggy`
- `networkx`
- `pytest`

### Add very soon after
- `tenacity`
- `structlog`
- `diskcache`
- `pytest-asyncio`
- `respx`

### Add only when the relevant feature is real
- `fastapi`
- `uvicorn`
- `cryptography`
- `prometheus-client`
- `orjson`

---

## Example `pyproject.toml` dependency section

```toml
[project]
dependencies = [
  "pydantic>=2.0",
  "pydantic-settings>=2.0",
  "typer>=0.12",
  "httpx>=0.27",
  "resolvelib>=1.0",
  "packaging>=24.0",
  "pluggy>=1.0",
  "networkx>=3.0",
]

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "respx>=0.21",
]
```

---

## Final recommendation

For Aptitude Client, the strongest foundation is:

- **Pydantic** for data models and validation
- **Typer** for CLI
- **httpx** for server communication
- **resolvelib** for dependency solving
- **packaging** for version semantics
- **Pluggy** for plugins
- **networkx** for dependency graphs
- **pytest** for tests

If you want the architecture to stay clean, avoid adding many libraries too early. Prefer a small, deliberate set where each package clearly maps to one architectural responsibility.
