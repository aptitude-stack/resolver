# Agent Repo Rules

This file is for agent workflow only. Canonical architecture and implementation rules live under `../docs/`.

## Required Canonical Reads

Before non-trivial implementation work, read:

1. `../docs/architecture/system-overview.md`
2. `../docs/architecture/decision-rules.md`
3. `../docs/architecture/selection-and-governance.md` when the change touches planning, policy, governance, locking, or checksums
4. `../docs/reference/archive-artifact-materialization.md` when the change touches artifact fetching, archive extraction, materialization concurrency, or install/sync payload handling

## Agent-Specific Rules

- Treat `docs/` as canonical and `.agents/` as derivative.
- Keep `.agents/memory/meta.md` brief and factual.
- Do not treat `.agents/plans/` as current architecture.
- Update agent docs in the same change when product identity, package layout, or doc entrypoints change.

## Naming And Planning

- Use `kebab-case` for new filenames and plan slugs unless a tool requires something else.
- Save new plan files under `.agents/plans/`.
- Treat historical plans as history, not current guidance.
- When planning Python changes, use [`$python-testing`](../skills/python-testing/SKILL.md) to ensure the plan includes adding or updating tests.
