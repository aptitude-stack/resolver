# Aptitude Client Architecture

## Status

This is the canonical architecture source of truth for `aptitude-client`.

Before any non-trivial change, feature, refactor, or new module:

1. read this file
2. read [RULES.md](RULES.md)
3. identify the owning module before writing code

If the intended implementation changes the architecture, boundaries, or flow, update this file first or in the same change. Do not silently drift from it.

## System Overview

Aptitude is a client-side dependency and capability manager for AI skills.

The system is split into:

- **Server**: owns data-local work such as registry storage, immutable metadata, immutable artifacts, and indexed candidate retrieval
- **Client**: owns decision-local work such as intent interpretation, candidate selection, dependency solving, governance, locking, and execution planning

The server returns facts.
The client makes decisions.

## Core Architectural Law

Always enforce:

- Server = data-local work
- Client = decision-local work

The client must own:

- interpret user intent
- discover candidates
- choose versions
- select the final root
- resolve dependencies
- enforce governance
- generate a lock
- build the execution plan

The client must not:

- delegate final selection to the server
- delegate dependency solving to the server
- treat server ordering or advisory ranking as final truth
- execute from unlocked graph state once a lock exists

## Canonical Pipelines

### 1. Fresh Planning Flow

Use this when the input is a user request or query.

```text
User Request
-> Interface
-> Application Use Case
-> Discovery
-> Resolver
-> Governance
-> Lockfile
-> Execution Planning
-> Result or Materialization
```

This is the architecture behind:

- `install`
- hidden `resolve`

### 2. Lock Replay Flow

Use this when the input is an existing lockfile.

```text
Lockfile
-> Interface
-> Application Use Case
-> Lock Parse + Replay
-> Execution Planning
-> Materialization
```

This is the architecture behind:

- `sync --lock`

This is not a pipeline violation. It is the correct replay path once a lock already exists.

## Hard Constraints

Every implementation must preserve:

- deterministic behavior for identical logical inputs
- traceable decision-making
- strict module boundaries
- governance before lock generation in fresh planning flows
- lock as the single source of truth for execution

If a proposed change violates one of these, the design is wrong until proven otherwise.

## Current Package Map

```text
src/aptitude_client/
  application/
    commands/
    dto/
    queries/
    use_cases/
  discovery/
    intent/
    query_builder/
    reranking/
  domain/
    errors/
    models/
    policy/
    tracing/
  execution/
  governance/
  interfaces/
    cli/
  lockfile/
  registry/
  resolver/
    conflict/
    graph/
    normalizer/
    replay/
    solver/
    validation/
  shared/
    config/
    logging/
```

Reserved but not yet implemented as top-level packages:

- `plugins/`
- `cache/`
- `telemetry/`
- additional interfaces such as `mcp/` and `sdk/`

These should be added only when they become real responsibilities.

## Dependency Direction

Allowed architectural direction:

- `interfaces -> application`
- `application -> domain | discovery | execution | governance | lockfile | registry | resolver | shared`
- `discovery -> domain | shared`
- `governance -> domain`
- `lockfile -> domain`
- `execution -> domain | lockfile`
- `registry -> domain | shared`
- `resolver -> domain | shared`

Important note:

- lower layers may depend on protocols or inputs supplied by application
- they must not import interface code or bypass the intended workflow

Forbidden:

- `domain -> application | discovery | execution | governance | interfaces | lockfile | registry | resolver`
- `interfaces -> discovery` for business-logic bypass
- `interfaces -> execution` for business-logic bypass
- `interfaces -> governance` for business-logic bypass
- `interfaces -> lockfile` for business-logic bypass
- `interfaces -> registry` for business-logic bypass
- `interfaces -> resolver` for business-logic bypass
- `shared -> application | discovery | execution | governance | lockfile | registry | resolver`

## Module Responsibilities

### interfaces/

Owns:

- external entrypoints
- input parsing
- interactive prompting
- output formatting
- exit behavior

Must not own:

- business rules
- final selection
- dependency solving
- governance logic
- registry transport

### application/

Owns:

- use-case orchestration
- workflow sequencing
- DTO boundaries
- handoff between discovery, resolver, governance, lockfile, and execution

Must not own:

- solver internals
- discovery internals
- raw transport details
- CLI formatting
- execution internals

### discovery/

Owns:

- request-intent interpretation
- discovery query construction
- candidate identity shaping
- non-final reranking

Must not own:

- final candidate selection
- dependency solving
- lock generation
- execution planning

### registry/

Owns:

- all Aptitude Server communication
- auth headers
- endpoint knowledge
- transport parsing
- transport error translation
- transport-to-domain mapping

Must not own:

- prompt interpretation
- client reranking policy
- dependency solving
- lock generation

### resolver/

Owns:

- candidate version selection
- final candidate selection
- dependency normalization
- dependency expansion
- graph construction
- conflict detection
- validation

Resolver behavior must be deterministic and explainable.

### governance/

Owns:

- policy evaluation before lock generation
- blocking invalid resolved systems

Current implementation:

- lifecycle policy checks

Planned expansion:

- trust validation
- organization-specific rules
- cost constraints

### lockfile/

Owns:

- lock schema
- deterministic serialization
- parsing
- replay validation

The lockfile is the execution source of truth.

### execution/

Owns:

- execution-plan construction from lock data
- artifact fetch planning
- checksum verification
- environment preparation
- materialization
- execution-owned debug artifacts

Execution must not depend on `ResolutionGraph`.

### domain/

Owns:

- entities
- value objects
- client-owned errors
- policy types
- tracing models

Must remain free of transport and CLI concerns.

### shared/

Owns:

- configuration loading
- logging setup
- generic low-business-meaning helpers

Must not hide feature-owned logic.

## Current Implemented User Surfaces

Public CLI:

- `install`
- `sync`

Hidden internal CLI:

- `resolve`

Normal user flow:

- `install`
- `sync --lock`

`resolve` is intentionally a preview/debug surface, not the public default flow.

## Architecture Change Protocol

Before adding a new capability, ask:

1. Which module owns it?
2. Does it belong to the fresh planning flow or the lock replay flow?
3. Does it affect determinism, traceability, or execution truth?
4. Does this file need to change first?

If the answer to `4` is yes, update this file in the same change. Do not leave architecture drift behind for "later".

## Decision Gate

Before considering a design acceptable, verify:

- Is the logic in the correct layer?
- Does the client still own the decision?
- Is the result deterministic?
- Is the decision traceable?
- Does execution still run from lock data only?

If any answer is no, the design is not complete.
