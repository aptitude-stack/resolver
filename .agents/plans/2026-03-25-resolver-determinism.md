# Resolver Determinism Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Aptitude resolution independent of registry dependency ordering so the graph, install order, and lockfile are deterministic for the same logical input.

**Architecture:** Canonical ordering must be applied inside the resolver before traversal, edge insertion, and post-order install derivation. The serializer remains passive and only reflects the already-deterministic graph.

**Tech Stack:** Python, pytest

---

### Task 1: Add order-independence tests

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_recursive_graph_resolver.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`

- [ ] Add a resolver test that feeds the same dependencies in different orders and asserts identical graph structure, identical install order, and identical traceable traversal order.
- [ ] Add a lockfile test that builds locks from reordered dependency inputs and asserts byte-identical serialized lockfiles.

### Task 2: Canonicalize dependencies inside the resolver

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\resolver\graph\recursive_graph_resolver.py`

- [ ] Add a canonical dependency sort key based on exact version when present, otherwise normalized selector form.
- [ ] Sort dependency lists before normalization/traversal.
- [ ] Emit trace entries for received dependency order, sorted dependency order, and traversal order.
- [ ] Ensure graph node/edge/install-order construction remains deterministic from that canonical traversal.

### Task 3: Verify the full suite

**Files:**
- No additional code files if prior tasks are complete.

- [ ] Run focused resolver and lockfile pytest slices.
- [ ] Run the full pytest suite.
