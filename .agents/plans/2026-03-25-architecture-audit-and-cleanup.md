# Architecture Audit And Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the current code and documentation against the stated Aptitude Resolver architecture, surface concrete mismatches, and remove clearly obsolete files that no longer fit the implemented direction.

**Architecture:** Review the architecture source documents first, then map current runtime modules and legacy slices to those responsibilities. Only delete files that are demonstrably obsolete or disconnected from the current runtime path; otherwise report the mismatch first and preserve the artifact for a conscious follow-up decision.

**Tech Stack:** Python, Typer, pytest, Markdown docs

---

### Task 1: Build the architecture baseline

**Files:**
- Read: `docs/Aptitude Client Architecture.md`
- Read: `docs/Aptitude Client Future Architecture.md`
- Read: `docs/Module-Responsibilities.md`
- Read: `docs/MVP.md`
- Read: `docs/scope.md`
- Read: `src/aptitude_client/**`

- [ ] **Step 1: Read the key architecture and scope documents**
- [ ] **Step 2: Inventory the current source tree and runtime entrypoints**
- [ ] **Step 3: Map implemented modules to documented responsibilities**

### Task 2: Identify concrete mismatches and stale artifacts

**Files:**
- Read: `src/aptitude_client/**`
- Read: `tests/**`
- Modify: `src/aptitude_client/**` only if a file is clearly obsolete
- Modify: `docs/**` only if a file is clearly obsolete

- [ ] **Step 1: Flag architecture mismatches with exact file references**
- [ ] **Step 2: Identify legacy or duplicate files that are no longer relevant**
- [ ] **Step 3: Remove only the clearly obsolete files**
- [ ] **Step 4: Recheck imports/tests after deletions**

### Task 3: Report the current state clearly

**Files:**
- Summarize findings from code and docs

- [ ] **Step 1: Produce findings ordered by severity**
- [ ] **Step 2: List assumptions and open decisions**
- [ ] **Step 3: Include any deletions performed and their rationale**
