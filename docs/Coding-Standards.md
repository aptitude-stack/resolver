# Coding Standards

## Purpose

This document defines how code should be written in `aptitude-client` so that
the repository stays deterministic, layered, and easy for both humans and
agents to extend.

It complements:

- `docs/Aptitude Client Architecture.md`
- `docs/Aptitude-Recommended-Libraries.md`
- `.agents/rules/repo.md`

The architecture establishes that the client owns request interpretation,
candidate reranking, dependency solving, lock generation, and execution
planning, while the server remains a registry and retrieval system. Keep code
aligned with that boundary.

## Current Repository Reality

Write code against the current repository structure, not against future folders
that exist only in architecture diagrams.

Current main packages under `src/aptitude_client/`:

- `application/`
- `discovery/`
- `domain/`
- `interfaces/`
- `resolver/`
- `shared/`

If a future module is needed, add it only when the use case clearly justifies it.

## Core Engineering Rules

### 1. Keep behavior deterministic

For the same:

- user request
- registry snapshot
- policy inputs
- installed-state inputs
- lock/replay inputs

the client should produce the same selected versions, lock output, and decision
trace.

When ordering is ambiguous, define a tie-break explicitly.

### 2. Keep layers strict

Allowed dependency direction:

- `interfaces -> application`
- `application -> domain`, `discovery`, `resolver`, `shared`
- `discovery -> domain`, `shared`
- `resolver -> domain`, `shared`
- `domain ->` no interface or transport layer
- `shared ->` no feature-specific modules

Do not bypass the application layer from CLI or other entrypoints.

### 3. Prefer simple, explicit code

Prefer:

- small classes
- small functions
- explicit DTOs
- explicit return types
- explicit error types
- explicit tie-break rules

Avoid hidden global state or overly clever abstractions.

### 4. Design for explainability

Resolution and selection logic must be explainable.

When implementing logic that affects outcomes, ensure there is a way to record:

- why a candidate was kept or removed
- why a version was selected
- why a conflict occurred
- why a policy blocked a result

## Python and Naming

- Use type hints on all public functions and methods.
- Prefer `snake_case` for Python files, functions, methods, and variables.
- Use `PascalCase` for classes.
- Use `UPPER_SNAKE_CASE` for constants.
- Prefer boolean names like `is_trusted`, `has_conflicts`, `is_deprecated`.

## Model Rules

### Domain models

Use the domain layer for core concepts and invariants.

Examples:

- `SkillId`
- `SkillVersion`
- `Dependency`
- `VersionConstraint`
- `ResolutionResult`

Domain models should not know about:

- FastAPI
- CLI formatting
- HTTP response objects
- raw registry transport payloads

### DTOs

Use DTOs to move data between layers.

DTOs belong under `application/dto/` when they define use-case inputs and outputs.

Examples:

- `ResolveRequestDto`
- `ResolveResultDto`
- `SearchRequestDto`

### Pydantic usage

The repository already uses `pydantic` and `fastapi` in the lockfile. Use
Pydantic where validation and clear serialization boundaries matter,
especially for DTOs and external payloads.

Use Pydantic for:

- request DTOs
- response DTOs
- parsed config objects
- registry transport models when strict validation is useful

Do not use Pydantic inside domain logic just because it is available. Domain
types should stay focused on business meaning, not transport convenience.

## Function Design Rules

Prefer functions that do one thing well.

A good function usually has:

- a clear name
- a small number of parameters
- a single responsibility
- a typed return value
- no hidden mutation

If a function needs too many inputs, group them into a typed object.

## Use Case Rules

A use case coordinates workflow. It should not contain all implementation logic.

A use case may:

- validate the request shape
- call discovery components
- call resolver components
- call policy checks
- assemble the final result DTO

A use case should not:

- embed raw HTTP client details
- embed CLI printing
- duplicate solver internals

## Discovery Rules

The discovery layer owns:

- user-intent normalization
- registry query construction
- registry API calls
- local reranking of candidates

The discovery layer must not:

- own final dependency solving
- generate locks
- create execution plans

## Resolver Rules

The resolver layer owns:

- requirement normalization
- dependency solving
- graph construction
- conflict explanation
- resolution validation
- replay from lock input

If tie-break logic is added, document it in code and tests.

## Shared Module Rules

The `shared/` package is for cross-cutting support only.

Allowed examples:

- config loading
- logging setup
- clock abstraction
- hashing helpers

Not allowed:

- candidate reranking logic
- dependency solving logic
- registry query semantics

## Error Handling Rules

Use explicit custom errors for expected business failures.

Examples:

- `SkillNotFoundError`
- `RegistryUnavailableError`
- `DependencyConflictError`
- `PolicyViolationError`

Guidelines:

- raise domain errors for domain failures
- translate infrastructure errors at layer boundaries
- avoid leaking low-level library errors directly to interfaces

## Logging Rules

Log:

- start and end of major workflows
- registry calls
- candidate counts
- policy rejections
- conflict summaries
- lock generation summaries

Do not log secrets, tokens, or sensitive payloads.

## Testing Rules

Minimum expectations:

- happy-path test
- failure-path test
- determinism test where ordering or resolution matters

### What to test by layer

`domain/`
- invariants
- value semantics
- error behavior

`application/`
- orchestration
- result shaping
- error translation

`discovery/`
- intent extraction
- query building
- reranking rules

`resolver/`
- version selection
- backtracking
- conflicts
- validation
- replay behavior

## Do / Don't

### Do

- keep interfaces thin
- define DTOs explicitly
- keep domain models meaningful
- document tie-break rules
- add tests before or with implementation
- prefer replacement over compatibility glue in unfinished areas

### Don't

- put business logic in CLI handlers
- let domain import transport code
- hide important decisions inside helpers with no tests
- treat advisory server ranking as authoritative
- add generic abstractions before a concrete need exists
