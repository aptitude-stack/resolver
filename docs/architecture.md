# Aptitude Resolver Architecture

## Status

This is the canonical architecture source of truth for `aptitude-resolver`.

Current internal hardening wave:

- test hardening
- hard policy CLI overrides
- cache and retry
- observability
- advanced governance

Explicitly out of scope for this wave:

- SDK
- MCP
- `latest` selection profile

Before any non-trivial change, feature, refactor, or new module:

1. read this file
2. read [RULES.md](rules.md)
3. identify the owning module before writing code

If the intended implementation changes the architecture, boundaries, or flow, update this file first or in the same change. Do not silently drift from it.

## System Overview

Aptitude is a client-side dependency and capability manager for AI skills.

The system is split into:

- **Server**: owns data-local work such as registry storage, immutable metadata, immutable artifacts, and indexed candidate retrieval
- **Client**: owns decision-local work such as intent interpretation, candidate selection, dependency solving, governance, locking, and execution planning

The server returns facts.
The client makes decisions.

## Core Architectural Law

Always enforce:

- Server = data-local work
- Client = decision-local work

The client must own:

- interpret user intent
- discover candidates
- choose versions
- select the final root
- resolve dependencies
- enforce governance
- generate a lock
- build the execution plan

The client must not:

- delegate final selection to the server
- delegate dependency solving to the server
- treat server ordering or advisory ranking as final truth
- execute from unlocked graph state once a lock exists

## Canonical Pipelines

### 1. Fresh Planning Flow

Use this when the input is a user request or query.

```text
User Request
-> Interface
-> Application Use Case
-> Discovery
-> Resolver
-> Governance
-> Lockfile
-> Execution Planning
-> Result or Materialization
```

This is the architecture behind:

- `install`
- hidden `resolve`

### 2. Lock Replay Flow

Use this when the input is an existing lockfile.

```text
Lockfile
-> Interface
-> Application Use Case
-> Lock Parse + Replay
-> Execution Planning
-> Materialization
```

This is the architecture behind:

- `sync --lock`

This is not a pipeline violation. It is the correct replay path once a lock already exists.

## Selection, Governance, And Integrity Contract

This section is the source of truth for how fresh planning chooses and validates a system.

If implementation differs from this contract, implementation must be updated. Do not "infer" this behavior from scattered code paths.

### Server-Owned Metadata

The server owns immutable facts attached to skills and versions.

For selection and governance, the client may rely on server-provided:

- `lifecycle_status`
- `trust_tier`
- `token_estimate`
- `content_size_bytes`
- checksum metadata for immutable content
- publisher or provenance metadata when the registry exposes it

The client may apply documented fallbacks for missing metadata, but it must not silently invent new trust or cost facts from heuristics.

### Client-Owned Policy

Policy is client-owned even when policy decisions use server-provided metadata.

Required policy source precedence:

1. per-request override
2. workspace or organization policy
3. client default policy

Current implementation status:

- client defaults exist
- programmatic override exists through `PolicyContext`
- workspace policy loading from `aptitude.toml` exists today
- organization-managed policy sources beyond workspace config are not implemented yet
- CLI per-request overrides exist for fresh planning only:
  - `--allow-trust`
  - `--allow-lifecycle`
  - `--max-tokens`
  - `--max-content-size`

Phase A per-request policy override semantics:

- these flags apply only to fresh planning commands
- they affect governance legality only, not selection preferences
- they do not apply to `sync --lock`
- workspace policy currently merges from workspace `aptitude.toml`
- current merge semantics are stricter-only:
  - allowed-value lists intersect with the effective base policy
  - numeric ceilings choose the stricter minimum
- CLI overrides may only make the effective policy stricter than the current base
- policy snapshot `source` should record `cli_override` when any of these flags are used

Phase 1 default client policy:

- `profile = "default"`
- `source = "client_default"`
- `allowed_lifecycle_statuses = ["published", "deprecated", "archived"]`
- `allowed_trust_tiers = ["verified", "internal", "untrusted"]`
- `max_token_estimate = null`
- `max_content_size_bytes = null`

These defaults are part of the contract. They must not be left implicit in code.

### Client-Owned Selection Preferences

Selection preferences are separate from hard policy.

Policy decides what is legal.
Selection preferences decide what is preferred among the remaining legal candidates.

Phase 1 `SelectionPreferences` defaults:

