---
name: aptitude-client-builder
description: Build the Aptitude client as a modular Python system using Typer, Pydantic, resolvelib, networkx, pluggy, and httpx. Use when implementing step-by-step client architecture and production-oriented module boundaries.
---
# Aptitude Client Builder

## Purpose
Build the Aptitude client step by step as a modular Python system for managing AI skills.

## Project Context
Aptitude is a package-manager-like system for AI skills.
It is conceptually inspired by pip, npm, and Maven.
Skills are versioned artifacts with metadata, dependencies, runtime compatibility, security attributes, and popularity metrics.

## Architecture Rules
- Use Python.
- Use Typer for CLI.
- Use Pydantic for models and validation.
- Use httpx for HTTP communication.
- Use resolvelib for version/dependency resolution.
- Use networkx for dependency graph construction and analysis.
- Use pluggy for plugin hooks.
- Keep CLI thin.
- Put business logic in services/core modules.
- Keep models explicit and versionable.
- Build in small, testable increments.

## Preferred Project Structure
aptitude_client/
  cli/
  core/
    resolver/
    registry/
    installer/
    graph/
  models/
  plugins/
  cache/
  utils/

## Workflow
When invoked:
1. Understand the requested step only.
2. Identify which modules are affected.
3. Implement the minimal complete solution for that step.
4. Keep code modular and production-oriented.
5. Do not implement future steps unless explicitly requested.
6. Return:
   - files created/modified
   - short explanation
   - next recommended step

## Definition of Done
A step is done only if:
- code is consistent with the architecture
- naming is clear
- no logic is misplaced in CLI
- models are validated
- imports are clean
- the step is runnable or structurally complete