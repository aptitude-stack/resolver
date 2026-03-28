# Plan 03 - Registry Read Adapter

## Goal
Implement the anti-corruption layer between `aptitude-client` and the server
read API, keeping all raw HTTP and transport parsing inside `registry/`.

## Stack Alignment
- HTTP client: sync `httpx`
- Transport validation: Pydantic v2
- Tests: `pytest` with opt-in live integration tests against the running server

## Scope
- Create a sync registry client under `src/aptitude_client/registry/`.
- Support only:
  - exact metadata fetch
  - direct dependency fetch
- Inject bearer authentication from shared settings.
- Parse runtime JSON into typed transport models, then map into domain-safe
  models.
- Centralize transport error handling and map server failures into explicit
  client errors.
- Preserve server-authored dependency order exactly.
- Exclude discovery, markdown content fetch, publish, and admin operations from
  the adapter surface used by milestones 03 and 04.

## Planned File Map
- Create: `src/aptitude_client/registry/__init__.py`
- Create: `src/aptitude_client/registry/client.py`
- Create: `src/aptitude_client/registry/transport_models.py`
- Create: `src/aptitude_client/registry/mappers.py`
- Create: `src/aptitude_client/domain/models/__init__.py`
- Create: `src/aptitude_client/domain/models/skill_coordinate.py`
- Create: `src/aptitude_client/domain/models/skill_metadata.py`
- Create: `src/aptitude_client/domain/models/dependency_spec.py`
- Create: `tests/integration/registry/test_live_client.py`

## Public And Internal Interfaces
- `RegistryClient.__init__(settings, http_client: httpx.Client | None = None)`
- `RegistryClient.fetch_skill_metadata(slug: str, version: str) -> SkillMetadata`
- `RegistryClient.fetch_direct_dependencies(slug: str, version: str) -> list[DependencySpec]`

Domain model decisions:
- `SkillCoordinate`
  - fields: `slug`, `version`
- `SkillMetadata`
  - fields:
    - `coordinate: SkillCoordinate`
    - `name`
    - `description`
    - `tags`
    - `rendered_summary`
    - `content_checksum_algorithm`
    - `content_checksum_digest`
    - `lifecycle_status`
    - `trust_tier`
    - `published_at`
- `DependencySpec`
  - fields:
    - `slug`
    - `version`
    - `optional`
    - `markers`

## Error Translation Rules
- `404` with `SKILL_VERSION_NOT_FOUND` -> `SkillNotFoundError`
- `422` with `INVALID_REQUEST` -> `InvalidCoordinateError`
- `401` or `403` -> `RegistryAccessError`
- connection failures and timeouts -> `RegistryUnavailableError`
- malformed JSON or missing required response fields -> `UnexpectedRegistryResponseError`

## Architecture Impact
- Makes `registry/` the only layer that knows raw URLs, headers, status codes,
  and JSON field names for Aptitude Server.
- Keeps domain, discovery, and application code independent of transport payload details.
- Creates stable internal models the rest of the client can build on.

## Deliverables
- Authenticated sync registry client.
- Pydantic transport models for the two runtime read responses and the error
  envelope.
- Mapper functions from transport models to domain models.
- Error translation that preserves message context but returns client-owned
  exceptions.
- Live integration tests that prove the adapter against a running Aptitude Server.

## Acceptance Criteria
- Non-transport layers never parse server JSON directly.
- The registry adapter is the only layer that knows the runtime read endpoint
  paths.
- Dependency order is preserved exactly as the server returned it.
- The adapter is verified against the real running server contract.

## Test Plan
- Metadata happy path returns a fully mapped `SkillMetadata`.
- Direct dependency happy path returns ordered `DependencySpec` models.
- `404` exact coordinate returns `SkillNotFoundError`.
- `422` invalid version path returns `InvalidCoordinateError`.
- Auth header propagation works against the live server.
- The integration tests publish unique skills and read them back through the adapter.
