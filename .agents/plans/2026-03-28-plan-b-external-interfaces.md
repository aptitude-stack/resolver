# Plan B: External Interfaces Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add external programmatic interfaces to the Aptitude client only after the internal planning, governance, resilience, and test surface are stable.

**Architecture:** Keep new interfaces thin. `interfaces/sdk/` and `interfaces/mcp/` must wrap existing composition and use-case flows; they must not introduce new solver, governance, or execution logic. SDK comes first, MCP second. Both must preserve the current lock-driven execution contract and must not bypass orchestration in `application/`.

**Tech Stack:** Python, Pydantic DTOs, pytest, FastMCP or Python MCP SDK

---

## Scope Boundaries

- This plan starts only after Plan A stabilizes internal behavior and coverage.
- This plan includes:
  - SDK
  - MCP
- This plan does **not** include:
  - governance redesign
  - selection/ranking changes
  - cache/retry
  - observability expansion
- Both interfaces must remain adapters over existing use cases.
- Neither interface may bypass lock replay, governance, or resolver orchestration.

## Planned File Ownership

### SDK Interface

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\sdk\test_client.py`

### MCP Interface

- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\server.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\mcp\test_server.py`

---

## Chunk 1: Stable Python SDK

### Task 1: Freeze the SDK boundary in docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `interfaces/sdk/` as a real top-level interface package.
- [ ] State that SDK methods are thin adapters over:
  - `ResolveSkillQueryUseCase`
  - `InstallSkillUseCase`
  - `SyncFromLockUseCase`
- [ ] State that SDK must not bypass use-case orchestration or create a parallel pipeline.

### Task 2: Implement the SDK facade

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\sdk\client.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\sdk\test_client.py`

- [ ] Add a small `AptitudeClient` facade with methods like:
  - `resolve(...)`
  - `install(...)`
  - `sync(...)`
- [ ] Reuse the same composition/use-case wiring used by CLI.
- [ ] Return stable DTO-shaped outputs.
- [ ] Add tests for happy path and error shaping.
- [ ] Run: `py -3 -m pytest tests/unit/interfaces/sdk/test_client.py -v`

---

## Chunk 2: MCP Interface After SDK Stabilizes

### Task 3: Freeze the MCP boundary in docs

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Document `interfaces/mcp/` as a real external interface package.
- [ ] State that MCP wraps existing SDK or use-case behavior and must not add hidden business logic.
- [ ] State that MCP remains subject to the same lock-driven execution and governance rules as CLI/SDK.

### Task 4: Implement the MCP server

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\__init__.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\mcp\server.py`
- Create: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\mcp\test_server.py`

- [ ] Use the `mcp-builder` skill when this task starts.
- [ ] Expose only thin tools around:
  - resolve
  - install
  - sync
- [ ] Prefer reusing the SDK surface once it exists.
- [ ] Add unit tests for tool wiring and error propagation.
- [ ] Run: `py -3 -m pytest tests/unit/interfaces/mcp/test_server.py -v`

---

## Recommended Execution Order

1. Chunk 1: SDK
2. Chunk 2: MCP

## Validation Commands

- `py -3 -m pytest tests/unit/interfaces/sdk/test_client.py -v`
- `py -3 -m pytest tests/unit/interfaces/mcp/test_server.py -v`
- `py -3 -m pytest -v`

## Notes

- Do not start this plan until Plan A has stabilized the internal behavior and coverage.
- Keep both interfaces thin and orchestration-only.
- Prefer SDK reuse from MCP rather than duplicating interface plumbing.
