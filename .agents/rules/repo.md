# Repo Rules

## Naming Convention

- Use `kebab-case` for new filenames, rule identifiers, and plan slugs unless a tool requires a different format.

## Planning And Execution

- Save plan files under `.agents/plans/`.
- Use date-based or otherwise descriptive filenames; do not rely on the old `plan-XX-*` convention.
- Treat historical plan files as work history, not as the current architecture source of truth.

## TDD Workflow

- Follow RED -> GREEN -> REFACTOR for non-trivial changes.
- Write or update failing tests first for new behavior when practical.
- Implement the minimal change to pass tests.
- Refactor only with tests green and behavior preserved.
- Include happy-path and failure-path coverage.

## Documentation Guidelines

- Keep docs concise, concrete, and aligned with current behavior.
- Before any non-trivial implementation, read:
  - `docs/ARCHITECTURE.md`
  - `docs/RULES.md`
- Update these files when relevant behavior or boundaries change:
  - `docs/ARCHITECTURE.md`
  - `docs/RULES.md`
  - `README.md`
  - `.agents/memory/meta.md`
- Historical milestone plans under `.agents/plans/` do not need retroactive rewrites unless they are being actively reused.
- Document deterministic rules explicitly: ordering, tie-breakers, governance precedence, and lock-driven execution assumptions.
