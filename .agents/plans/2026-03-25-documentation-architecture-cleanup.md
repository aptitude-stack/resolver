# Documentation Architecture Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the repository documentation back in sync with the current Aptitude Resolver architecture, delete clearly obsolete documents, and preserve any architecture-relevant disagreements for human review instead of silently overwriting them.

**Architecture:** Audit every top-level project document against the current implementation, classify each document as keep/update, delete, or discuss, then apply the minimal doc edits needed to leave one coherent and current documentation set. Keep runtime and architecture truth aligned with the implemented lock-driven, client-owned decision pipeline.

**Tech Stack:** Markdown docs, Python codebase inspection, pytest verification

---

### Task 1: Inventory and classify documents

**Files:**
- Review: `README.md`
- Review: `docs/*.md`
- Review: `docs/openapi/*`

- [ ] Read each current document and note whether it is current, stale-but-useful, or obsolete.
- [ ] Compare major architecture claims to current code in `src/aptitude_client/`.
- [ ] Mark any document whose claims may still be architecturally valid for human review instead of deletion.

### Task 2: Remove clearly obsolete documents

**Files:**
- Delete: any doc that is fully superseded and misleading

- [ ] Delete only documents that are no longer relevant and add no unique value.
- [ ] Avoid deleting documents that still contain important architecture intent unless that intent is captured elsewhere in updated form.

### Task 3: Update authoritative docs

**Files:**
- Modify: `README.md`
- Modify: `docs/Aptitude Client Architecture.md`
- Modify: `docs/Module-Responsibilities.md`
- Modify: other current docs that remain authoritative after audit

- [ ] Update the surviving docs to match the implemented module boundaries and lock-driven flow.
- [ ] Ensure the docs distinguish fresh planning flows from lock-replay sync flows.
- [ ] Remove stale endpoint descriptions, package structure claims, and outdated MVP limitations.

### Task 4: Preserve unresolved architecture questions

**Files:**
- Modify: best-fit surviving architecture doc or `README.md`

- [ ] Record any important doc-vs-code disagreement that still deserves discussion instead of silently “fixing” it away.
- [ ] Keep these notes concise and explicit so they can drive the next architecture pass.

### Task 5: Verify and summarize

**Files:**
- Test: documentation references and import smoke tests as needed

- [ ] Run targeted verification to ensure no broken assumptions were introduced by doc cleanup.
- [ ] Summarize what was deleted, what was updated, and what still needs a product/architecture decision.
