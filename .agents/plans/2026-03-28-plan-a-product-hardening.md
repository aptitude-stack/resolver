# Plan A: Product Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the Aptitude client's internal behavior, policy controls, resilience, and observability before exposing any new public programmatic interface.

**Architecture:** Keep the existing ownership boundaries intact: governance owns hard legality, discovery owns non-final reranking, resolver owns deterministic solving and final root selection, lockfile remains the durable resolved artifact, and execution stays strictly lock-driven. This plan is internal hardening only; it must not introduce any SDK or MCP surface and must not make execution depend on debug, trace, telemetry, or preference metadata.

**Tech Stack:** Python, Typer, dataclasses, Pydantic DTOs, pytest, diskcache, tenacity, structlog

---

## Scope Boundaries

- This plan covers only:
  - test hardening
  - hard policy CLI overrides
  - cache and retry
  - observability
  - advanced governance
- This plan does **not** include:
  - SDK
  - MCP
  - `latest` selection profile
  - broad org-policy merge semantics before the contract is frozen
- Cache must remain advisory and must not affect correctness.
- Execution must remain lock-driven and must not depend on telemetry or explainability metadata.
- Do not claim offline fresh planning because of discovery cache.

## Planned File Ownership

### Test Hardening

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_parser.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_replay.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_debug_artifacts.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\discovery\test_query_builder.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_dependency_normalizer.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_conflict_rules.py`

### Hard Policy CLI Overrides

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`

### Cache And Retry

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\store.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\keys.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\client.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\cache\test_store.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\registry\test_client.py`

### Observability

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\logging\configure.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\telemetry\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\telemetry\metrics.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\install_skill.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\sync_from_lock.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\telemetry\test_metrics.py`

### Advanced Governance

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\config\aptitude_config.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\governance\evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

---

## Chunk 1: Test Hardening Before New Behavior

### Task 1: Freeze Phase A priorities in the canonical docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Add a short note that the next internal wave is:
  - test hardening
  - hard policy CLI overrides
  - cache and retry
  - observability
  - advanced governance
- [ ] Explicitly note that SDK and MCP are not part of this plan.
- [ ] Keep `latest` deferred.

### Task 2: Add direct lockfile parser coverage

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_parser.py`

- [ ] Write failing tests for malformed JSON, wrong top-level shape, missing required fields, and backward compatibility for older locks without `selection`.
- [ ] Run: `py -3 -m pytest tests/unit/lockfile/test_parser.py -v`
- [ ] Implement only the minimum parser changes if a real gap appears.
- [ ] Re-run until green.

### Task 3: Add direct lock replay coverage

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_replay.py`

- [ ] Write failing tests for duplicate install-order entries, missing root nodes, unknown nodes in install order, and edge references to missing nodes.
- [ ] Run: `py -3 -m pytest tests/unit/lockfile/test_replay.py -v`
- [ ] Implement only the minimum replay validation changes if needed.
- [ ] Re-run until green.

### Task 4: Add direct debug-artifact coverage

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_debug_artifacts.py`

- [ ] Write tests for `graph.json`, `trace.json`, and `policy.json` output.
- [ ] Verify exact file names and minimal payload shape.
- [ ] Run: `py -3 -m pytest tests/unit/execution/test_debug_artifacts.py -v`

### Task 5: Harden resolver/discovery edge-case coverage

**Files:**
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_dependency_normalizer.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_conflict_rules.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\discovery\test_query_builder.py`

- [ ] Add selector-normalization edge cases.
- [ ] Add version-conflict edge cases.
- [ ] Add intent/query edge cases:
  - empty-like queries
  - non-Latin characters
  - very long input
- [ ] Run the focused resolver/discovery suite.

### Task 6: Harden CLI/config error coverage

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Add `_format_error()` coverage for current domain error types surfaced by CLI.
- [ ] Add a full-stack config precedence test covering:
  - CLI
  - env
  - workspace
  - user
  - default
- [ ] Run: `py -3 -m pytest tests/unit/interfaces/cli/test_app.py tests/unit/application/test_composition.py -v`

---

## Chunk 2: Hard Policy CLI Overrides

### Task 7: Freeze the per-request policy override contract

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document that Plan A adds CLI per-request policy overrides for:
  - `allowed_trust_tiers`
  - `allowed_lifecycle_statuses`
  - `max_token_estimate`
  - `max_content_size_bytes`
- [ ] Keep them client-owned policy inputs, not selection preferences.
- [ ] Keep workspace/org policy merge semantics deferred.
- [ ] Do not add `latest`.

### Task 8: Pass hard policy overrides through composition

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Add a composition helper for one effective `PolicyContext`.
- [ ] Support only:
  - client defaults
  - CLI per-request overrides
