# Discovery Version Selection Separation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move concrete candidate version selection out of `discovery/` and into `resolver/` while preserving the current resolve/install UX.

**Architecture:** Discovery should stop producing version-selected candidates and instead return skill-level discovery matches plus available versions and trace data. The application planning layer will then hand those matches to a resolver-owned version resolution step, keeping discovery focused on discovery and resolver focused on deterministic version choice.

**Tech Stack:** Python, pytest, dataclasses, Pydantic DTOs

---

## Chunk 1: Discovery Output Boundary

### Task 1: Introduce skill-level discovery matches

**Files:**
- Create: `.agents/plans/2026-03-25-discovery-version-selection-separation.md`
- Create: `src/aptitude_client/domain/models/discovered_skill.py`
- Modify: `src/aptitude_client/domain/models/__init__.py`
- Modify: `src/aptitude_client/discovery/candidate_discovery.py`

- [ ] **Step 1: Add a discovery output model that carries slug and available versions without a chosen version**
- [ ] **Step 2: Update discovery orchestration to return discovered skills plus trace**
- [ ] **Step 3: Remove resolver-owned version selection from discovery**

## Chunk 2: Resolver-Owned Version Resolution

### Task 2: Add a resolver step that turns discovered skills into versioned candidates

**Files:**
- Create: `src/aptitude_client/resolver/solver/candidate_version_resolution.py`
- Modify: `src/aptitude_client/resolver/solver/__init__.py`
- Modify: `src/aptitude_client/application/queries/plan_skill_resolution.py`
- Modify: `src/aptitude_client/application/use_cases/resolution_mapping.py`

- [ ] **Step 1: Add a resolver helper that selects a concrete version for each discovered skill**
- [ ] **Step 2: Emit trace entries for version resolution decisions**
- [ ] **Step 3: Reuse existing candidate DTO mapping on resolver-produced versioned candidates**

## Chunk 3: Safety Net

### Task 3: Update tests and verify behavior

**Files:**
- Create: `tests/unit/resolver/test_candidate_version_resolution.py`
- Modify: `tests/unit/application/use_cases/test_resolve_skill_query.py`
- Modify: `tests/unit/application/use_cases/test_install_skill.py`
- Modify: `tests/unit/shared/test_imports.py`

- [ ] **Step 1: Add focused resolver tests for candidate version resolution**
- [ ] **Step 2: Update use-case tests to assert the same public outcomes still hold**
- [ ] **Step 3: Run focused pytest verification**

