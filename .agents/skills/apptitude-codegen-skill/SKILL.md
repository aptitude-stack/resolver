---
name: apptitude-codegen
description: Code generation rules and architectural constraints for the Aptitude Client repository.
origin: Aptitude
---

# Aptitude Client Code Generation Skill

This skill defines how code must be generated inside the **Aptitude Client repository**.

It ensures that all generated code respects the project's architecture, module boundaries, and development standards.

This skill should be activated automatically whenever an agent writes, modifies, or reviews code in this repository.

---

# When to Activate

Activate this skill when:

- Writing new Python modules
- Implementing a new feature
- Creating application use cases
- Adding DTO models
- Implementing discovery logic
- Implementing resolver logic
- Writing CLI commands
- Writing tests
- Refactoring existing modules

---

# Core Architecture Principles

The Aptitude Client follows a **layered architecture**.

Each layer has strict responsibilities and dependency rules.

Allowed dependency direction:

- interfaces -> application
- application -> domain
- application -> discovery
- application -> resolver
- application -> shared
- discovery -> domain
- discovery -> shared
- resolver -> domain
- resolver -> shared

Forbidden dependency direction:

domain -> application
domain -> interfaces
resolver -> interfaces
discovery -> interfaces
shared -> application
shared -> discovery
shared -> resolver

Never introduce circular dependencies.

---

# Module Responsibilities

## domain

The **domain layer** contains the core business logic.

Allowed content:

- Entities
- Value objects
- Domain policies
- Domain validation
- Domain errors

Forbidden content:

- HTTP calls
- CLI logic
- Registry communication
- Filesystem access
- Logging configuration

The domain must remain pure and infrastructure-independent.

---

## application

The **application layer** orchestrates use cases.

Responsibilities:

- Use case implementations
- Workflow coordination
- Mapping between DTOs and domain objects
- Calling discovery and resolver services

Application code should contain **no infrastructure logic**.

---

## interfaces

The **interfaces layer** exposes the system to the outside world.

Examples:

- CLI commands
- MCP interface
- SDK entrypoints

Responsibilities:

- Input parsing
- Input validation
- Calling application use cases
- Formatting output

Interfaces must not contain business logic.

---

## discovery

The **discovery module** is responsible for identifying potential skills.

Responsibilities:

- Searching the registry
- Interpreting user intent
- Ranking candidate skills
- Returning possible matches

Discovery **does not perform dependency solving**.

---

## resolver

The **resolver module** is responsible for dependency solving.

Responsibilities:

- Dependency resolution
- Version solving
- Conflict detection
- Lockfile generation
- Validation of dependency graphs

Resolver logic must be deterministic.

---

## shared

The **shared module** contains reusable utilities.

Examples:

- Logging configuration
- Configuration loading
- Common helpers
- Shared constants

Shared code must remain lightweight, dependency-safe, and infrastructure-like.
Other layers may depend on `shared`, but `shared` must not depend on feature
layers or contain feature-owned business logic.

---

# Code Generation Rules

When implementing new functionality, follow this order:

1. Define domain models if needed
2. Implement application use case
3. Connect discovery or resolver logic
4. Expose functionality through interfaces
5. Write tests

Always keep modules small and focused.

Prefer composition over inheritance.

---

# DTO Rules

Use **Pydantic models** for external data structures.

Use Pydantic for:

- API responses
- CLI inputs
- Registry responses
- Manifest structures

Example:

from pydantic import BaseModel

class SkillInfo(BaseModel):
    name: str
    version: str
    description: str

Domain models should remain independent of Pydantic where possible.

---

# Logging Rules

Use the shared logging system.

Never use `print()` for logging.

Example:

logger.info("Resolving skill dependencies")

Log important events such as:

- skill discovery
- dependency resolution
- installation planning
- validation failures

---

# Testing Rules

All new functionality must include tests.

Test location:

tests/unit
tests/integration

Testing requirements:

- Use pytest
- Follow TDD (Red → Green → Refactor)
- Target coverage: 80% or higher
- Critical paths must have 100% coverage

---

# Error Handling

Use explicit domain errors.

Examples:

- SkillNotFoundError
- VersionConflictError
- RegistryUnavailableError
- InvalidManifestError

Do not return raw exceptions to interfaces.

Errors should be structured and explainable.

---

# Performance Guidelines

Prefer deterministic algorithms.

Avoid unnecessary network calls.

Cache registry responses when appropriate.

Dependency resolution must remain predictable.

---

# What NOT to Do

Do not:

- Introduce new architectural layers
- Add modules not defined in the architecture
- Create circular dependencies
- Put business logic in CLI modules
- Access the registry directly from domain
- Use print statements instead of logging

---

# Goal of This Skill

This skill ensures that all generated code:

- respects the Aptitude architecture
- remains maintainable
- stays deterministic
- follows consistent design patterns
- integrates cleanly with discovery and resolver systems
