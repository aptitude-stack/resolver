# Phase 2 Productization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Aptitude client with user-facing hard policy overrides, stronger test coverage, a stable Python SDK, cache/retry infrastructure, structured observability, and later advanced governance and MCP support without weakening the current lock-driven architecture.

**Architecture:** Preserve the existing split: hard legality stays in `governance/`, soft preference stays in `discovery/`, deterministic solving stays in `resolver/`, lock durability stays in `lockfile/`, and execution remains strictly lock-driven. New features in this plan must stay additive: cache must not affect correctness, logging/telemetry must not become decision sources, and SDK/MCP surfaces must remain thin interface adapters over existing use cases.

**Tech Stack:** Python, Typer, dataclasses, Pydantic DTOs, pytest, diskcache, tenacity, structlog, FastMCP or Python MCP SDK (later milestone)

---

## Scope Boundaries

- This plan is for **Phase 2 only**.
- Do **not** change lock determinism semantics in this wave.
- Do **not** make execution depend on trace, telemetry, or explainability metadata.
- Do **not** introduce fallback-to-next-candidate behavior unless `docs/ARCHITECTURE.md` is updated first.
- Do **not** implement the `latest` selection profile in this plan.
- Do **not** implement broad org-policy merge semantics until the contract is explicitly frozen.
- Do **not** claim offline fresh planning support from discovery cache; only cached lock replay may work offline when required immutable content is already cached.

## Planned File Ownership

### Hard Policy CLI Overrides

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`

### Test Hardening

- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_parser.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_replay.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_debug_artifacts.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\discovery\test_query_builder.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_dependency_normalizer.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_conflict_rules.py`

### SDK Interface

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\sdk\test_client.py`

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
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

### MCP Interface

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\server.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\mcp\test_server.py`

---

## Chunk 1: Test Hardening Before New Behavior

### Task 1: Freeze the Phase 2 scope in the canonical docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Add a short “Phase 2 priorities” note that confirms the next order:
  - test hardening
  - hard policy CLI overrides
  - SDK
  - cache and retry
  - observability
  - advanced governance
  - MCP
- [ ] Keep `latest` explicitly deferred.
- [ ] Keep org-policy merge semantics explicitly unresolved until a dedicated contract update.

### Task 2: Add direct lockfile parser tests

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_parser.py`

- [ ] Write failing tests for malformed JSON, wrong top-level shape, missing required fields, and old locks with no `selection`.
- [ ] Run: `py -3 -m pytest tests/unit/lockfile/test_parser.py -v`
- [ ] Implement only the minimum parser assertions needed if gaps are discovered.
- [ ] Re-run the same test file until green.

### Task 3: Add direct lock replay tests

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_replay.py`

- [ ] Write failing tests for:
  - missing nodes referenced by install order
  - duplicate install-order entries
  - missing root node
  - edge references to unknown nodes
- [ ] Run: `py -3 -m pytest tests/unit/lockfile/test_replay.py -v`
- [ ] Implement only the minimum replay validation changes if a gap is found.
- [ ] Re-run until green.

### Task 4: Add direct debug-artifact tests

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_debug_artifacts.py`

- [ ] Write tests for `graph.json`, `trace.json`, and `policy.json` file output.
- [ ] Verify exact file names and minimal payload shape.
- [ ] Run: `py -3 -m pytest tests/unit/execution/test_debug_artifacts.py -v`

### Task 5: Harden resolver/discovery edge-case coverage

**Files:**
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_dependency_normalizer.py`
- Create or modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\resolver\test_conflict_rules.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\discovery\test_query_builder.py`

- [ ] Add direct selector-normalization edge cases.
- [ ] Add direct version-conflict edge cases.
- [ ] Add intent/query edge cases:
  - empty-like queries
  - non-Latin characters
  - very long input
- [ ] Run the focused resolver/discovery suite.

### Task 6: Harden CLI/config failure coverage

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Add `_format_error()` coverage for all current domain error types surfaced by CLI.
- [ ] Add a full-stack config precedence test for:
  - CLI
  - env
  - workspace
  - user
  - default
- [ ] Run:
  - `py -3 -m pytest tests/unit/interfaces/cli/test_app.py tests/unit/application/test_composition.py -v`

---

## Chunk 2: Hard Policy CLI Overrides

### Task 7: Freeze the contract for per-request policy overrides

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document that Phase 2 adds CLI per-request overrides for:
  - `allowed_trust_tiers`
  - `allowed_lifecycle_statuses`
  - `max_token_estimate`
  - `max_content_size_bytes`
- [ ] Keep them client-owned policy inputs, not selection preferences.
- [ ] State clearly that broader workspace/org policy precedence remains a later step.
- [ ] Do **not** add `latest` here.

### Task 8: Pass policy overrides through composition

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Add a composition helper for one effective `PolicyContext`.
- [ ] Support only:
  - client defaults
  - CLI per-request overrides
- [ ] Keep workspace/org policy loading deferred.
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
- [ ] Ensure the flags affect only fresh planning commands:
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
- [ ] Add at least one end-to-end use-case test from CLI override -> policy failure.
- [ ] Run:
  - `py -3 -m pytest tests/unit/governance/test_evaluator.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/test_composition.py tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`

---

## Chunk 3: Stable Python SDK

### Task 11: Freeze the SDK boundary in docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `interfaces/sdk/` as a real top-level interface package.
- [ ] State that SDK methods are thin adapters over:
  - `PlanSkillResolutionQuery`
  - `ResolveSkillQueryUseCase`
  - `InstallSkillUseCase`
  - `SyncFromLockUseCase`
- [ ] State that SDK must not bypass use-case orchestration.

### Task 12: Implement the SDK facade

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\sdk\test_client.py`

