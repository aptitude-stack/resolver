# Module Responsibilities

## Purpose

This document explains what each main package in `aptitude-client` is allowed
to do, what it must not do, and how the packages relate to each other.

## Architectural Baseline

Aptitude Client is responsible for:

- interpreting user intent
- discovering candidate skills
- reranking candidates using client context
- resolving dependencies deterministically
- enforcing client-side policies
- generating lock outputs
- building execution plans

The server remains responsible for registry search, metadata storage, immutable
artifact records, and publish/read governance.

## Package Map

Current package structure:

```text
src/aptitude_client/
  application/
    dto/
    use_cases/
  discovery/
    intent/
    registry_api/
  domain/
    errors/
    models/
  interfaces/
    cli/
  resolver/
    solver/
  shared/
    config/
    logging/
```

## Dependency Direction

Allowed:

- `interfaces -> application`
- `application -> domain`
- `application -> discovery`
- `application -> resolver`
- `application -> shared`
- `discovery -> domain`
- `discovery -> shared`
- `resolver -> domain`
- `resolver -> shared`

Forbidden:

- `domain -> interfaces`
- `domain -> discovery.registry_api`
- `interfaces -> resolver` for business-logic bypass
- `interfaces -> discovery` for business-logic bypass
- `shared -> application`, `shared -> discovery`, `shared -> resolver`

## interfaces/

### Owns

- parsing raw external input
- mapping external input to application DTOs
- calling use cases
- formatting user-facing output
- setting process exit codes

### Must not own

- business rules
- dependency solving
- policy decisions
- registry query logic

## application/

### Owns

- use-case entrypoints
- workflow sequencing
- DTO definitions for use-case boundaries
- coordination across discovery, resolver, policy, lock, and planning components
- translation of lower-level errors into application-level outcomes

### Must not own

- HTTP transport details
- CLI formatting
- low-level dependency-solving internals

## application/dto/

### Owns

- request DTOs
- result DTOs
- stable orchestration payloads

Use Pydantic for DTOs and external-boundary validation where it improves clarity.

## discovery/

### Owns

- intent interpretation
- search request construction
- registry API communication
- candidate mapping
- local reranking before final solving

### Must not own

- final dependency graph solving
- lock generation
- execution-plan generation

### discovery/intent/

Owns prompt or input interpretation into structured search intent.

### discovery/registry_api/

Owns the client for server discovery endpoints and exact metadata fetches.

No other business layer should need to know raw transport details.

## resolver/

### Owns

- requirement normalization
- version selection
- dependency expansion
- graph building
- conflict analysis
- validation of resolved outcomes
- replay from pinned lock state

### Must not own

- raw user prompt parsing
- CLI formatting
- HTTP endpoint orchestration

## domain/

### Owns

- entities
- value objects
- client-side policies
- domain services where appropriate
- domain-specific error types
- deterministic rule concepts

### Must not own

- terminal formatting
- FastAPI or HTTP client objects
- registry transport payload schemas

## shared/

### Owns

- config loading
- logging setup
- shared protocol definitions
- hash helpers
- generic utility functions with low business meaning

### Must not own

- feature workflows
- dependency solving
- candidate reranking rules
- registry semantics

## Responsibility Test

When adding new code, ask:

1. Is this user-entrypoint parsing or output formatting? -> `interfaces/`
2. Is this workflow orchestration? -> `application/`
3. Is this about interpreting a request and retrieving/reranking candidates? -> `discovery/`
4. Is this about solving dependencies or validating a resolved graph? -> `resolver/`
5. Is this a core business concept or invariant? -> `domain/`
6. Is this generic support code with no feature ownership? -> `shared/`

## Common Misplacements to Avoid

### Anti-pattern: fat CLI

CLI parses input, calls registry, reranks, solves, and prints everything.

Fix:
- keep the CLI thin
- move workflow into a use case

### Anti-pattern: transport leakage into domain

Fix:
- map transport models in discovery or application boundaries

### Anti-pattern: feature logic in shared

Fix:
- move feature-owned code into its real module

## Suggested Near-Term Additions

Based on the architecture docs and current repo shape, these future packages are
reasonable when the implementation grows:

- `application/commands/`
- `application/queries/`
- `discovery/query_builder/`
- `discovery/reranking/`
- `resolver/graph/`
- `resolver/conflict/`
- `resolver/validation/`
- `resolver/replay/`

Do not create them empty just to match the diagram.