- `profile = "balanced"`
- `interaction_mode = "auto"`

Selection-preference source precedence:

1. CLI override
2. environment override
3. workspace config
4. user config
5. client default

Currently implemented selection-preference sources:

- CLI flags:
  - `--prefer`
  - `--interaction-mode`
- environment variables:
  - `APTITUDE_PREFER`
  - `APTITUDE_INTERACTION_MODE`
- workspace `aptitude.toml`
- user `aptitude.toml`

Supported phase 1 selection profiles:

- `balanced`
- `low-cost`
- `high-trust`

Explicitly deferred:

- `latest`
- broader workspace or organization policy merge semantics beyond the current fresh-planning CLI overrides

Supported phase 1 interaction modes:

- `auto`
- `always`
- `never`

Interaction rules:

- prompting is allowed only for root candidate ambiguity
- recursive dependency resolution must never prompt
- preference metadata may explain fresh planning decisions, but it must not become an execution dependency
- selection-preference source metadata may be stored for explainability, but execution must ignore it

### Missing Metadata Fallbacks

Missing selection metadata must be handled deterministically.

Phase 1 fallback rules:

- missing `trust_tier` is normalized to `untrusted` at the registry mapping boundary
- missing `token_estimate` is treated as `unknown`
- missing `content_size_bytes` is treated as `unknown`

Policy behavior for unknown resource values:

- if no ceiling is configured, unknown resource values do not cause policy failure
- if a ceiling is configured, unknown resource values fail closed during candidate policy and graph governance

Ranking behavior for unknown resource values:

- ranking may compare `token_estimate` or `content_size_bytes` only when both candidates define the value
- otherwise that ranking criterion is skipped and later tiebreakers apply

### Governance Runs In Two Phases

Fresh planning requires two distinct governance phases.

#### 1. Candidate Policy Phase

This phase runs after discovery has produced enriched candidates with selected versions, but before final ranking and final root selection.

This phase may only use rules that can be evaluated without graph expansion.

Phase 1 candidate-policy rules:

- allowed lifecycle states
- allowed trust tiers
- maximum `token_estimate`
- maximum `content_size_bytes`

Phase 1 outcome:

- candidates that fail are filtered out before ranking
- filtered candidates remain traceable

Phase 1 module handoff:

1. discovery returns candidate identities and intent
2. resolver chooses one concrete version per candidate
3. governance filters candidate-level policy compliance
4. discovery reranks only the surviving legal candidates
5. resolver selects the final root from that ranked legal set

#### 2. Graph Governance Phase

This phase runs after recursive dependency resolution and before lock generation.

This phase validates the full resolved graph and may block the entire result.

Phase 2 graph-governance responsibilities:

- enforce lifecycle and trust rules across all resolved nodes
- enforce resource ceilings across all resolved nodes
- enforce aggregate token and content-size ceilings across the resolved graph
- enforce future organization-specific rules
- enforce future cost constraints that depend on the graph, not just the root candidate

Current implementation status:

- candidate pre-filter governance exists today
- graph governance exists today
- lifecycle, trust, and resource-ceiling rules are implemented today
- aggregate graph token and content-size ceilings are implemented today

### Ranking Happens Only Among Policy-Compliant Candidates

Policy filters illegal candidates.
Ranking chooses the best candidate among the remaining legal candidates.

Deterministic ranking is profile-aware.

Shared relevance floor for all phase 1 profiles:

1. exact name match
2. exact slug match
3. runtime or language fit
4. stronger label, tag, and text relevance to the request

`balanced` profile:

1. shared relevance floor
2. higher trust tier
3. lower `token_estimate` when known
4. lower `content_size_bytes` when known
5. current-default preference and deterministic version quality
6. newer semantic version
7. newer publication timestamp
8. slug as the final stable tiebreak

`low-cost` profile:

1. shared relevance floor
2. lower `token_estimate` when known
3. lower `content_size_bytes` when known
4. higher trust tier
5. lifecycle quality
6. current-default preference and deterministic version quality
7. newer semantic version
8. newer publication timestamp
9. slug as the final stable tiebreak

`high-trust` profile:

1. shared relevance floor
2. higher trust tier
3. lifecycle quality
4. lower `token_estimate` when known
5. lower `content_size_bytes` when known
6. current-default preference and deterministic version quality
7. newer semantic version
8. newer publication timestamp
9. slug as the final stable tiebreak

