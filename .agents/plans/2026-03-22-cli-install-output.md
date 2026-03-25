# CLI Install Output Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default `install` JSON output with a human-readable English summary inspired by `pip`/`npm`, while preserving structured JSON via an explicit flag.

**Architecture:** Keep formatting in the CLI interface layer so application DTOs and use cases stay transport-agnostic. Add focused CLI helpers for rendering install progress-style text, then update interface tests to cover both default and `--json` output paths.

**Tech Stack:** Python, Typer, pytest

---

### Task 1: Shape the CLI output contract

**Files:**
- Modify: `src/aptitude_client/interfaces/cli/app.py`
- Test: `tests/unit/interfaces/cli/test_app.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run the targeted CLI test to confirm the current JSON output fails the new expectation**
- [ ] **Step 3: Add CLI-only formatting helpers and a `--json` escape hatch**
- [ ] **Step 4: Run the targeted CLI test to confirm the new default output passes**

### Task 2: Cover structured output and final UX details

**Files:**
- Modify: `tests/unit/interfaces/cli/test_app.py`
- Modify: `src/aptitude_client/interfaces/cli/app.py`

- [ ] **Step 1: Add a regression test for `install --json`**
- [ ] **Step 2: Implement any missing wiring for JSON passthrough**
- [ ] **Step 3: Verify the success text includes the installed coordinate list and final install path**
- [ ] **Step 4: Run the focused CLI/unit verification suite**
