# Canonical Architecture And Rules Docs Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create one canonical architecture document and one canonical rules document, then make the repository guidance require reading and following them before future implementation work.

**Architecture:** Consolidate the current spread of architecture and rules guidance into a small source-of-truth set. The new docs will explicitly define the required pre-change workflow: read the architecture, read the rules, update them when architecture changes, and verify every implementation against them.

**Tech Stack:** Markdown documentation, repo-internal guidance files, pytest smoke verification

---

### Task 1: Define the canonical documentation set

**Files:**
- Modify: `docs/Aptitude Client Architecture.md`
- Modify: `docs/Coding-Standards.md`
- Modify: `README.md`
- Review: `docs/Module-Responsibilities.md`
- Review: `docs/scope.md`

- [ ] **Step 1: Audit the current docs and decide which file becomes the canonical architecture doc**
- [ ] **Step 2: Audit the current docs and decide which file becomes the canonical rules doc**
- [ ] **Step 3: Decide which supporting docs stay as subordinate references rather than competing sources of truth**

### Task 2: Rewrite the architecture doc as the mandatory architectural source of truth

**Files:**
- Modify: `docs/Aptitude Client Architecture.md`

- [ ] **Step 1: Add an explicit “before any change” requirement to read this document**
- [ ] **Step 2: Define the core system model, pipelines, module ownership, and hard constraints**
- [ ] **Step 3: State how architecture changes must be reflected in this file before or with implementation**

### Task 3: Rewrite the rules doc as the mandatory implementation contract

**Files:**
- Modify: `docs/Coding-Standards.md`

- [ ] **Step 1: Add a required pre-implementation checklist**
- [ ] **Step 2: Add a required post-implementation verification checklist**
- [ ] **Step 3: Ensure rules explicitly bind future work to the architecture doc**

### Task 4: Rewire the repo guidance to point to the canonical pair

**Files:**
- Modify: `README.md`
- Modify: `docs/agent_contract_navigation.md`
- Modify: `.agents/agent.md`
- Modify: `.agents/memory/meta.md`
- Modify: `.agents/rules/repo.md`
- Modify: `.agents/skills/aptitude-codegen/SKILL.md`

- [ ] **Step 1: Make the canonical architecture and rules docs the first references everywhere**
- [ ] **Step 2: Remove or demote competing “source of truth” language elsewhere**
- [ ] **Step 3: Keep supporting docs aligned but subordinate**

### Task 5: Verify and summarize remaining discussion points

**Files:**
- Test: `tests/unit/shared/test_imports.py`
- Test: `tests/unit/interfaces/cli/test_help_surface.py`

- [ ] **Step 1: Run a stale-reference scan over the surviving canonical docs**
- [ ] **Step 2: Run the smoke verification commands**
- [ ] **Step 3: Summarize what is now canonical and what architectural questions still deserve review**
