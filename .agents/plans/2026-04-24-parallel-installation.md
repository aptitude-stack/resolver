# Parallel Skill Installation Plan

## Summary

Create branch `feature/parallel-installation` from latest `dev`, then implement lock-driven parallel skill materialization.

Implementation follows Aptitude's lock-first architecture: resolution stays unchanged, execution still consumes lock data only, and materialization becomes parallel inside the staging directory.

Research anchors:

- uv exposes bounded concurrency through settings and environment variables, including `concurrent-downloads`, `concurrent-installs`, and `UV_CONCURRENT_INSTALLS`, rather than ordinary day-to-day CLI flags.
- uv defaults install concurrency to available CPU cores and keeps download/build/install concurrency as separate work-type controls.
- Python's stdlib `ThreadPoolExecutor` fits Aptitude's current sync, I/O-heavy materialization model without an async registry refactor.
- HTTPX documents that sync `Client` instances can be shared between threads, which fits Aptitude's registry adapter shape.

References:

- https://docs.astral.sh/uv/reference/settings/#concurrent-installs
- https://docs.astral.sh/uv/reference/environment/#uv_concurrent_installs
- https://www.python-httpx.org/api/#client

## Key Changes

- Add `MaterializationOptions(concurrent_installs: int | None)` under execution and pass it into `materialize_lockfile`.
- Add `[execution] concurrent_installs = N` to `aptitude.toml` parsing and `APTITUDE_CONCURRENT_INSTALLS` env support.
- Use precedence: built-in default -> system config -> user config -> workspace config -> environment. Last non-null wins.
- Do not add `--concurrent-installs` in v1.
- Default worker count: available CPU cores, minimum `1`, capped by locked skill count.
- Implement whole-skill parallelism: each locked skill fetches content, verifies checksum, and writes its own staging path concurrently.
- Preserve deterministic output: `installed_skills`, trace entries, lock artifacts, and execution plan remain ordered by lockfile install order, never completion order.
- Keep promotion atomic: write everything under a temporary staging root, then replace the final target only after all workers succeed.
- Add a narrow lock in `CacheStore` around cache `get`/`set`/`close`.
- No cosmetic-only cleanup.

## Public Interfaces

New TOML section:

```toml
[execution]
concurrent_installs = 4
```

New environment variable:

```powershell
$env:APTITUDE_CONCURRENT_INSTALLS = "4"
```

Existing CLI commands remain unchanged:

- `aptitude install ...`
- `aptitude sync --lock ...`

## Test Plan

- Unit test parallel materialization with a delayed fake registry to prove multiple skills are in flight.
- Unit test deterministic result ordering when workers finish out of order.
- Unit test `concurrent_installs=1` preserves serial behavior.
- Unit test checksum failure does not promote a partial target and surfaces the original checksum error.
- Unit test config/env parsing, precedence, and invalid values like `0` or negative numbers.
- Update existing materialization tests that assume registry call order; assert output order instead.
- Run `uv run pytest`, focused execution/config tests, and `uv run mypy`.

## Assumptions

- First implementation uses stdlib threads, not an async registry refactor.
- Parallelism applies only to lock-driven materialization, not discovery or resolution.
- Aptitude config uses snake_case (`concurrent_installs`) to match current Aptitude TOML style, even though uv uses hyphenated setting names.
