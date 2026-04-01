# CLI Wizard Replacement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default Textual TUI with a clean inline Aptitude-branded CLI wizard that uses Rich and prompt_toolkit for keyboard-first interaction.

**Architecture:** Keep the existing install workflow service and Typer subcommands, but replace the no-args launcher with a new `wizard.py` module under `interfaces/cli`. The wizard handles query input, option selection, candidate choice, plan review, install confirmation, progress rendering, and final summaries using non-fullscreen prompt_toolkit menus and Rich output; then remove the unused Textual package and dependency. The visual direction should use `skills.sh` only as loose inspiration for streamed CLI structure and keyboard ergonomics. The final interface should say `Aptitude` at the top, preserve Aptitude’s own identity, and be cleaner, quieter, and more legible than `skills.sh`.

**Tech Stack:** Python, Rich, prompt_toolkit, Typer, pytest

---

## Chunk 1: Launcher Swap

### Task 1: Redirect the no-args entrypoint to the new CLI wizard

**Files:**
- Modify: `src/aptitude/interfaces/cli/main.py`
- Modify: `tests/unit/interfaces/cli/test_main.py`

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/cli/test_main.py -q` and confirm the old Textual expectations fail**
- [ ] **Step 3: Replace `run_tui_app()` with `run_cli_wizard()`**
- [ ] **Step 4: Re-run the same test command and confirm it passes**

## Chunk 2: New CLI Wizard

### Task 2: Add an inline keyboard-driven wizard module

**Files:**
- Create: `src/aptitude/interfaces/cli/wizard.py`
- Create: `tests/unit/interfaces/cli/test_wizard.py`

- [ ] **Step 1: Write failing tests for the wizard orchestration using injected prompt/select/confirm callbacks**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/cli/test_wizard.py -q` and confirm they fail**
- [ ] **Step 3: Implement a `CliWizard` that uses the shared workflow service and a non-fullscreen prompt_toolkit menu helper**
- [ ] **Step 4: Render styled CLI sections, simple spinners, and loading bars with Rich**
- [ ] **Step 5: Make `Aptitude` the clear top-level header and avoid cloning `skills.sh` line-for-line**
- [ ] **Step 6: Prefer fewer borders, tighter summaries, and better spacing than the reference CLI**
- [ ] **Step 7: Re-run the same test command and confirm it passes**

### Task 3: Preserve install semantics while improving interactivity

**Files:**
- Create: `src/aptitude/interfaces/cli/wizard.py`
- Test: `tests/unit/interfaces/cli/test_wizard.py`

- [ ] **Step 1: Ensure candidate selection re-resolves with the chosen slug**
- [ ] **Step 2: Ensure install runs with the selected profile/interaction mode/target**
- [ ] **Step 3: Re-run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/cli/test_wizard.py -q`**

### Task 4: Lock the visual direction so it is inspired by `skills.sh`, not a copy

**Files:**
- Create: `src/aptitude/interfaces/cli/wizard.py`
- Test: `tests/unit/interfaces/cli/test_wizard.py`

- [ ] **Step 1: Keep the top header Aptitude-branded rather than reproducing the reference branding**
- [ ] **Step 2: Use a restrained visual system with minimal accents and only the borders that improve scanability**
- [ ] **Step 3: Keep summaries compact and readable instead of stacking oversized boxes**
- [ ] **Step 4: Re-run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/cli/test_wizard.py -q`**

## Chunk 3: Remove Textual

### Task 5: Remove the old TUI package and dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/unit/shared/test_imports.py`
- Delete: `src/aptitude/interfaces/tui/__init__.py`
- Delete: `src/aptitude/interfaces/tui/app.py`
- Delete: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Remove `textual` from dependencies**
- [ ] **Step 2: Remove the `aptitude.interfaces.tui` import test entry**
- [ ] **Step 3: Delete the Textual package and its dedicated tests**
- [ ] **Step 4: Run the focused test/lint commands**

## Chunk 4: Refactor Cleanup

### Task 6: Clean up all TUI-era leftovers after the Rich CLI replacement

**Files:**
- Modify: `src/aptitude/interfaces/cli/main.py`
- Modify: `src/aptitude/interfaces/cli/wizard.py`
- Modify: `src/aptitude/interfaces/cli/app.py`
- Modify: `src/aptitude/interfaces/cli/__init__.py`
- Modify: `tests/unit/interfaces/cli/test_main.py`
- Modify: `tests/unit/shared/test_imports.py`
- Delete if unused: `src/aptitude/interfaces/tui/__init__.py`
- Delete if unused: `src/aptitude/interfaces/tui/app.py`
- Delete if unused: `tests/unit/interfaces/tui/test_textual_app.py`

- [ ] **Step 1: Remove stale names and comments that still describe the default flow as a TUI**
- [ ] **Step 2: Replace old `selection_source="textual"` style values with Rich CLI or wizard-specific wording where behavior depends on that metadata**
- [ ] **Step 3: Remove dead helper functions, imports, tests, and package exports that only existed for Textual**
- [ ] **Step 4: Run `rg -n "textual|interfaces.tui|run_tui_app|AptitudeInstallerApp" src tests pyproject.toml -S` and resolve any leftover references that are not intentionally retained**
- [ ] **Step 5: Re-run focused tests after cleanup**

## Chunk 5: Verification

### Task 7: Verify the replacement end to end

**Files:**
- Modify: `src/aptitude/interfaces/cli/main.py`
- Create: `src/aptitude/interfaces/cli/wizard.py`
- Modify: `tests/unit/interfaces/cli/test_main.py`
- Create: `tests/unit/interfaces/cli/test_wizard.py`
- Modify: `tests/unit/shared/test_imports.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/unit/interfaces/cli/test_main.py tests/unit/interfaces/cli/test_wizard.py tests/unit/shared/test_imports.py -q`**
- [ ] **Step 2: Run `UV_CACHE_DIR=.uv-cache uv run --extra dev ruff check src/aptitude/interfaces/cli tests/unit/interfaces/cli/test_main.py tests/unit/interfaces/cli/test_wizard.py tests/unit/shared/test_imports.py`**
- [ ] **Step 3: Review `git status --short` and confirm unrelated `skill_demo/` deletions remain untouched**
