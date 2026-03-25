# Aptitude Client Rules

## Status

This is the canonical implementation rules document for `aptitude-client`.

Before any non-trivial implementation work:

1. read [ARCHITECTURE.md](ARCHITECTURE.md)
2. read this file
3. apply the pre-change checklist below

These rules are hard constraints, not suggestions.

## Mandatory Workflow For Every Future Change

### Before writing code

You must:

1. identify the owning module
2. identify whether the work belongs to fresh planning or lock replay
3. check whether the architecture document already covers the intended behavior
4. if not, update `ARCHITECTURE.md` first or in the same change
5. decide how determinism and traceability will be preserved

### While implementing

You must:

1. place logic only in the owning layer
2. keep interfaces thin
3. keep application orchestration-focused
4. keep discovery from doing final selection
5. keep execution lock-driven
6. add or maintain trace points for decision-affecting logic

### Before claiming completion

You must verify:

1. module ownership is still correct
2. the flow still matches the architecture
3. the behavior is deterministic
4. the decision path is traceable
5. the relevant docs were updated if behavior or boundaries changed
6. fresh verification commands succeeded

If any answer is no, the task is not complete.

## Hard Implementation Rules

### 1. Keep layers strict

Do not:

- put business logic in CLI handlers
- put solver logic in application
- let discovery do final selection
- let execution re-resolve dependencies
- hide feature logic in `shared/`

### 2. Keep execution lock-driven

Execution must operate from lock data only.

Do not:

- rebuild execution order from an unlocked graph during materialization
- treat `ResolutionGraph` as the execution source of truth
- require discovery or resolver during `sync --lock`

### 3. Keep determinism explicit

For the same logical inputs, the client should produce the same:

- selected candidate
- version choice
- dependency graph
- install order
- lockfile
- execution plan

When order matters, define the tie-break in code and tests.

### 4. Keep decisions explainable

Decision-affecting logic should emit traceable evidence.

This includes:

- intent parsing
- candidate reranking
- version selection
- final selection
- dependency traversal order
- governance outcomes
- lock generation
- execution-plan generation

### 5. Keep docs synchronized

When behavior or boundaries change, update the canonical docs in the same change:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [RULES.md](RULES.md)

Update supporting repo guidance as needed:

- [../README.md](../README.md)
- [../.agents/agent.md](../.agents/agent.md)
- [../.agents/memory/meta.md](../.agents/memory/meta.md)
- [../.agents/rules/repo.md](../.agents/rules/repo.md)
- [../.agents/skills/apptitude-codegen-skill/SKILL.md](../.agents/skills/apptitude-codegen-skill/SKILL.md)

Do not postpone documentation synchronization.

## Layer Rules

### interfaces/

- parse input
- prompt when needed
- format output
- set exit behavior

Must not own business logic.

### application/

- orchestrate use cases
- map DTO boundaries
- sequence discovery, resolver, governance, lockfile, and execution

Must not own solving internals.

### discovery/

- interpret requests
- build discovery queries
- shape and rerank candidate sets

Must not choose the final candidate.

### registry/

- own server transport
- map transport to client-owned models
- translate transport errors

Must not own discovery policy or resolver logic.

### resolver/

- own deterministic version and graph logic
- validate resolved outcomes

Must remain explainable and deterministic.

### governance/

- enforce policy before locking
- block invalid results explicitly

### lockfile/

- generate, serialize, parse, and replay the durable resolved-system artifact

### execution/

- consume lock data only
- build execution plans
- verify checksums
- materialize locked systems

### shared/

- utilities only
- no hidden feature workflows

## Testing Rules

Every non-trivial change should add or update:

- happy-path coverage
- failure-path coverage
- determinism coverage where ordering or selection matters

Layer emphasis:

- `application/`: orchestration and DTO shaping
- `discovery/`: intent and reranking
- `registry/`: server-boundary behavior
- `resolver/`: version choice, traversal, validation, conflicts
- `lockfile/`: serialize/parse/replay correctness
- `execution/`: lock-driven planning and materialization

Prefer live integration tests for the real registry boundary when practical. Use small in-process fakes for higher layers.

## Documentation And Review Gate

Before merging or calling work complete, ask:

1. Did I read `ARCHITECTURE.md` before implementing?
2. Did I keep the logic in the correct module?
3. If the architecture changed, did I update `ARCHITECTURE.md`?
4. If the implementation rules changed, did I update `RULES.md`?
5. Do the tests or verification commands prove the claimed behavior?

If any answer is no, stop and fix that first.

## Anti-Patterns

Do not:

- trust server ordering as final client choice
- keep competing source-of-truth docs alive
- add new top-level packages speculatively
- introduce dual execution paths
- treat preview flows as the public user contract without saying so explicitly

## Short Version

The working rule is:

read architecture, read rules, assign ownership, update docs if the architecture changed, implement in the correct layer, verify determinism and traceability, then claim completion.
