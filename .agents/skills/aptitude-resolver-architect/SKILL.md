---
name: aptitude-resolver-architect
description: Architect Aptitude dependency resolution and graph planning with resolvelib and networkx. Use when implementing version constraint solving, cycle/conflict detection, and explainable install-order planning.
---
# Aptitude Resolver Architect

## Purpose
Design and implement the dependency resolution and graph planning logic for the Aptitude client.

## Responsibilities
- Resolve skill dependencies with version constraints.
- Build a directed dependency graph.
- Detect cycles and conflicts.
- Produce an execution/install order.
- Keep resolution logic separate from download/install logic.

## Technical Rules
- Use resolvelib for dependency/version solving where appropriate.
- Use networkx for directed graph creation, traversal, cycle detection, and topological sorting.
- Keep registry access abstracted behind a provider/repository interface.
- Do not mix HTTP calls directly into graph logic.
- Resolution output must be explainable.

## Required Outputs
When implementing resolver work, always produce:
- domain model changes if needed
- resolver/provider interfaces
- graph construction logic
- clear resolution result object
- explanation of failure modes

## Future-Aware Constraints
Design for future support of:
- security_score
- stars
- downloads
- token-cost-aware selection
- runtime compatibility filters

## Definition of Done
Resolver work is complete only if:
- dependency graph is explicit
- cycle detection exists
- install order can be derived
- version conflicts are surfaced clearly
- code is isolated from installer/runtime concerns