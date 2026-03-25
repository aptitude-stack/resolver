# Final Candidate Selection Separation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move final root-candidate selection out of `application/queries` and into `resolver/solver` while preserving the current resolve/install behavior.

**Architecture:** Application should continue to coordinate discovery, version resolution, reranking, graph resolution, and governance, but it should not decide the winning candidate itself. Resolver will own deterministic candidate selection and emit the related decision trace, while application will just consume the selection result.

**Tech Stack:** Python, pytest, dataclasses

---

## Chunk 1: Resolver Selection Module

### Task 1: Introduce resolver-owned final candidate selection

**Files:**
- Create: `.agents/plans/2026-03-25-final-candidate-selection-separation.md`
- Create: `src/aptitude_client/resolver/solver/candidate_selection.py`
- Modify: `src/aptitude_client/resolver/solver/__init__.py`
- Modify: `src/aptitude_client/application/queries/plan_skill_resolution.py`

- [ ] **Step 1: Add a resolver result model for final candidate selection**
- [ ] **Step 2: Move explicit slug, single-candidate, interactive ambiguity, and top-ranked fallback decisions into resolver**
- [ ] **Step 3: Leave application responsible only for coordinating the result**

## Chunk 2: Safety Net

### Task 2: Add focused tests and verify behavior

**Files:**
- Create: `tests/unit/resolver/test_candidate_selection.py`
- Modify: `tests/unit/application/use_cases/test_resolve_skill_query.py`

- [ ] **Step 1: Add direct resolver tests for final candidate selection**
- [ ] **Step 2: Keep use-case tests green without changing public behavior**
- [ ] **Step 3: Run focused pytest verification**
