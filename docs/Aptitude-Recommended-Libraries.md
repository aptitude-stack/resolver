# Aptitude Client - Recommended Python Libraries

## Purpose

This document lists the Python libraries that fit the current Aptitude Client
architecture and the near-term implementation path.

The first client slice is:

- CLI-first
- sync-first
- exact-coordinate read-only
- built on a dedicated `registry/` boundary

## Must-Have Libraries Now

### Pydantic

Why:
- typed DTOs
- validated transport models
- clear serialization boundaries

Fits:
- `application/dto/`
- `registry/transport_models.py`
- output models when useful

### pydantic-settings

Why:
- typed environment-driven config
- central settings management

Fits:
- `shared/config/`

### Typer

Why:
- clear CLI ergonomics
- good fit for thin interface handlers

Fits:
- `interfaces/cli/`

### httpx

Why:
- modern sync and async HTTP client
- clean API for a dedicated registry boundary

Fits:
- `registry/`

### pytest

Why:
- strong default test framework for Python

Fits:
- `tests/unit/`
- `tests/integration/`

## Libraries To Add As Soon As The Capability Is Real

### packaging

Why:
- reliable version parsing and comparison

Fits:
- `domain/`
- `resolver/`

### resolvelib

Why:
- real dependency-solving primitives
- strong match for package-manager-style behavior

Fits:
- `resolver/solver/`

### networkx

Why:
- graph operations
- cycle detection
- dependency explanation support

Fits:
- `resolver/` once graph solving becomes real

### tenacity

Why:
- retries for transient server failures

Fits:
- `registry/`

Only add it when retry policy is a real requirement, not by default.

## Optional Later Libraries

### Pluggy

Why:
- strong plugin system once extension points are real

### structlog

Why:
- structured logging once workflow volume and observability needs grow

### diskcache

Why:
- practical local cache when caching becomes a real product need

### FastAPI and Uvicorn

Why:
- useful only if the client later exposes a local HTTP facade or debug service

They are not the center of the current client design.

## Testing Guidance

### Preferred testing shape for the current repo

- use `pytest`
- keep unit tests for pure domain, application, resolver, and interface behavior
- prefer opt-in live integration tests for the `registry/` boundary against a running server
- do not treat mocked-HTTP contract tests as the primary proof of server behavior in this repo

### When simple fakes are still fine

Small in-process fakes are still useful for:

- application use case tests
- CLI tests
- resolver tests

The key distinction is:

- server contract proof should come from the real server when practical
- higher-layer isolation can still use small fakes

## Practical Recommendation For The Current Implementation

Start with this stack:

### Must-have now
- `pydantic`
- `pydantic-settings`
- `typer`
- `httpx`
- `pytest`

### Add when resolver capability becomes real
- `packaging`
- `resolvelib`
- `networkx`

### Add when transport or ops needs justify them
- `tenacity`
- `structlog`
- `diskcache`

### Add only when the relevant feature exists
- `pluggy`
- `fastapi`
- `uvicorn`

## Layer-to-Library Map

### `interfaces/`
- `typer`
- `pydantic`

### `application/`
- `pydantic`

### `discovery/`
- no special library required yet beyond what registry and domain already expose

### `registry/`
- `httpx`
- `pydantic`
- later `tenacity` if needed

### `resolver/`
- later `resolvelib`
- later `packaging`
- later `networkx`

### `shared/`
- `pydantic-settings`
- standard library logging

### `tests/`
- `pytest`

## Final Recommendation

For Aptitude Client, the strongest foundation right now is:

- Pydantic for structured models
- pydantic-settings for config
- Typer for the CLI
- httpx for the registry boundary
- pytest for testing

Then add resolver and plugin libraries only when those capabilities are actually being implemented.
