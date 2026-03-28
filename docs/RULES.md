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
5. if the work touches selection, governance, ranking, or checksums, read the "Selection, Governance, And Integrity Contract" in `ARCHITECTURE.md`
6. decide how determinism and traceability will be preserved

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

### 3. Keep selection and governance split explicit

Do not blur policy filtering, ranking, and graph validation into one hidden step.

Required behavior:

- candidate-policy rules that can be checked before graph expansion must run before final ranking and final root selection
- final graph governance must still run after resolution and before lock generation
- ranking must only compare policy-compliant candidates
- interaction mode must flow explicitly through request and use-case boundaries; do not hide it as an internal resolver assumption
- interaction behavior must be explicit via `auto`, `always`, or `never`
- `auto` may prompt only when the session can prompt and ambiguity remains
- `always` must fail clearly when prompting is required but unavailable
- `never` must choose the top-ranked policy-compliant candidate deterministically
- prompting must stay root-only and must never happen inside dependency resolution
- interactive mode must present only policy-compliant candidates
- explainability traces may describe effective selection preferences and winner-vs-runner-up reasoning, but they must stay additive
- governance failure after graph resolution must not silently fall through to another candidate unless the architecture is updated to require fallback behavior

### 4. Keep policy client-owned and metadata server-owned

Do not confuse metadata ownership with policy ownership.

Required behavior:

- trust, lifecycle, token estimate, content size, and checksum metadata come from the server
- allowed trust tiers, allowed lifecycle states, and resource ceilings are client policy
- selection profile and interaction mode are client-owned preferences, not hard legality rules
- policy precedence is:
  1. per-request override
  2. workspace or organization policy
  3. client default policy

Until external policy sources exist, document defaults explicitly and test them.

Phase 1 defaults and fallback behavior must be explicit in code and tests:

- `profile = "default"`
- `source = "client_default"`
- missing `trust_tier` normalizes to `untrusted`
- missing `token_estimate` and `content_size_bytes` are `unknown`
- unknown resource values fail closed only when the corresponding ceiling is configured

Phase 1 selection-preference defaults must be explicit in code and tests:

- `profile = "balanced"`
- `interaction_mode = "auto"`
- selection-preference precedence is:
  1. CLI override
  2. environment override
  3. workspace config
  4. user config
  5. client default
- supported profiles are:
  - `balanced`
  - `low-cost`
  - `high-trust`
- `latest` is explicitly deferred
- hard policy CLI flags such as `--max-tokens`, `--max-content-size`, and `--allow-trust` remain deferred

### 5. Keep determinism explicit

For the same logical inputs, the client should produce the same:

- selected candidate
- version choice
- dependency graph
- install order
- lockfile
- execution plan

When order matters, define the tie-break in code and tests.

This includes:

- candidate-policy filtering
- profile-aware ranking order among policy-compliant candidates
- stable missing-metadata fallbacks
- explicit policy defaults
- explicit selection-preference defaults

### 6. Keep decisions explainable

Decision-affecting logic should emit traceable evidence.

This includes:

- intent parsing
- candidate-policy filtering
- candidate reranking
- effective selection preferences
- version selection
- final selection
- dependency traversal order
- governance outcomes
- lock generation
- execution-plan generation
- checksum verification failures

Explainability-only lock metadata is allowed when it helps users understand fresh-planning behavior, but:

- it must remain clearly separate from nodes, edges, and install order
- parsing may preserve it
- execution must not require it

### 7. Keep checksum semantics explicit

Do not leave integrity behavior to assumption.

Required behavior:

- phase 1 checksum data uses `content_checksum.algorithm`, `content_checksum.digest`, and optional `content_checksum.size_bytes`
- phase 1 algorithm is `sha256`
- the server publishes checksum facts
- the client verifies checksum facts during materialization
- checksum mismatch must fail fast and surface as `ContentChecksumMismatchError`
- checksum mismatch payload must include `slug`, `version`, `algorithm`, `expected_digest`, and `actual_digest`

### 8. Keep docs synchronized

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
- enforce candidate-policy filtering before final root selection when the rule can be checked without graph expansion
- block invalid results explicitly
- keep the candidate-policy handoff explicit:
  - discovery returns candidates
  - resolver chooses candidate versions
  - governance filters legal candidates
  - discovery reranks the legal set
  - resolver performs final root selection

### lockfile/

- generate, serialize, parse, and replay the durable resolved-system artifact
- persist both governance outcomes and the minimal policy snapshot needed to explain the decision
- store `null` explicitly for unset ceilings in the policy snapshot

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
- `governance/`: candidate filtering, graph policy, and policy-failure behavior
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
- let graph governance stand in for candidate filtering when the rule could have run earlier
- keep competing source-of-truth docs alive
- add new top-level packages speculatively
- introduce dual execution paths
- treat preview flows as the public user contract without saying so explicitly

## Short Version

The working rule is:

read architecture, read rules, assign ownership, update docs if the architecture changed, implement in the correct layer, verify determinism and traceability, then claim completion.
