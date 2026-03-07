# Aptitude Scope: Repository vs Client

## Purpose

This document defines the hard boundary between `aptitude-repository` and `aptitude-client` so responsibilities do not overlap.

## Maven Analogy

- `aptitude-repository` = Maven Artifactory (authoritative package/metadata/graph source).
- `aptitude-client` = Maven Builder (client-facing orchestrator that consumes packages and builds execution plans).

## Ownership Matrix

| Capability | Repository Owner | Client Owner | Notes |
| --- | --- | --- | --- |
| Skill artifact storage (immutable versions) | Yes | No | Client consumes only |
| Upload / publish workflow | Yes | No | Includes validation and provenance |
| Download artifact / bundle APIs | Yes | No | Client calls these APIs |
| Dependency/conflict/overlap graph source of truth | Yes | No | Client may post-process but not persist authority |
| Metadata index and evaluation signals | Yes | No | Client reads signals |
| Optional RAG index for retrieval hints | Yes (optional) | No | Advisory signal only |
| Deterministic dependency resolution contract | Yes | Partial | Client can request, not redefine |
| Prompt/tool-call interface (MCP/CLI) | No | Yes | Primary user entrypoint |
| Plugin machine (security scanner, overlap scorer, policy hooks) | No | Yes | Extensible runtime behavior |
| Runtime execution planning | No | Yes | Builds executable plan from resolved bundle |
| Governance policy enforcement at source | Yes | Partial | Client can add stricter local gates |
| Audit of repository lifecycle events | Yes | No | Publish/deprecate/archive/resolve in repository |
| Request trace across plugins/runtime | No | Yes | Client trace and diagnostics |

## System Contract (Request Flow)

1. Runtime caller sends tool call + prompt to the client (`MCP` or `CLI`).
2. Client normalizes request and asks repository for deterministic resolution.
3. Repository returns `ResolvedBundle` + `ResolutionReport` (+ optional retrieval hints).
4. Client executes plugin chain (security scan, overlap scoring, policy checks).
5. Client builds execution plan and returns output/trace to the runtime caller.
6. Client never writes directly to repository DB; all interaction is API-based.

## API and Data Contract

- Repository must expose:
  - `POST /skills/publish`
  - `GET /skills/{id}/{version}`
  - `POST /resolve`
  - `GET /bundles/{bundle_id}` (or equivalent artifact download)
  - `GET /reports/{resolution_id}`
- Client must expose:
  - MCP tool endpoint: `resolve_and_plan`
  - CLI command: `aptitude resolve "<prompt>"`
  - Structured output: `bundle_hash`, selected skills, plugin decisions, execution plan, trace ID

## Boundary Rules (Hard)

- Client cannot mutate skill artifacts, metadata authority, or dependency graph source-of-truth.
- Repository cannot execute runtime plugin chains or user prompt orchestration.
- Any overlap-scoring logic that changes final runtime selection must be recorded in client trace output.
- Deterministic package selection rules live in repository policy; client-specific filtering must be additive and explicit.

## Non-Goals

- Building a monolith that combines repository persistence and client runtime in one deployable.
- Letting plugin behavior silently override repository governance decisions.
- Making optional RAG retrieval a mandatory dependency for MVP resolution.

## Assumptions to Validate

- Initial target scale: 10k skills, 100-200 skill bundle upper bound.
- Client plugin budget target: <= 150 ms median overhead per plugin.
- RAG remains disabled by default and enabled only after benchmark validation.
