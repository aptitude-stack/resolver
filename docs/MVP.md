# MVP

This document defines the initial MVP scope for the Aptitude Client.

It is intentionally narrow in capability, but it should still be built on the
real product architecture rather than on a temporary boundary we expect to undo.

This document is a product and implementation scope definition, not an execution plan.

Detailed step-by-step execution should still be written under `.agents/plans/`
when implementation work begins.

## 1. MVP Goal

Build the first end-to-end client flow that can:

1. accept a skill request from the CLI
2. fetch exact immutable metadata from the server
3. fetch direct immutable dependencies from the server
4. shape a minimal deterministic resolution result
5. print the result to the CLI as stable JSON

This MVP should prove the first executable client pipeline:

`CLI -> application -> registry -> resolver -> output`

## 2. Architectural Rule For The MVP

The MVP is small in features, not small in architecture.

That means:

- all Aptitude Server communication belongs in `registry/`
- `discovery/` is reserved for discovery-specific logic only
- the CLI still goes through the application layer
- the resolver remains the owner of deterministic result shaping

## 3. In Scope

The MVP includes only the following responsibilities.

### CLI Input

Use `interfaces/cli` to accept this first hard-cut command shape:

`aptitude resolve <slug> --version <version>`

The client now also supports a narrow discovery-backed query shape:

`aptitude resolve "<name query>" --version <version>`

The broader name-only UX without `--version` remains a later milestone until
the server exposes version lookup for discovery.

### Registry Reads

Use `registry/` to call the runtime-tested repository API and fetch:

- exact immutable metadata
- direct immutable dependencies

For the initial hard cut, discovery was excluded. The current implementation
now allows `POST /discovery` only for query-to-slug selection when the user
still supplies `--version`.

### Domain Modeling

Define only the minimum domain models needed for the first slice.

Initial recommended domain objects:

- `SkillCoordinate`
- `SkillMetadata`
- `DependencySpec`
- `ResolutionResult` or equivalent result shape

### Application Layer

Use `application/use_cases` to orchestrate the flow.

The MVP should contain one main use case such as:

- `resolve_exact_skill`
- or `plan_exact_skill_read`

This use case should coordinate:

- input handling
- exact metadata fetch
- direct dependency fetch
- result shaping

### Resolver

Use `resolver/solver` to implement a minimal deterministic resolver.

For the first MVP slice, the resolver should support only:

- exact coordinate shaping
- dependency order preservation
- deterministic output assembly

No full graph solving is required in the first version.

### Output

The MVP should produce a stable output that can later evolve into a lockfile or execution plan.

Initial output may be:

- requested coordinate
- selected coordinate
- minimal skill metadata summary
- direct dependencies
- status

Example:

```json
{
  "requested_coordinate": {
    "slug": "pdf.extract",
    "version": "1.2.0"
  },
  "selected_coordinate": {
    "slug": "pdf.extract",
    "version": "1.2.0"
  },
  "dependencies": [
    {
      "slug": "filesystem.read",
      "version": "1.3.1"
    }
  ],
  "status": "resolved"
}
```

## 4. Explicitly Out of Scope

The following are not part of the initial MVP.

- name-only discovery without `--version`
- semantic intent interpretation
- candidate ranking across multiple matches
- version choice across multiple candidate versions
- policy engine
- conflict governance
- deep dependency graph solving
- caching strategy beyond simple placeholders
- environment profiles
- execution runtime
- artifact installation
- provenance and audit features
- authentication and token governance
- advanced lockfile format finalization

These may be added later, but they should not block the first vertical slice.

## 5. Modules Allowed in This MVP

Allowed modules:

- `application/dto`
- `application/use_cases`
- `discovery/intent`
- `domain/errors`
- `domain/models`
- `interfaces/cli`
- `registry`
- `resolver/solver`
- `shared/config`
- `shared/logging`

Do not introduce speculative packages unrelated to the current executable slice.

## 6. MVP Decisions

### Interface Style

The MVP is CLI-first.

Rationale:
- the CLI module already exists
- it provides the fastest way to validate the end-to-end flow
- it avoids premature expansion into MCP or SDK interfaces

### Execution Style

The MVP is sync-first unless a specific API client constraint requires async.

Rationale:
- simpler implementation
- easier debugging
- easier deterministic testing
- better fit for the first slice

### Server Boundary Style

The MVP uses a dedicated registry adapter.

Rationale:
- exact metadata and dependency reads are not discovery logic
- the same boundary will later host discovery, publish, and lifecycle clients
- this preserves the real product architecture from the start

### Resolver Style

The MVP resolver is minimal and deterministic.

Rationale:
- prove the pipeline first
- avoid full dependency solver complexity too early

## 7. Suggested First Vertical Slice

Input:

`aptitude resolve <slug> --version <version>`

Flow:

1. CLI parses the request
2. application use case is invoked
3. registry returns exact metadata
4. registry returns direct dependencies
5. resolver shapes one deterministic result
6. CLI prints the result

Success criteria:

- one command works end to end
- result is deterministic
- basic tests exist
- logging exists
- architecture boundaries are respected

## 8. Validation Criteria

The MVP is complete when all of the following are true:

- a CLI command can request a skill by exact coordinate
- the client can call the repository API through `registry/`
- the response is mapped into internal models
- the resolver produces a deterministic output
- the CLI prints a stable result
- unit tests exist for core logic
- integration tests exist for the API flow
- implementation respects the real product boundary between discovery and registry

## 9. Relationship to Planning

This file defines what the MVP is.

It does not replace planning.

When actual implementation starts, the agent must still create or update plan
files under `.agents/plans/`.

So there is no contradiction:

- `docs/MVP.md` = scope and product boundary
- `.agents/plans/*.md` = execution plan for implementing that scope

## 10. Discovery Follow-Up

The broader product target still includes a name-driven flow such as:

`aptitude resolve pdf.extract`

The client now supports a narrower intermediate step:

`aptitude resolve "pdf extract" --version 1.2.0`

However, the full name-only flow is still deferred until the server discovery
contract is aligned with a version lookup route.

Before that expansion happens, the project must resolve:

- whether discovery remains body-based or query-based
- whether discovery returns slug strings only or richer candidate objects
- how the client derives an exact version after discovery
- what deterministic tie-break rule applies when multiple candidates or versions exist

Until then, exact coordinates remain the source of truth for the first executable slice.
