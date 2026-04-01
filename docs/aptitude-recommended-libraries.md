# Aptitude Resolver Recommended Libraries

## Purpose

This document lists the Python libraries that fit the current Aptitude Resolver architecture.

The current client is:

- CLI-first
- sync-first
- lock-driven for execution
- built around a dedicated `registry/` boundary

## Current Active Stack

These libraries are already aligned with the repository and current implementation.

### Pydantic

Use for:

- application DTOs
- registry transport models
- other explicit serialization boundaries

### pydantic-settings

Use for:

- typed environment-backed configuration in `shared/config/`

### Typer

Use for:

- CLI entrypoints in `interfaces/cli/`

### httpx

Use for:

- registry HTTP transport in `registry/`

### packaging

Use for:

- semantic version parsing and comparison in deterministic resolver logic

### pytest

Use for:

- unit tests
- opt-in live integration tests

## Good Future Additions

Add these only when the corresponding capability becomes real.

### Pluggy

Good fit for:

- a future `plugins/` package

### structlog

Good fit for:

- richer structured logging and observability

### diskcache

Good fit for:

- a future local cache that does not affect correctness

### tenacity

Good fit for:

- retries around transient registry failures, if retry policy becomes a real requirement

## Libraries To Add Only If Complexity Justifies Them

### resolvelib

Potential fit for:

- more advanced dependency solving

Do not add it just because it is available. The current resolver is custom and deterministic.

### networkx

Potential fit for:

- richer graph analysis
- debugging or visualization

Do not add it unless graph operations clearly outgrow the current explicit implementation.

## Libraries That Are Not Required Today

### FastAPI / Uvicorn

Only add these if Aptitude Resolver grows a local HTTP facade or service surface.

They are not part of the current CLI-first architecture.

## Testing Guidance

Preferred testing style in this repo:

- use `pytest`
- keep unit tests around deterministic layer behavior
- use opt-in live integration tests for the real registry boundary when practical
- use small in-process fakes for application, CLI, lockfile, and execution tests

## Practical Recommendation

Right now the best-fit foundation is:

- `pydantic`
- `pydantic-settings`
- `typer`
- `httpx`
- `packaging`
- `pytest`

Add plugin, cache, retry, or observability libraries only when those capabilities are real implemented responsibilities.