- [ ] Keep workspace/org policy loading out of this chunk.
- [ ] Add precedence tests proving CLI overrides the default policy.

### Task 9: Expose hard policy flags in the CLI

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`

- [ ] Add:
  - `--allow-trust`
  - `--allow-lifecycle`
  - `--max-tokens`
  - `--max-content-size`
- [ ] Keep parsing strict and deterministic.
- [ ] Ensure the flags affect only fresh-planning commands:
  - `install`
  - hidden `resolve`
- [ ] Ensure `sync --lock` ignores them entirely.
- [ ] Add help and wiring tests.

### Task 10: Verify policy overrides affect governance only

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`

- [ ] Add tests proving:
  - `--allow-trust` rejects candidates/graphs outside the allowed set
  - `--allow-lifecycle` rejects disallowed lifecycle states
  - `--max-tokens` and `--max-content-size` enforce ceilings
- [ ] Add at least one end-to-end use-case test from CLI override to policy failure.
- [ ] Run: `py -3 -m pytest tests/unit/governance/test_evaluator.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/test_composition.py tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`

---

## Chunk 3: Cache And Retry

### Task 11: Freeze cache and retry semantics

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `cache/` as a real top-level package.
- [ ] State that cache must not affect correctness.
- [ ] State that offline replay is valid only when immutable content was already cached.
- [ ] State that retries apply only to transient transport failures.

### Task 12: Implement immutable-content-first caching

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\store.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\keys.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\cache\test_store.py`

- [ ] Add content caching keyed by checksum/digest first.
- [ ] Then add exact metadata/version-list caching.
- [ ] Add discovery caching last, with short TTL and explicit tests for non-authoritative behavior.
- [ ] Run focused cache and registry tests.

### Task 13: Add retry logic only for transient registry failures

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\client.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\registry\test_client.py`

- [ ] Wrap only the transport boundary with bounded retry/backoff.
- [ ] Retry only transient failures.
- [ ] Do not retry policy, schema, not-found, or auth errors.
- [ ] Add tests proving retries happen only where intended.

---

## Chunk 4: Structured Observability

### Task 14: Add structured logging without replacing trace

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\logging\configure.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Add `structlog`-based configuration.
- [ ] Keep decision explainability in the trace model, not in logs.
- [ ] Add only minimal tests/config checks needed.

### Task 15: Add stage timing telemetry

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\telemetry\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\telemetry\metrics.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\install_skill.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\sync_from_lock.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\telemetry\test_metrics.py`

- [ ] Record timing for:
  - discovery
  - resolution
  - governance
  - lock
  - execution planning
  - materialization
- [ ] Keep telemetry additive and non-blocking.
- [ ] Ensure execution does not depend on telemetry state.

---

## Chunk 5: Advanced Governance

### Task 16: Freeze the org/workspace policy contract before code

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Decide and document whether CLI may loosen organization policy.
- [ ] Recommended contract:
  - org policy sets hard ceilings/floors
  - workspace/user/CLI may become stricter
  - they may not become looser
- [ ] Do not implement merge logic until this is written down.

### Task 17: Add workspace policy loading

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\config\aptitude_config.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Load policy sections from workspace config.
- [ ] Merge them only according to the documented contract.
- [ ] Keep the implementation concrete; do not add a plugin rule engine yet.

### Task 18: Add graph-level aggregate resource ceilings

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\governance\evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`

- [ ] Add aggregate graph-level token and content-size checks.
- [ ] Keep them separate from candidate-level root filtering.
- [ ] Add direct tests for pass/fail cases.

---

## Recommended Execution Order

1. Chunk 1: test hardening
2. Chunk 2: hard policy CLI overrides
3. Chunk 3: cache and retry
4. Chunk 4: observability
5. Chunk 5: advanced governance

## Validation Commands

- `py -3 -m pytest tests/unit/lockfile/test_parser.py tests/unit/lockfile/test_replay.py tests/unit/execution/test_debug_artifacts.py tests/unit/interfaces/cli/test_app.py tests/unit/application/test_composition.py -v`
- `py -3 -m pytest tests/unit/governance/test_evaluator.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/test_composition.py tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`
- `py -3 -m pytest tests/unit/cache/test_store.py tests/unit/registry/test_client.py -v`
- `py -3 -m pytest tests/unit/telemetry/test_metrics.py -v`
- `py -3 -m pytest -v`

## Notes

- Keep hard legality and soft preference separate.
- Keep lock replay independent from fresh-planning config and policy sources.
- Keep cache advisory and execution lock-driven.
- Keep SDK and MCP out of this plan.
- Keep `latest` deferred until there is an explicit product need and ranking contract.
