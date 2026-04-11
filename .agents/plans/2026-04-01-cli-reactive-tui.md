# CLI Reactive TUI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Aptitude Textual installer into a more CLI-native, keyboard-first, reactive terminal interface while preserving the existing install flow.

**Architecture:** Keep the current multi-screen Textual app, but shift it from button/card-heavy composition to a terminal-style event stream with stronger keyboard control. Add lightweight reactive state to the query and candidate screens so the UI responds immediately to input and selection changes without changing the underlying workflow service contract.

**Tech Stack:** Python, Textual, pytest

---

## Chunk 1: Keyboard-First Query Screen

### Task 1: Add a reactive command preview on the query screen

**Files:**
- Modify: `src/aptitude/interfaces/tui/app.py`
- Test: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/tui/test_textual_app.py -q` and confirm the new assertion fails**
- [ ] **Step 3: Add reactive query preview updates in the query screen**
- [ ] **Step 4: Re-run the same test command and confirm it passes**

### Task 2: Tighten the query screen into a CLI-style surface

**Files:**
- Modify: `src/aptitude/interfaces/tui/app.py`
- Test: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Keep the first-screen wordmark, command line, key menu, and minimal monochrome layout**
- [ ] **Step 2: Ensure the visible status copy and footer/menu remain literal text, not Rich markup**
- [ ] **Step 3: Re-run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/tui/test_textual_app.py -q`**

## Chunk 2: Reactive Candidate Navigation

### Task 3: Replace button-first candidate selection with list-first selection

**Files:**
- Modify: `src/aptitude/interfaces/tui/app.py`
- Test: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Write failing tests for arrow-key movement and enter-to-select active candidate**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/tui/test_textual_app.py -q` and confirm the candidate assertions fail**
- [ ] **Step 3: Add candidate screen state for active selection and render a reactive detail pane**
- [ ] **Step 4: Wire up `up/down/j/k/enter` so selection works without tabbing between candidate buttons**
- [ ] **Step 5: Re-run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/tui/test_textual_app.py -q`**

### Task 4: Preserve back/install flow after candidate redesign

**Files:**
- Modify: `src/aptitude/interfaces/tui/app.py`
- Test: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Keep `escape` and back navigation working**
- [ ] **Step 2: Confirm the resolved plan screen still opens with the chosen slug**
- [ ] **Step 3: Re-run the targeted test command**

## Chunk 3: Verification

### Task 5: Verify touched files

**Files:**
- Modify: `src/aptitude/interfaces/tui/app.py`
- Test: `tests/unit/interfaces/tui/test_textual_app.py`
- Test: `tests/unit/interfaces/cli/test_main.py`

- [ ] **Step 1: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/tui/test_textual_app.py tests/unit/interfaces/cli/test_main.py -q`**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev ruff check src/aptitude/interfaces/tui/app.py tests/unit/interfaces/tui/test_textual_app.py tests/unit/interfaces/cli/test_main.py`**
- [ ] **Step 3: Review the diff and confirm unrelated `skill_demo/` deletions were not touched**

