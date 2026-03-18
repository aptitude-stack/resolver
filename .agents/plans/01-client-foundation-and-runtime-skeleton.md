# Plan 01 - Client Foundation and Runtime Skeleton

## Goal
Turn the current repository from empty package scaffolding into an importable,
testable client foundation with typed configuration, shared logging bootstrap,
base errors, and an initial test harness.

## Stack Alignment
- Runtime baseline: Python `>=3.9`
- Runtime deps to add: `pydantic`, `pydantic-settings`, `httpx`, `typer`
- Dev deps to add: `pytest`
- Test execution: local, offline, no network required

## Scope
- Add package markers and minimal entrypoints required to make the existing
  package tree importable.
- Extend `pyproject.toml` with the runtime and dev dependency set required by
  milestones 03 and 04.
- Add shared settings under `src/aptitude_client/shared/config/` with typed
  environment loading for:
  - `APTITUDE_SERVER_BASE_URL`
  - `APTITUDE_READ_TOKEN`
  - `APTITUDE_SERVER_TIMEOUT_SECONDS`
- Add shared logging bootstrap under `src/aptitude_client/shared/logging/`.
- Add initial client-side error hierarchy under `src/aptitude_client/domain/errors/`.
- Add the initial test layout and pytest configuration.
- Do not add registry transport logic, CLI commands, or resolver behavior in
  this milestone.

## Planned File Map
- Modify: `pyproject.toml`
- Create: `src/aptitude_client/__init__.py`
- Create: `src/aptitude_client/shared/config/__init__.py`
- Create: `src/aptitude_client/shared/config/settings.py`
- Create: `src/aptitude_client/shared/logging/__init__.py`
- Create: `src/aptitude_client/shared/logging/configure.py`
- Create: `src/aptitude_client/domain/errors/__init__.py`
- Create: `src/aptitude_client/domain/errors/client_errors.py`
- Create: `tests/unit/shared/config/test_settings.py`
- Create: `tests/unit/shared/test_imports.py`

## Architecture Impact
- Establishes the lowest-level reusable infrastructure the rest of the client
  will depend on without leaking transport or CLI behavior into shared code.
- Makes configuration and logging explicit before HTTP and CLI work begins.
- Creates a single place for client-owned error types before server error
  translation is introduced.

## Deliverables
- Importable Python packages for the current repo structure.
- Typed settings object with env-based loading and defaults:
  - `APTITUDE_SERVER_TIMEOUT_SECONDS` default: `5.0`
  - `APTITUDE_SERVER_BASE_URL` required
  - `APTITUDE_READ_TOKEN` required
- Minimal logging configurator that can be reused by the CLI later.
- Base error types:
  - `AptitudeClientError`
  - `SkillNotFoundError`
  - `InvalidCoordinateError`
  - `RegistryUnavailableError`
  - `RegistryAccessError`
  - `UnexpectedRegistryResponseError`
- Pytest configuration embedded in `pyproject.toml` or added in a dedicated
  config file if the dependency-group syntax makes that cleaner.

## Acceptance Criteria
- `src/aptitude_client/` imports successfully as a package.
- Settings load successfully from environment variables and fail clearly when
  required values are missing.
- Tests run without making network requests.
- The milestone introduces no business logic and no direct server calls.

## Test Plan
- Settings happy path with all required env vars present.
- Settings failure path when base URL is missing.
- Settings failure path when read token is missing.
- Import smoke test for the root package and the shared/domain packages.
- Logging bootstrap smoke test if logging setup contains behavior beyond a
  trivial wrapper.
