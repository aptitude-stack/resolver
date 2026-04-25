# Governance And Lock Replay Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-value remaining gaps after the architecture cleanup by expanding governance beyond lifecycle-only checks, hardening the lock replay and `sync` flow, and removing install/sync behavior drift.

**Architecture:** Keep fresh planning and lock replay as separate canonical pipelines. Governance work stays in `domain/` and `governance/`, lock replay hardening stays in `lockfile/`, `execution/`, `application/`, and `interfaces/cli/`, and execution must remain lock-driven in every phase.

**Tech Stack:** Python, Typer, Pydantic DTOs, pytest

---

## Scope Summary

The current baseline is strong, but these gaps are still open:

1. The canonical architecture now defines two governance phases and an explicit checksum contract, but code does not fully match that contract yet.
2. Governance currently enforces lifecycle only.
3. `sync --lock` works, but its negative-path coverage and isolation guarantees are still thinner than the fresh-planning flow.
4. `install` and `sync` share lock-driven materialization, but supplemental artifact behavior is not yet fully aligned or explicitly decided.
5. Organization-specific governance rules likely need additional metadata beyond what the current domain model carries.

## Chunk 0: Contract Freeze

### Task 0: Keep selection, governance, and checksum semantics canonical before code changes

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\README.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\.agents\memory\meta.md`

- [x] Define server-owned metadata vs client-owned policy.
- [x] Define two governance phases: candidate-policy filtering and graph governance.
- [x] Define deterministic ranking only among policy-compliant candidates.
- [x] Define the phase 1 checksum contract.
- [x] Define the need for a minimal policy snapshot in the lockfile.

## Chunk 1: Governance Phase 1

### Task 1: Expand governance to trust and resource ceilings

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\governance\evaluator.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\resolution_mapping.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\model.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\serializer.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\governance\test_evaluator.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`

- [ ] Define the first non-lifecycle policy inputs in `PolicyContext`.
- [ ] Start with signals already present in the graph: `trust_tier`, `token_estimate`, and `content_size_bytes`.
- [ ] Implement explicit policy rules such as allowed trust tiers and optional token/content ceilings.
- [ ] Make failed governance rules block fresh planning before lock generation.
- [ ] Persist the resulting governance snapshot in the lockfile so replay can explain governed outcomes.
- [ ] Add happy-path and failure-path tests for each new rule.

### Task 2: Decide the organization-rules prerequisite

**Files:**
- Review: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\models\skill_metadata.py`
- Review: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\transport_models.py`
- Review: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\registry\mappers.py`
- Review: `C:\Dev\apptitude-client\aptitude-client\docs\openapi\`
- Document: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md` if the required metadata model changes

- [ ] Confirm which server-owned provenance or publisher fields are actually available and stable.
- [ ] If enough organization metadata already exists, plan a second governance slice that maps it into domain and lockfile models.
- [ ] If the metadata is not available, document that organization rules are intentionally deferred rather than guessed.

## Chunk 2: Lock Replay Hardening

### Task 3: Harden lock parsing and sync failure behavior

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\parser.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\sync_from_lock.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\materialize.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_sync_from_lock.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_materialize.py`

- [ ] Add explicit tests for invalid JSON lock payloads.
- [ ] Add explicit tests for missing required fields and wrong JSON shapes.
- [ ] Add sync-path tests for checksum mismatch propagation.
- [ ] Add sync-path tests for non-file lock paths.
- [ ] Ensure error messages remain machine-readable and user-debuggable.

### Task 4: Prove sync isolation from discovery and resolver

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_sync_from_lock.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`

- [ ] Add a lock-sync fake that exposes only `fetch_skill_content`.
- [ ] Add trap methods for discovery and resolver-like behavior so unexpected calls fail immediately.
- [ ] Assert that `sync --lock` uses lock parse plus execution only.

### Task 5: Tighten sync CLI UX coverage

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`

- [ ] Add explicit `sync --help` coverage, not just top-level help.
- [ ] Verify the `--lock` requirement and help text stay clear after future CLI growth.
- [ ] Keep the user-facing sync output aligned with the install UX style.

## Chunk 3: Install/Sync Convergence

### Task 6: Remove materialization drift between install and sync

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\install_skill.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\sync_from_lock.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\materialize.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\debug_artifacts.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_install_skill.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_sync_from_lock.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_materialize.py`

- [ ] Decide whether `sync` should write the same supplemental debug artifacts as `install`, or whether the difference should stay intentional and documented.
- [ ] If parity is the goal, move the shared behavior into execution-owned helpers so application still only orchestrates.
- [ ] Add tests that compare the resulting `resolution/` artifacts for install-from-lock and sync-from-lock paths.
- [ ] Keep `aptitude.lock.json` and `execution-plan.json` identical when the lock input is the same.

### Task 7: Keep install explicitly lock-driven at execution time

**Files:**
- Review: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\install_skill.py`
- Review: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\materialize.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_install_skill.py`

- [ ] Preserve the rule that install may plan from a fresh graph, but execution/materialization must consume the generated lock only.
- [ ] Add a regression test that would fail if install starts reading graph state during materialization.

## Chunk 4: Post-Hardening Follow-Up

### Task 8: Decide when to add new top-level packages

**Files:**
- Review: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Review: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Review: `C:\Dev\apptitude-client\aptitude-client\.agents\plans\roadmap.md`

- [ ] Do not add `plugins/`, `cache/`, or `telemetry/` during the governance/sync hardening work unless a concrete implementation requirement appears.
- [ ] Revisit these only after the governance and lock replay surfaces are stable.

## Recommended Execution Order

0. Contract freeze in canonical docs
1. Governance phase 1
2. Lock replay hardening
3. Install/sync convergence
4. Organization-rule follow-up only if server metadata supports it

## Validation Targets

- `py -3 -m pytest tests/unit/governance -v`
- `py -3 -m pytest tests/unit/application/use_cases/test_sync_from_lock.py tests/unit/lockfile/test_lockfile.py tests/unit/execution/test_materialize.py -v`
- `py -3 -m pytest tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`
- `py -3 -m pytest -v`

## Notes

- Keep `docs/ARCHITECTURE.md` and `docs/RULES.md` in sync if any ownership or pipeline rule changes.
- If organization governance requires new server metadata, treat that as an explicit architecture review point instead of silently extending the model.