Selection behavior:

- `auto` prompts only when the session can prompt and ambiguity remains; otherwise it selects the top-ranked legal candidate deterministically
- `always` prompts whenever ambiguity remains; if prompting is impossible, the client fails clearly instead of silently auto-picking
- `never` never prompts and always selects the top-ranked legal candidate deterministically
- interactive prompting shows only policy-compliant candidates, already ranked
- interactive candidate payloads may include additive selection details and short comparison reasons prepared by the core ranking flow; interfaces may render them, but must not recompute them
- graph governance does not silently "fallback" to another candidate unless the architecture is updated to say so explicitly

Current implementation status:

- deterministic profile-aware reranking exists today
- ranking pre-filters by candidate policy today
- explicit interaction modes are carried through the request and use-case flow today
- selection-preference precedence is merged in application composition today
- effective selection preferences are emitted in trace today
- final-selection explainability trace is emitted today
- automatic fallback to "next candidate if governance fails" is not part of the design

### Lock Must Explain Both Policy Inputs And Policy Outcomes

The lockfile must explain not only what was selected, but also which policy context governed that selection.

Required lock governance information:

- governance outcome entries for each rule evaluation
- a minimal policy snapshot describing the client policy used for the decision
- optional selection explainability metadata describing the chosen selection profile and interaction mode

Phase 1 minimal policy snapshot:

- policy version or profile identifier
- allowed lifecycle states
- allowed trust tiers
- maximum `token_estimate`
- maximum `content_size_bytes`
- maximum total `token_estimate`
- maximum total `content_size_bytes`

Current implementation status:

- governance outcomes are stored today
- minimal policy snapshot is stored today
- minimal selection explainability metadata is stored today

Phase 1 minimal selection explainability snapshot:

- selected selection profile
- effective interaction mode
- profile source
- interaction-mode source

Phase 1 policy snapshot JSON shape:

```json
{
  "policy": {
    "profile": "default",
    "source": "client_default",
    "allowed_lifecycle_statuses": ["published", "deprecated", "archived"],
    "allowed_trust_tiers": ["verified", "internal", "untrusted"],
    "max_token_estimate": null,
    "max_content_size_bytes": null
  }
}
```

`null` is explicit and means "no ceiling".

### Checksum Contract

Checksum semantics are explicit, not implicit.

Phase 1 checksum contract:

- the server publishes immutable content checksum metadata
- the client stores that checksum in domain models and in the lockfile
- the client recomputes and verifies the checksum during materialization
- checksum mismatch fails fast and stops materialization

Phase 1 canonical checksum fields:

- `content_checksum.algorithm`
- `content_checksum.digest`
- optional `content_checksum.size_bytes`

Phase 1 canonical algorithm:

- `sha256`

Phase 1 canonical typed error:

- `ContentChecksumMismatchError`

Phase 1 required error payload fields:

- `slug`
- `version`
- `algorithm`
- `expected_digest`
- `actual_digest`

Future algorithms may be added later, but not by silently changing the meaning of phase 1 data.

## Hard Constraints

Every implementation must preserve:

- deterministic behavior for identical logical inputs
- traceable decision-making
- strict module boundaries
- governance before lock generation in fresh planning flows
- lock as the single source of truth for execution

If a proposed change violates one of these, the design is wrong until proven otherwise.

## Current Package Map

```text
src/aptitude_resolver/
  application/
    dto/
    queries/
    use_cases/
  cache/
  discovery/
    intent/
    query_builder/
    reranking/
  domain/
    errors/
    models/
    policy/
    tracing/
  execution/
  governance/
  interfaces/
    cli/
  lockfile/
  registry/
  resolver/
    conflict/
    graph/
    normalizer/
    replay/
    solver/
    validation/
  shared/
    config/
    logging/
  telemetry/
```

Reserved but not yet implemented as top-level packages:

- `plugins/`
- additional interfaces such as `mcp/` and `sdk/`

These should be added only when they become real responsibilities.

## Dependency Direction

Allowed architectural direction:

- `interfaces -> application`
- `application -> domain | discovery | execution | governance | lockfile | registry | resolver | shared | telemetry`
- `cache -> shared`
- `discovery -> domain | shared`
- `governance -> domain`
- `lockfile -> domain`
- `execution -> domain | lockfile`
- `registry -> cache | domain | shared`
- `resolver -> domain | shared`
- `telemetry -> shared`