- [ ] Add a small `AptitudeClient` facade with methods like:
  - `resolve(...)`
  - `install(...)`
  - `sync(...)`
- [ ] Reuse the same composition/use-case wiring already used by CLI.
- [ ] Add tests for stable DTO-shaped outputs.
- [ ] Run:
  - `py -3 -m pytest tests/unit/interfaces/sdk/test_client.py -v`

---

## Chunk 4: Cache And Retry

### Task 13: Freeze cache semantics before implementation

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `cache/` as a now-real top-level package.
- [ ] State that cache must not affect correctness.
- [ ] State that offline replay is only valid when immutable content was already cached.
- [ ] State that cache is advisory and the lock remains the source of truth.

### Task 14: Implement immutable-content-first caching

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\store.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\cache\keys.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\cache\test_store.py`

- [ ] Add content cache keyed by checksum/digest first.
- [ ] Then add exact metadata/version-list caching.
- [ ] Add discovery caching last, with short TTL and explicit tests for non-authoritative behavior.
- [ ] Run focused cache and registry tests.

### Task 15: Add retry logic only for transient registry failures

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\client.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\registry\test_client.py`

- [ ] Wrap only the transport boundary with bounded retry/backoff.
- [ ] Retry only transient failures.
- [ ] Do not retry policy, schema, not-found, or auth errors.
- [ ] Add tests proving retries happen only where intended.

---

## Chunk 5: Structured Observability

### Task 16: Add structured logging without replacing trace as the source of decision truth

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\logging\configure.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Add `structlog`-based configuration.
- [ ] Keep decision explainability in the trace model, not in logs.
- [ ] Add only minimal tests/config checks needed.

### Task 17: Add telemetry timing for major pipeline stages

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

## Chunk 6: Advanced Governance Foundations

### Task 18: Freeze the org/workspace policy contract before code

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Decide and document whether CLI may loosen organization policy.
- [ ] My recommended contract:
  - org policy sets hard ceilings/floors
  - workspace/user/CLI may become stricter
  - they may not become looser
- [ ] Do not implement merge logic until this is written down.

### Task 19: Add workspace policy loading

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\config\aptitude_config.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Load policy sections from workspace config.
- [ ] Merge them according to the documented contract only.
- [ ] Keep the implementation concrete; do not add a plugin rule engine yet.

### Task 20: Add graph-level aggregate resource ceilings

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\governance\evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`

- [ ] Add aggregate graph-level token and content-size checks.
- [ ] Keep them separate from candidate-level root filtering.
- [ ] Add direct tests for pass/fail cases.

---

## Chunk 7: MCP Interface After SDK Stabilizes

### Task 21: Freeze the MCP boundary in docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `interfaces/mcp/` as a real external interface package.
- [ ] State that MCP wraps existing SDK/use-case behavior; it must not add hidden business logic.

### Task 22: Implement the MCP server

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\server.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\mcp\test_server.py`

- [ ] Use the `mcp-builder` skill when this task starts.
- [ ] Expose only thin tools around:
  - resolve
  - install
  - sync
- [ ] Reuse the SDK or use-case surface rather than duplicating workflow logic.

---

## Explicit Deferrals

- `latest` selection profile
- dynamic plugin-based governance engines
- broad org-policy merge semantics before the contract is frozen
- any execution dependency on preference, policy, trace, or telemetry metadata
- claiming fresh planning works offline because of discovery cache

## Recommended Execution Order

1. Chunk 1: test hardening
2. Chunk 2: hard policy CLI overrides
3. Chunk 3: SDK
4. Chunk 4: cache and retry
5. Chunk 5: observability
6. Chunk 6: advanced governance foundations
7. Chunk 7: MCP

## Validation Commands

- `py -3 -m pytest tests/unit/lockfile/test_parser.py tests/unit/lockfile/test_replay.py tests/unit/execution/test_debug_artifacts.py tests/unit/interfaces/cli/test_app.py tests/unit/application/test_composition.py -v`
- `py -3 -m pytest tests/unit/governance/test_evaluator.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/test_composition.py tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`
- `py -3 -m pytest tests/unit/interfaces/sdk/test_client.py -v`
- `py -3 -m pytest tests/unit/cache/test_store.py tests/unit/registry/test_client.py -v`
- `py -3 -m pytest tests/unit/telemetry/test_metrics.py -v`
- `py -3 -m pytest -v`

## Notes

- Keep hard legality and soft preference separate.
- Keep lock replay independent from fresh-planning config and policy sources.
- Keep cache advisory and execution lock-driven.
- Keep SDK stable before introducing MCP.
- Keep `latest` deferred until there is an explicit product need and ranking contract.

Plan complete and saved to `.agents/plans/2026-03-28-phase-2-productization-plan.md`. Ready to execute?
