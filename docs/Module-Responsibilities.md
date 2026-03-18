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
  domain/
    errors/
    models/
  interfaces/
    cli/
  registry/
  resolver/
    solver/
  shared/
    config/
    logging/
```

## Dependency Direction

Allowed:

- `interfaces -> application`
- `application -> domain | discovery | registry | resolver | shared`
- `discovery -> registry | domain | shared`
- `registry -> domain | shared`
- `resolver -> domain | shared`

Forbidden:

- `domain -> interfaces`
- `domain -> registry`
- `interfaces -> registry` for business-logic bypass
- `interfaces -> discovery` for business-logic bypass
- `shared -> application | discovery | registry | resolver`

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
- coordination across discovery, registry, resolver, policy, lock, and planning components
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
- discovery request construction
- candidate shaping and reranking
- discovery-specific orchestration over registry clients

### Must not own

- generic server transport
- exact metadata reads unrelated to discovery behavior
- final dependency graph solving
- lock generation
- execution-plan generation

### discovery/intent/

Owns prompt or input interpretation into structured discovery intent.

## registry/

### Owns

- all Aptitude Server HTTP communication
- auth header injection
- endpoint path knowledge
- request and response parsing
- transport error-envelope parsing
- transport-to-domain mapping

### Must not own

- user-intent interpretation
- candidate reranking policy
- dependency solving
- CLI formatting

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
- HTTP client objects
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
3. Is this about interpreting a request or reranking discovery candidates? -> `discovery/`
4. Is this about talking to Aptitude Server? -> `registry/`
5. Is this about solving dependencies or validating a resolved graph? -> `resolver/`
6. Is this a core business concept or invariant? -> `domain/`
7. Is this generic support code with no feature ownership? -> `shared/`

## Common Misplacements to Avoid

### Anti-pattern: fat CLI

CLI parses input, calls the registry, resolves dependencies, and prints everything.

Fix:
- keep the CLI thin
- move workflow into a use case

### Anti-pattern: transport leakage into domain

Fix:
- map transport models in `registry/` before values reach domain or application

### Anti-pattern: all server calls under discovery

Fix:
- keep `discovery/` focused on discovery behavior
- keep raw server communication in `registry/`
