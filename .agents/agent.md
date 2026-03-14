# Aptitude Client Agent Contract

## General Idea
Aptitude Client is a Python-based client for interpreting skill requests,
discovering candidates, resolving dependencies deterministically, enforcing
client-side policies, and producing stable execution-oriented outputs.

## Source and Instruction Files
1. Client architecture source of truth: [`../docs/Aptitude Client Architecture.md`](../docs/Aptitude%20Client%20Architecture.md)
2. Client-server scope boundary source of truth: [`../docs/scope.md`](../docs/scope.md)
3. Repo operating rules: [`rules/repo.md`](rules/repo.md)
4. Stable repo facts: [`memory/meta.md`](memory/meta.md)
5. Additional implementation guidance:
   - [`../docs/Coding-Standards.md`](../docs/Coding-Standards.md) - coding rules, layering discipline, determinism, and testing expectations
   - [`../docs/Module-Responsibilities.md`](../docs/Module-Responsibilities.md) - package ownership and forbidden cross-layer responsibilities
   - [`../docs/Aptitude-Recommended-Libraries.md`](../docs/Aptitude-Recommended-Libraries.md) - recommended library choices by client module
   - [`../docs/agent_contract_navigation.md`](../docs/agent_contract_navigation.md) - task-based navigation guidance for agent workflows
6. Plan execution files: `plans/plan-XX-*.md` (append-only milestones)
7. Skills:
   - [`skills/architect-review`](skills/architect-review) - system design and architecture guidance
   - [`skills/apptitude-codegen-skill`](skills/apptitude-codegen-skill) - implementation workflow guidance aligned to current client structure
   - [`skills/python-patterns`](skills/python-patterns) - python design and implementation best practices
   - [`skills/python-testing`](skills/python-testing) - python testing and TDD best practices
   - [`skills/superpowers/using-superpowers`](skills/superpowers/using-superpowers) - startup skill invocation discipline
   - [`skills/superpowers/writing-plans`](skills/superpowers/writing-plans) - planning workflow before multi-step implementation
   - [`skills/superpowers/executing-plans`](skills/superpowers/executing-plans) - execution workflow for written plans
   - [`skills/superpowers/systematic-debugging`](skills/superpowers/systematic-debugging) - mandatory debugging workflow for bugs and failures
   - [`skills/superpowers/verification-before-completion`](skills/superpowers/verification-before-completion) - verify before claiming completion

If rules conflict, follow the highest item unless the client includes a newer explicit architecture decision.

## Collaboration and Learning (Mandatory)
- Keep Yonatan involved in non-trivial design and implementation decisions.
- Teach while building: explain relevant Python, client architecture, dependency
  resolution, and deterministic workflow concepts in short, concrete terms.
- For non-trivial decisions, present options with pros, cons, and impact when
  the tradeoff is still open.
- Keep changes incremental and reviewable with clear verification notes.

## Core Invariants
- Client behavior should stay deterministic for the same request, inputs, and
  pinned dependency or registry state.
- The client is responsible for interpretation, discovery, resolution, policy
  checks, and plan generation, not for server-side governance or artifact hosting.
- Keep client guidance client-focused; do not copy server assumptions unless the
  same capability exists in this repository.
- Prefer actual repository state over stale assumptions:
  - there is currently no `main.py`
  - `pyproject.toml` currently declares `uvicorn` only
  - `src/aptitude_client/` mostly defines module boundaries rather than
    implemented modules
- Preserve clear layering direction:
  - `interfaces/` should stay thin and contain no business logic
  - `application/` should orchestrate use cases
  - `domain/` should hold core models and rules
  - `discovery/` and `resolver/` should remain focused on their client responsibilities
  - `shared/` should contain cross-cutting utilities, not feature logic
- When the architecture document mentions future modules not present in the
  filesystem yet, treat them as design intent rather than current implementation fact.

## Documentation Discipline
- Keep `.agents/agent.md` aligned with the live repository structure and live skills.
- Update `.agents/memory/meta.md` when stable client facts change.
- Update `.agents/rules/repo.md` when workflow or repo rules change.
- When plan-driven work starts, create or update the relevant file under `.agents/plans/`.
- If skills are added, renamed, or removed, update the skills list in this file in the same change.
