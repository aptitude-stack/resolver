# Plan 04 - CLI Exact Resolve Vertical Slice

## Goal
Deliver the first end-to-end client command using exact coordinates, proving
the repository can parse a CLI request, call the registry adapter, shape a
deterministic result, and print stable JSON.

## Stack Alignment
- CLI: Typer
- DTOs: Pydantic v2
- Transport: sync `httpx` via `RegistryClient`
- Tests: `pytest`; live server coverage remains at the registry boundary, while application and CLI layers may use small in-process fakes as needed

## Scope
- Add a thin CLI under `src/aptitude_client/interfaces/cli/`.
- Add one application use case under `src/aptitude_client/application/use_cases/`.
- Add request and result DTOs under `src/aptitude_client/application/dto/`.
- Add a minimal resolver shaper under `src/aptitude_client/resolver/solver/`.
- Support this exact first public command:
  - `aptitude resolve <slug> --version <version>`
- Flow:
  1. CLI parses `slug` and `version`
  2. use case fetches exact metadata through `RegistryClient`
  3. use case fetches direct dependencies through `RegistryClient`
  4. resolver shapes a deterministic read result without solving
  5. CLI prints stable JSON to stdout
- Do not add discovery-based UX, candidate selection, recursive solving,
  lockfiles, plugins, or execution planning.

## Planned File Map
- Modify: `pyproject.toml`
- Create: `src/aptitude_client/application/dto/__init__.py`
- Create: `src/aptitude_client/application/dto/resolve_request_dto.py`
- Create: `src/aptitude_client/application/dto/resolve_result_dto.py`
- Create: `src/aptitude_client/application/use_cases/__init__.py`
- Create: `src/aptitude_client/application/use_cases/resolve_exact_skill.py`
- Create: `src/aptitude_client/interfaces/cli/__init__.py`
- Create: `src/aptitude_client/interfaces/cli/app.py`
- Create: `src/aptitude_client/interfaces/cli/main.py`
- Create: `src/aptitude_client/resolver/solver/__init__.py`
- Create: `src/aptitude_client/resolver/solver/exact_resolve.py`
- Create: `tests/unit/application/use_cases/test_resolve_exact_skill.py`
- Create: `tests/unit/interfaces/cli/test_app.py`

## Public And Internal Interfaces

### Public CLI
- `aptitude resolve <slug> --version <version>`

CLI behavior decisions:
- `slug` is a required positional argument
- `--version` is a required option
- successful output goes to stdout as formatted JSON
- server and domain failures go to stderr as JSON and exit code `1`
- CLI usage errors remain Typer defaults

### Application DTOs
- `ResolveRequestDto`
  - `slug`
  - `version`
- `ResolveResultDto`
  - `requested_coordinate`
  - `selected_coordinate`
  - `skill`
  - `dependencies`
  - `status`

## Result Shape

```json
{
  "requested_coordinate": {
    "slug": "python.lint",
    "version": "1.2.3"
  },
  "selected_coordinate": {
    "slug": "python.lint",
    "version": "1.2.3"
  },
  "skill": {
    "name": "Python Lint",
    "description": "Linting skill",
    "tags": ["python", "lint"],
    "rendered_summary": "Lint Python files consistently.",
    "lifecycle_status": "published",
    "trust_tier": "internal"
  },
  "dependencies": [
    {
      "slug": "python.base",
      "version": "1.0.0",
      "optional": false,
      "markers": ["linux"]
    }
  ],
  "status": "resolved"
}
```

## Resolver Behavior
- The resolver does not choose among candidates in this milestone.
- The resolver simply converts exact metadata plus direct dependencies into a
  stable result DTO.
- Dependency order is preserved as returned by the registry adapter.
- `selected_coordinate` always equals `requested_coordinate` in this milestone.

## Architecture Impact
- Proves the intended layered flow:
  - `interfaces -> application -> registry -> resolver -> output`
- Keeps the CLI thin and prevents direct transport access from the interface
  layer.
- Creates the first user-visible behavior without overcommitting to future
  discovery or solving semantics.

## Deliverables
- Console script entry in `pyproject.toml` pointing to
  `aptitude_client.interfaces.cli.main:main`
- Typer app with a single `resolve` command
- Use case that orchestrates metadata read, dependency read, and result shaping
- Stable success JSON and structured stderr error JSON

## Acceptance Criteria
- The command succeeds for an existing exact coordinate.
- The same server response produces identical stdout JSON.
- Not-found and invalid-coordinate failures are surfaced cleanly and exit
  non-zero.
- No part of the flow bypasses the application layer to call the registry
  adapter directly from the CLI.

## Test Plan
- CLI happy path prints the expected JSON structure.
- CLI missing `--version` follows Typer usage failure behavior.
- Use case happy path composes metadata and dependencies correctly.
- `SkillNotFoundError` is printed to stderr as structured JSON and exits `1`.
- `InvalidCoordinateError` is printed to stderr as structured JSON and exits `1`.
- Dependency ordering in stdout matches the registry adapter response order.
