# Lock-Driven Flow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the graph-driven install flow with a lock-driven pipeline that produces a rich lock artifact, replays from lock, and executes/materializes from locked data only.

**Architecture:** `PlanSkillResolutionQuery` remains the application orchestrator, but it now drives the flow through governance, lock generation, and execution planning. The lockfile becomes the durable handoff artifact between planning and execution, while the execution module owns materialization, checksum verification, and execution-plan construction from lock data only.

**Tech Stack:** Python, Pydantic DTOs, dataclasses, pytest

---

## Chunk 1: Lock Schema and Replay

### Task 1: Add lockfile tests first

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`

- [ ] Add failing tests for deterministic lock building, JSON serialization/parsing, and replay from lock only.
- [ ] Run the new lockfile test module and confirm it fails for the missing schema/parser/replay behavior.

### Task 2: Implement the rich lock schema

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\model.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\serializer.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\parser.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\replay.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\__init__.py`
- Delete: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\resolver\replay\replay_stub.py`
- Delete: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\resolver\replay\__init__.py`

- [ ] Add rich lock dataclasses for root metadata, locked nodes, edges, install order, and governance snapshot.
- [ ] Implement deterministic `build_lockfile(...)`, `serialize_lockfile(...)`, `parse_lockfile(...)`, and `load_lockfile(...)`.
- [ ] Implement `replay_lockfile(...)` that reconstructs execution-ready structures from lock data only.
- [ ] Run the lockfile tests and make sure they pass.

## Chunk 2: Lock-Driven Execution

### Task 3: Move execution/materialization into `execution/`

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\plan.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\materialize.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\execution\__init__.py`
- Delete or gut: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\commands\install_resolved_graph.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\commands\__init__.py`
- Create/modify tests under `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\`

- [ ] Change execution planning to consume `Lockfile`, not `ResolutionGraph`.
- [ ] Move checksum verification, staging/materialization, and metadata writing into execution-owned code.
- [ ] Ensure materialization uses only lock data plus artifact content fetches.
- [ ] Add focused execution tests for plan generation and materialization from lock.

## Chunk 3: Rewire Application Flow

### Task 4: Make planning produce lock + execution preview

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\resolve_skill_query.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\install_skill.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\resolution_mapping.py`

- [ ] Extend the planning artifact so governance is followed by lock generation and execution planning.
- [ ] Make `resolve` return the lock artifact / lock preview plus execution preview.
- [ ] Make `install` materialize from the planned lock artifact instead of the transient graph.
- [ ] Remove any remaining graph-driven execution path.

### Task 5: Update DTOs and CLI expectations

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\resolve_result_dto.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\install_dto.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\__init__.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`

- [ ] Add DTOs for the lock schema and execution-plan preview.
- [ ] Keep human-friendly install output stable while exposing the new lock-driven data in JSON mode.
- [ ] Update resolve JSON expectations to include the real lock preview and execution preview.

## Chunk 4: Verification

### Task 6: Update and run the affected test slices

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\commands\test_install_resolved_graph.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_install_skill.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\shared\test_imports.py`

- [ ] Remove or replace tests that assume graph-driven execution.
- [ ] Run the full affected pytest slices and confirm the lock-driven flow is the only remaining path.
