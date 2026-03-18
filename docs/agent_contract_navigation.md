# Agent Contract and Navigation Guide

This document defines how agents should operate inside the Aptitude repository.

It serves two purposes:

1. define the operational contract for agents
2. provide a navigation guide for understanding the repository

Agents should read this file before performing any task in the repository.

## Project Mission

Aptitude is a governed AI capability ecosystem.

The Aptitude Client is responsible for:

- interpreting user intent
- discovering skills
- resolving dependencies
- generating lockfiles
- planning execution

The server provides registry services, metadata, and discovery support.

The client is responsible for deterministic resolution and execution planning.

## Current Repository Reality

This repository currently contains the Aptitude Client foundation plus the first
real server boundary implementation, not a finished client.

Current implementation reality:

- the project is Python-based
- package boundaries exist under `src/aptitude_client/`
- shared config, shared logging, and base client errors are implemented
- a registry adapter exists under `src/aptitude_client/registry/`
- the CLI supports exact `slug + --version` resolution
- the CLI also supports discovery-backed name queries when `--version` is supplied
- live integration tests exist for the registry adapter under `tests/integration/registry/`
- the client still does not have server-driven version lookup for discovery, so name-only queries without `--version` remain unresolved by design
- `pyproject.toml` should be treated as the source of truth for active dependencies and pytest markers

Agents must distinguish between:

- current repository reality: what actually exists in the filesystem
- target architecture: what the architecture documents describe as the intended direction

Do not assume a module, interface, endpoint, workflow, or dependency already
exists unless it is present in the repository or explicitly requested.

## Source of Truth Documents

Agents should use the following documents as primary references:

- `docs/scope.md`
- `docs/Aptitude Client Architecture.md`
- `docs/Module-Responsibilities.md`
- `docs/Coding-Standards.md`
- `docs/Aptitude-Recommended-Libraries.md`
- `.agents/rules/repo.md`

These documents define the intended architecture and repository rules.

## Repository Navigation by Task

Agents should not read all documentation blindly.

Instead, follow the navigation rules based on the task.

### Implementing New Code

Steps:

1. read the architecture and package-responsibility documents
2. activate the code generation skill
3. follow repository rules
4. verify the current repository structure before creating new modules
5. implement using the current layered architecture

Relevant files:

- `docs/Aptitude Client Architecture.md`
- `docs/Module-Responsibilities.md`
- `docs/Coding-Standards.md`
- `.agents/skills/apptitude-codegen-skill/SKILL.md`
- `.agents/rules/repo.md`

### Writing Tests

Steps:

1. activate the python testing skill
2. follow TDD workflow where the change is non-trivial
3. keep tests aligned with current repository reality, not future diagrams
4. prefer live integration tests for the registry boundary when practical

Relevant files:

- `docs/Coding-Standards.md`
- `.agents/skills/python-testing/SKILL.md`

### Reviewing Code

Steps:

1. read the scope and architecture docs that define the intended boundaries
2. use architectural review guidance when the change has architectural impact
3. verify architecture boundaries
4. verify test coverage
5. verify documentation discipline

Relevant files:

- `docs/scope.md`
- `docs/Aptitude Client Architecture.md`
- `docs/Module-Responsibilities.md`
- `docs/Coding-Standards.md`
- `.agents/skills/architect-review/SKILL.md`

### Architecture Work

Steps:

1. read scope
2. read the architecture document
3. verify current repo structure
4. separate target-state guidance from implemented-state facts

Relevant files:

- `docs/scope.md`
- `docs/Aptitude Client Architecture.md`
- `docs/Module-Responsibilities.md`
- `docs/Coding-Standards.md`

## Skills Available to Agents

The following skills may be activated depending on the task:

- `apptitude-codegen`
- `architect-review`
- `python-patterns`
- `python-testing`
- `using-superpowers`
- `writing-plans`
- `executing-plans`
- `systematic-debugging`
- `verification-before-completion`

Skills define procedural guidance for agents performing tasks.

## Core Invariants

Agents must respect the following invariants.

### Layered Architecture

Allowed dependency direction:

- `interfaces -> application`
- `application -> domain | discovery | registry | resolver | shared`
- `discovery -> registry | domain | shared`
- `registry -> domain | shared`
- `resolver -> domain | shared`

Forbidden:

- `domain -> application | discovery | registry | resolver | interfaces`
- `resolver -> interfaces`
- `interfaces -> resolver` for business-logic bypass
- `interfaces -> discovery` for business-logic bypass
- `interfaces -> registry` for business-logic bypass
- `shared -> application | discovery | registry | resolver`

### Deterministic Behavior

The Aptitude client must behave deterministically.

Dependency resolution must produce consistent results for the same inputs.

### Documentation Discipline

When architecture or stable repository facts change:

- update architecture documents when behavior or boundaries change
- update repository rules when workflow expectations change
- update agent-facing docs when skills, paths, or current repo facts change

Documentation must reflect repository reality.

## Current Repository vs Target Architecture

The architecture documentation may describe a target state.

Agents must verify the current repository structure before implementing new modules.

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

Treat folders that appear only in architecture diagrams as design intent, not
implemented fact.

## Implementation Workflow

When implementing features, follow this workflow:

1. define or refine domain models if needed
2. implement application use case
3. integrate registry, discovery, or resolver logic as appropriate
4. expose functionality through interfaces
5. add tests

Prefer small focused modules.

Avoid unnecessary abstraction.

## Error Handling

Use structured domain or client-owned errors.

Examples:

- `SkillNotFoundError`
- `VersionConflictError`
- `RegistryUnavailableError`
- `InvalidManifestError`

Errors must be explainable and deterministic.

## Logging

Use the shared logging infrastructure when it exists for the workflow you are
touching.

Do not use print statements as application logging.

Log:

- registry operations
- discovery operations
- dependency resolution
- validation errors
- execution planning

## Goal of This Contract

Ensure that all agent activity in the repository:

- respects the architecture
- maintains deterministic behavior
- follows repository rules
- keeps documentation consistent
- distinguishes clearly between current state and target state
