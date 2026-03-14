# MVP.md

This document defines the **initial MVP scope** for the Aptitude Client.

It is intentionally narrow.

The goal of this MVP is **not** to implement the full target architecture described in the repository documents.
The goal is to deliver the **first working vertical slice** using only the modules that already exist under `src/aptitude_client/`.

This document is a **product and implementation scope definition**, not an execution plan.

Detailed step-by-step execution should still be written under `.agents/plans/` when implementation work begins.

---

# 1. MVP Goal

Build the first end-to-end client flow that can:

1. accept a skill request from the CLI
2. query the repository API for matching skill candidates
3. map the response into internal DTO/domain models
4. run a minimal deterministic resolution flow
5. produce a simple execution-oriented result
6. print the result to the CLI

This MVP should prove the basic client pipeline:

`CLI -> discovery -> registry_api -> domain/application mapping -> resolver -> output`

---

# 2. In Scope

The MVP includes only the following responsibilities.

## CLI Input

Use the existing `interfaces/cli` module to accept a simple user request such as:

- skill name
- optional version constraint

Example:

`aptitude install pdf.extract`

or

`aptitude resolve pdf.extract`

The exact command naming may still be refined, but the MVP should remain CLI-first.

---

## Discovery

Use the existing `discovery/registry_api` module to call the repository API and fetch candidate skills.

Use the existing `discovery/intent` module only for a **minimal interpretation step** if needed.
For the MVP, direct skill-name lookup is enough.

No advanced ranking is required in the first slice.

---

## Domain Modeling

Define only the minimum domain models needed for the first slice.

Initial recommended domain objects:

- `SkillManifest`
- `DependencySpec`
- `ResolutionResult`
- `ExecutionPlan`
- `Lockfile` (optional in MVP Step 2, not mandatory in Step 1)

Use `docs/DOMAIN_SCHEMAS.md` as the schema source of truth.

---

## Application Layer

Use `application/use_cases` to orchestrate the flow.

The MVP should contain one main use case such as:

- `resolve_skill_request`
- or `plan_skill_installation`

This use case should coordinate:

- input handling
- discovery
- mapping
- resolution
- output shaping

---

## Resolver

Use the existing `resolver/solver` module to implement a **minimal deterministic resolver**.

For the first MVP slice, the resolver may support only:

- exact version selection when one candidate exists
- deterministic selection of one candidate when multiple results are returned
- minimal dependency expansion for direct dependencies only

No full graph solving is required in the first version.

---

## Output

The MVP should produce a stable output that can later evolve into a lockfile or execution plan.

Initial output may be:

- selected skill
- selected version
- direct dependencies
- simple explanation of the resolution result

Example:

```json
{
  "requested_skill": "pdf.extract",
  "selected_version": "1.2.0",
  "dependencies": [
    {
      "skill": "filesystem.read",
      "version": "1.3.1"
    }
  ],
  "status": "resolved"
}
```

---

# 3. Explicitly Out of Scope

The following are **not** part of the initial MVP.

- MCP-first workflow
- plugin system
- advanced ranking or semantic intent interpretation
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

---

# 4. Modules Allowed in This MVP

Implementation must stay within the modules that already exist in `src/aptitude_client/`.

Allowed modules:

- `application/dto`
- `application/use_cases`
- `discovery/intent`
- `discovery/registry_api`
- `domain/errors`
- `domain/models`
- `interfaces/cli`
- `resolver/solver`
- `shared/config`
- `shared/logging`

Do **not** introduce new top-level packages for the MVP.

Do **not** implement future architecture modules that do not yet exist in the repository.

---

# 5. MVP Decisions

## Interface Style

The MVP is **CLI-first**.

Rationale:
- the CLI module already exists
- it provides the fastest way to validate the end-to-end flow
- it avoids premature expansion into MCP or SDK interfaces

## Execution Style

The MVP is **sync-first** unless a specific API client constraint requires async.

Rationale:
- simpler implementation
- easier debugging
- easier deterministic testing
- better fit for the first slice

## Discovery Style

The MVP uses **direct repository API lookup** rather than advanced intent ranking.

Rationale:
- simpler
- sufficient for the first vertical slice
- easier to test

## Resolver Style

The MVP resolver is **minimal and deterministic**.

Rationale:
- prove the pipeline first
- avoid full dependency solver complexity too early

---

# 6. Suggested First Vertical Slice

The recommended first implemented flow is:

## `resolve skill by exact name`

Input:

`aptitude resolve pdf.extract`

Flow:

1. CLI parses the request
2. application use case is invoked
3. registry API returns candidate manifests
4. domain models are created
5. resolver selects one deterministic result
6. CLI prints the result

Success criteria:

- one command works end-to-end
- result is deterministic
- basic tests exist
- logging exists
- architecture boundaries are respected

---

# 7. Suggested MVP Phases

## Phase 1

- implement repository API client shape
- implement basic DTOs
- implement minimal domain models
- implement CLI command
- return one resolved result

## Phase 2

- add direct dependency expansion
- add `ResolutionResult`
- add simple explanation output

## Phase 3

- add minimal `ExecutionPlan` output
- optionally introduce initial lockfile shaping

---

# 8. Validation Criteria

The MVP is complete when all of the following are true:

- a CLI command can request a skill by name
- the client can call the repository API
- the response is mapped into internal models
- the resolver produces a deterministic output
- the CLI prints a stable result
- unit tests exist for core logic
- integration tests exist for the API flow or mocked equivalent
- implementation stays inside existing modules only

---

# 9. Relationship to Planning

This file defines **what the MVP is**.

It does **not** replace planning.

When actual implementation starts, the agent must still create a plan file under:

`.agents/plans/`

Example:

`01-cli-first-mvp-resolve-flow.md`

Use the plan file to define:

- implementation steps
- milestones
- risks
- progress

So there is no contradiction:

- `docs/MVP.md` = scope and product boundary
- `.agents/plans/*.md` = execution plan for implementing that scope

---

# 10. Current Recommendation

Use this MVP as the source of truth for the first Aptitude Client implementation slice.

Do not expand beyond this scope until the first vertical flow works end-to-end.
