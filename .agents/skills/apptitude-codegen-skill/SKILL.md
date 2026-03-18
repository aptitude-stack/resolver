---
name: apptitude-codegen
description: Code generation rules and architectural constraints for the Aptitude Client repository.
origin: Aptitude
---

# Aptitude Client Code Generation Skill

This skill defines how code must be generated inside the Aptitude Client repository.

Use it whenever code, tests, or architecture-facing docs are changed in this repo.

## Core Architecture Principles

The Aptitude Client follows a layered architecture with one explicit server boundary.

Allowed dependency direction:

- interfaces -> application
- application -> domain | discovery | registry | resolver | shared
- discovery -> registry | domain | shared
- registry -> domain | shared
- resolver -> domain | shared

Forbidden dependency direction:

- domain -> application | discovery | registry | resolver | interfaces
- interfaces -> discovery for business-logic bypass
- interfaces -> registry for business-logic bypass
- resolver -> interfaces
- discovery -> interfaces
- registry -> interfaces
- shared -> application | discovery | registry | resolver

Never introduce circular dependencies.

## Module Responsibilities

### domain

The domain layer contains core business concepts, invariants, and client-owned errors.

Allowed content:
- entities
- value objects
- domain validation
- deterministic rules
- domain errors

Forbidden content:
- HTTP calls
- CLI logic
- registry transport payloads
- filesystem orchestration
- logging bootstrap

### application

The application layer orchestrates use cases.

Responsibilities:
- use case implementations
- workflow coordination
- mapping between DTOs and domain objects
- calling discovery, registry, and resolver services
- shaping user-facing outcomes for interfaces

Application code must not contain raw transport details or CLI formatting.

### interfaces

The interfaces layer exposes the system to the outside world.

Examples:
- CLI commands
- MCP entrypoints
- SDK entrypoints

Responsibilities:
- input parsing
- input validation
- calling application use cases
- formatting output
- setting process exit codes

Interfaces must not contain business logic.

### discovery

The discovery module owns discovery-specific client logic.

Responsibilities:
- interpreting user intent
- building discovery queries
- shaping or reranking candidates
- orchestrating discovery-specific flows through registry clients

Discovery does not own generic server transport, exact metadata fetches, or dependency solving.

### registry

The registry module is the anti-corruption layer to Aptitude Server.

Responsibilities:
- HTTP transport
- auth header injection
- endpoint path knowledge
- request and response parsing
- transport error translation
- mapping server payloads into client-owned models

All Aptitude Server communication belongs here.

### resolver

The resolver module owns deterministic dependency and selection logic.

Responsibilities:
- dependency normalization
- version solving
- dependency graph shaping
- conflict detection
- validation of resolved outcomes
- lock-oriented result shaping over time

Resolver logic must be deterministic.

### shared

The shared module contains cross-cutting support code.

Examples:
- logging configuration
- configuration loading
- shared constants
- generic helpers with low business meaning

Shared code must not depend on feature layers or hide feature-owned logic.

## Code Generation Rules

When implementing new functionality, follow this order where it fits the task:

1. Define or refine domain models if needed
2. Implement or refine the application use case
3. Add registry or discovery support
4. Add resolver behavior if needed
5. Expose functionality through interfaces
6. Add or update tests

Prefer small, explicit modules over broad abstractions.

## DTO Rules

Use Pydantic models for external and application-boundary structures.

Use Pydantic for:
- application DTOs
- registry transport models
- CLI-facing output models when serialization clarity matters
- configuration objects

Keep domain models independent of Pydantic where possible.

## Logging Rules

Use the shared logging system.

Never use `print()` for logging.

Log important workflow events such as:
- registry reads
- discovery requests
- dependency resolution steps
- validation failures

Never log tokens or other secrets.

## Testing Rules

All new functionality must include tests.

Test locations:
- tests/unit
- tests/integration

Testing expectations:
- use pytest
- follow TDD where the change is non-trivial
- add happy-path and failure-path coverage
- keep deterministic behavior under test where ordering matters
- verify the registry boundary with live integration tests against a running server when practical
- do not treat mocked-HTTP contract tests as the primary proof of registry behavior in this repo

## Error Handling

Use explicit client-owned errors.

Examples:
- SkillNotFoundError
- InvalidCoordinateError
- RegistryUnavailableError
- RegistryAccessError
- VersionConflictError

Do not leak raw library exceptions to interfaces.

## What Not To Do

Do not:
- create circular dependencies
- put business logic in CLI modules
- let domain import registry transport code
- move all server communication into discovery
- introduce speculative top-level packages without a real responsibility
- use print statements instead of logging

The dedicated registry boundary is approved and should be used for Aptitude Server communication.
