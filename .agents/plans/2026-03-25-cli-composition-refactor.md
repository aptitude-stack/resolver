# CLI Composition Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move concrete use-case wiring out of the CLI interface layer so the CLI depends only on application-facing composition helpers.

**Architecture:** Introduce an application-owned composition module that assembles configured use cases from the registry adapter and settings. Keep the CLI responsible only for parsing input, invoking use cases, formatting output, and exit codes.

**Tech Stack:** Python, Typer, pytest

---

### Task 1: Move composition out of the CLI

**Files:**
- Create: `src/aptitude_client/application/composition.py`
- Modify: `src/aptitude_client/interfaces/cli/app.py`

- [ ] **Step 1: Add the application composition helpers for resolve/install**
- [ ] **Step 2: Update the CLI to import those helpers instead of constructing registry/settings directly**
- [ ] **Step 3: Keep the CLI helper surface stable for tests and future interfaces**

### Task 2: Verify architecture-facing behavior

**Files:**
- Modify: `tests/unit/interfaces/cli/test_app.py` only if needed
- Optionally create: `tests/unit/application/test_composition.py`

- [ ] **Step 1: Add or adjust tests for the new composition module if needed**
- [ ] **Step 2: Run the focused CLI/import regression suite**
- [ ] **Step 3: Recheck that the CLI no longer imports registry or settings directly**
