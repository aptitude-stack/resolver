---
name: aptitude-codegen
description: Code generation rules and architectural constraints for the Aptitude Resolver repository.
origin: Aptitude
---

# Aptitude Resolver Code Generation Skill

Use this skill whenever code, tests, or architecture-facing docs change in this repository.

Before any non-trivial implementation:

1. read `docs/architecture/system-overview.md`
2. read `docs/architecture/decision-rules.md`
3. identify the owning module before editing code

If the intended work changes the architecture or module boundaries, update the canonical architecture docs first or in the same change. Do not silently drift from them.

## Core Architecture Principles

The Aptitude Resolver uses a layered architecture with one explicit server boundary.

The server owns facts.
The resolver owns decisions.

### Current architectural direction

- interfaces stay thin
- application orchestrates
- discovery interprets and reranks
- registry owns transport
- resolver owns deterministic solving
- governance runs before locking
- lockfile is the durable resolved artifact
- execution consumes lock data only

## Allowed Dependency Direction

- `interfaces -> application`
- `application -> domain | discovery | execution | governance | lockfile | registry | resolver | shared`
- `discovery -> domain | shared`
- `governance -> domain`
- `lockfile -> domain`
- `execution -> domain | lockfile`
- `registry -> domain | shared`
- `resolver -> domain | shared`

Do not introduce circular dependencies.

## Module Responsibilities

### domain

Owns:

- entities
- value objects
- deterministic rule concepts
- policy types
- tracing models
- resolver-owned errors

Must not own:

- HTTP calls
- CLI logic
- filesystem orchestration

### application

Owns:

- use-case orchestration
- workflow sequencing
- DTO boundaries
- coordination across discovery, resolver, governance, lockfile, and execution

Must not own:

- solver internals
- raw HTTP details
- CLI formatting

### interfaces

Owns:

- input parsing
- calling use cases
- interactive prompting
- output formatting
- exit codes

Must not own business logic.

### discovery

Owns:

- intent interpretation
- discovery query construction
- candidate shaping
- non-final reranking

Must not own:

- final candidate selection
- dependency solving
- lock generation

### registry

Owns:

- all Aptitude Server communication
- auth header injection
- endpoint knowledge
- request and response parsing
- transport error translation
- transport-to-domain mapping

### resolver

Owns:

- version selection
- final candidate selection
- dependency normalization
- dependency expansion
- graph building
- conflict handling
- validation

Resolver logic must be deterministic and explainable.

### governance

Owns:

- policy evaluation before lock generation

### lockfile

Owns:

- lock schema
- deterministic serialization
- parse and replay

### execution

Owns:

- execution-plan generation from lock data
- artifact fetching
- checksum verification
- environment preparation
- materialization

Execution must not depend on `ResolutionGraph`.

### shared

Owns generic support code only:

- config
- logging
- small reusable helpers

## DTO Rules

Use Pydantic where validation and serialization clarity matter:

- application DTOs
- registry transport models
- typed config objects

Keep domain models independent of Pydantic where possible.

## Testing Rules

All new behavior should include tests.

Focus on:

- happy path
- failure path
- determinism when ordering or selection matters
- registry boundary verification against the live server when practical

## Documentation Rules

When behavior or boundaries change, update the canonical docs in the same change:

- `docs/architecture/system-overview.md`
- `docs/architecture/decision-rules.md`

Update supporting docs when needed:

- `README.md`
- `docs/README.md`
- `.agents/agent.md`
- `.agents/memory/meta.md`
- `.agents/rules/repo.md`

## What Not To Do

Do not:

- put business logic in CLI handlers
- let discovery perform final selection
- let execution re-resolve dependencies
- let application become the solver
- treat server ordering as authoritative client choice
- hide feature logic in `shared/`