Important note:

- lower layers may depend on protocols or inputs supplied by application
- they must not import interface code or bypass the intended workflow

Forbidden:

- `domain -> application | discovery | execution | governance | interfaces | lockfile | registry | resolver`
- `interfaces -> discovery` for business-logic bypass
- `interfaces -> execution` for business-logic bypass
- `interfaces -> governance` for business-logic bypass
- `interfaces -> lockfile` for business-logic bypass
- `interfaces -> registry` for business-logic bypass
- `interfaces -> resolver` for business-logic bypass
- `shared -> application | discovery | execution | governance | lockfile | registry | resolver`

## Module Responsibilities

### interfaces/

Owns:

- external entrypoints
- input parsing
- interactive prompting
- output formatting
- exit behavior

Must not own:

- business rules
- final selection
- dependency solving
- governance logic
- registry transport

### application/

Owns:

- use-case orchestration
- workflow sequencing
- DTO boundaries
- handoff between discovery, resolver, governance, lockfile, and execution

Must not own:

- solver internals
- discovery internals
- raw transport details
- CLI formatting
- execution internals

### discovery/

Owns:

- request-intent interpretation
- discovery query construction
- candidate identity shaping
- non-final reranking

Must not own:

- final candidate selection
- dependency solving
- lock generation
- execution planning

### registry/

Owns:

- all Aptitude Server communication
- auth headers
- endpoint knowledge
- bounded transient retry at the transport boundary
- advisory caching of discovery results, immutable metadata, version lists, and content
- transport parsing
- transport error translation
- transport-to-domain mapping

Must not own:

- prompt interpretation
- client reranking policy
- dependency solving
- lock generation
- correctness-critical behavior that depends on cache state

### resolver/

Owns:

- candidate version selection
- final candidate selection
- dependency normalization
- dependency expansion
- graph construction
- conflict detection
- validation

Resolver behavior must be deterministic and explainable.

### governance/

Owns:

- policy evaluation before lock generation
- candidate-policy filtering before final ranking
- blocking invalid resolved systems

Current implementation:

- candidate-policy filtering before final ranking
- graph governance before lock generation
- lifecycle, trust, and resource-ceiling rules
- aggregate graph token and content-size ceilings

Planned expansion:

- organization-specific rules
- additional cost constraints that depend on graph-level context

### cache/

Owns:

- advisory disk-backed caches that improve performance without changing correctness
- cache key strategy for immutable content and transport reads

Must not own:

- policy decisions
- resolver behavior
- correctness-critical state

### telemetry/

Owns:

- additive timing collection for pipeline stages
- structured emission of observability events

Must not own:

- selection logic
- governance logic
- execution decisions

### lockfile/

Owns:

- lock schema
- deterministic serialization
- parsing
- replay validation
- policy snapshot and governance result durability

The lockfile is the execution source of truth.

### execution/

Owns:

- execution-plan construction from lock data
- artifact fetch planning
- checksum verification
- environment preparation
- materialization
- execution-owned debug artifacts

Execution must not depend on `ResolutionGraph`.
Execution must fail fast on checksum mismatch.

### domain/

Owns:

- entities
- value objects
- client-owned errors
- policy types
- tracing models

Must remain free of transport and CLI concerns.

### shared/

Owns:

- configuration loading
- logging setup
- generic low-business-meaning helpers

Must not hide feature-owned logic.

## Current Implemented User Surfaces

Public CLI:

- `install`
- `sync`

Hidden internal CLI:

- `resolve`

Normal user flow:

- `install`
- `sync --lock`

`resolve` is intentionally a preview/debug surface, not the public default flow.

## Architecture Change Protocol

Before adding a new capability, ask:

1. Which module owns it?
2. Does it belong to the fresh planning flow or the lock replay flow?
3. Does it affect determinism, traceability, or execution truth?
4. Does this file need to change first?

If the answer to `4` is yes, update this file in the same change. Do not leave architecture drift behind for "later".

## Decision Gate

Before considering a design acceptable, verify:

- Is the logic in the correct layer?
- Does the client still own the decision?
- Is the result deterministic?
- Is the decision traceable?
- Does execution still run from lock data only?

If any answer is no, the design is not complete.
