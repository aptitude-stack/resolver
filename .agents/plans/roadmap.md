# Aptitude Client Roadmap

## Goal
Deliver a first working Aptitude client in Python through incremental,
testable milestones, starting from the current repository skeleton and ending
with a CLI-first exact-coordinate read flow against the existing server
runtime contract.

## Alignment Sources
- MVP scope and sequencing: `docs/MVP.md`
- Client/server ownership boundary: `docs/scope.md`
- Target architecture direction: `docs/Aptitude Client Architecture.md`
- Current package responsibilities: `docs/Module-Responsibilities.md`
- Agent contract and current repo reality: `docs/agent_contract_navigation.md`
- Runtime-tested server behavior: `docs/server-api-integration-notes.md`
- Repo workflow rules: `.agents/rules/repo.md`

## Platform Defaults
- Runtime baseline: Python `>=3.9` from `pyproject.toml`
- CLI framework: Typer
- DTO and settings models: Pydantic v2 + pydantic-settings
- HTTP client: sync `httpx`
- Tests: `pytest` with opt-in live integration tests against a running server
- Execution style: sync-first for the initial vertical slice

## Boundary Guardrails
- This roadmap covers `aptitude-client` only.
- All Aptitude Server communication belongs in `src/aptitude_client/registry/`.
- `discovery/` owns discovery-specific logic only; it is not the generic server adapter layer.
- The client owns CLI orchestration, transport anti-corruption, deterministic
  result shaping, and client-side error translation.
- The server remains the source of truth for exact immutable metadata and
  direct dependency declarations.
- The initial working slice is read-only.
- The initial CLI uses exact coordinates: `aptitude resolve <slug> --version <version>`.
- The initial implementation does not call `POST /discovery`.
- Where the checked-in OpenAPI differs from runtime-tested Postman behavior,
  the Postman-tested runtime contract is authoritative for the first client
  slice.
- No mock server is a roadmap deliverable. The product target is the existing server contract.
- Avoid speculative new top-level packages, but `registry/` is an approved core boundary of the real product architecture.

## Milestones
1. `01-client-foundation-and-runtime-skeleton.md`
2. `02-runtime-read-contract-hard-cut.md`
3. `03-registry-read-adapter.md`
4. `04-cli-exact-resolve-vertical-slice.md`
5. `05-discovery-and-name-based-ux-after-contract-alignment.md`

## Phase Mapping
- Foundation: milestone 01
- Contract freeze for the initial client slice: milestone 02
- Server read adapter implementation: milestone 03
- First end-to-end CLI flow: milestone 04
- Deferred discovery-driven UX and contract reconciliation follow-up:
  milestone 05

## Roadmap Rules
- Milestone numbering is append-only.
- Work on one active milestone plan at a time.
- Complete milestones 01-04 before starting milestone 05.
- Do not widen the initial slice to publish/admin, discovery UX, lockfiles,
  plugins, or execution planning before the exact-coordinate read flow works.
- If the server contract changes during implementation, update
  `docs/server-api-integration-notes.md` first and then revise the affected
  milestone plan instead of silently drifting.
