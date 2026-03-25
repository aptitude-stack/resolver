# Discovery Boundary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move discovery-specific candidate orchestration out of `application/queries` and into `discovery/` without changing CLI or use-case behavior.

**Architecture:** Keep `application` responsible for use-case orchestration and resolution planning, while `discovery` owns query interpretation, candidate enrichment, and reranking over the registry port. Preserve the registry anti-corruption boundary and avoid any new direct `interfaces -> discovery` bypasses.

**Tech Stack:** Python, pytest, Pydantic DTOs, dataclasses

---

## Chunk 1: Boundary Move

### Task 1: Relocate discovery orchestration

**Files:**
- Create: `.agents/plans/2026-03-25-discovery-boundary-cleanup.md`
- Create: `src/aptitude_client/discovery/candidate_discovery.py`
- Modify: `src/aptitude_client/discovery/__init__.py`
- Modify: `src/aptitude_client/application/queries/plan_skill_resolution.py`
- Modify: `src/aptitude_client/application/queries/__init__.py`
- Delete: `src/aptitude_client/application/queries/discover_skill_candidates.py`

- [ ] **Step 1: Copy the current candidate discovery orchestration into the discovery package**

Preserve:
- slug-like query short-circuit
- trace creation
- candidate enrichment
- client-side reranking
- stale dotted slug handling

- [ ] **Step 2: Repoint application planning to discovery-owned orchestration**

`PlanSkillResolutionQuery` should depend on the discovery package for candidate discovery while keeping selection, graph resolution, and policy evaluation in `application`.

- [ ] **Step 3: Remove stale application exports**

Do not leave `application.queries` exporting a discovery-owned component.

## Chunk 2: Safety Net

### Task 2: Align tests and verify imports

**Files:**
- Create: `tests/unit/discovery/test_candidate_discovery.py`
- Modify: `tests/unit/shared/test_imports.py`

- [ ] **Step 1: Add focused discovery tests**

Cover:
- exact slug hit bypasses discovery
- missing dotted slug raises `SkillNotFoundError`
- discovery fallback reranks deterministically
- metadata enrichment still occurs when version summaries are incomplete

- [ ] **Step 2: Update import smoke tests**

Ensure the discovery package exports the new orchestration module and the application package still imports cleanly.

- [ ] **Step 3: Run focused pytest verification**

Run:
- `py -3 -m pytest tests/unit/discovery/test_candidate_discovery.py tests/unit/discovery/test_candidate_reranker.py tests/unit/discovery/test_query_builder.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/use_cases/test_explicit_slug_behavior.py tests/unit/shared/test_imports.py -v`

Expected:
- discovery tests pass
- application use-case behavior remains unchanged
- import smoke tests remain green
