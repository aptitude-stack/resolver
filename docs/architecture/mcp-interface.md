# Aptitude MCP Interface Design

This document defines the current normative MCP interface shape for Aptitude.

## Scope

The MCP server gives agent hosts a local, standard way to use Aptitude.

It exposes:

- discovery and inspection
- deterministic resolve previews
- effective policy inspection
- fresh install materialization
- lock-driven sync materialization
- read-only resources for command and architecture context
- prompts that guide agents through common Aptitude workflows

The MCP server does not redefine resolver, governance, lockfile, registry, or execution behavior. Those remain owned by the existing application and lower layers.

## Entry And Transport

The public entrypoint is:

```bash
uvx aptitude-resolver mcp
```

The direct installed-tool entrypoint remains `aptitude-mcp`.

The v1 transport is local `stdio`. This is the right fit for local desktop and coding-agent clients such as Claude Desktop, Claude Code, Cursor, Windsurf-style clients, and MCP Inspector.

Stdio logging must never write to stdout. Anything diagnostic must go to stderr or existing structured logging paths so JSON-RPC messages are not corrupted.

Remote Streamable HTTP is deferred until Aptitude has a real deployment, authorization, and multi-client operating model.

## Tools

Read-only tools:

- `aptitude_search_skills`: discovery-only candidate search with pagination and `markdown`, `json`, or `toon` output
- `aptitude_inspect_skill`: selected skill metadata, available versions, and bounded content preview
- `aptitude_resolve_skill`: deterministic fresh planning with candidates, selected coordinate, graph, lockfile, execution plan, trace, and policy evaluations
- `aptitude_show_policy`: effective policy and configuration layers

Mutating tools:

- `aptitude_install_skill`: fresh planning plus local materialization into an explicit target path
- `aptitude_sync_lock`: lock replay plus local materialization into an explicit target path

Mutating tools must require explicit paths. They must not accept shell commands, execute arbitrary commands, or infer hidden write targets.

## Resources And Prompts

Resources:

- `aptitude://manifest`
- `aptitude://policy/effective`
- `aptitude://docs/architecture`
- `aptitude://docs/cli-interface`

Prompts:

- `aptitude_plan_install`
- `aptitude_compare_candidates`
- `aptitude_sync_from_lock`

Prompts are guidance only. They must not encode hidden business rules or bypass application behavior.

## Layering Rules

The MCP package lives under `src/aptitude_resolver/interfaces/mcp/`.

It may:

- parse and validate MCP inputs with Pydantic
- call application composition builders
- render DTOs as Markdown, JSON, or TOON
- expose MCP tool annotations and resources
- convert resolver-owned errors into actionable tool responses

It must not:

- implement resolver decisions
- query the registry directly
- recompute governance or ranking
- turn lock replay back into fresh planning
- hide feature logic in shared helpers

MCP currently wraps application use cases directly. A future SDK interface may become the shared programmatic facade, at which point MCP can delegate to that SDK without changing the resolver boundary.

## Safety

Tool annotations must match behavior:

- read-only tools set `readOnlyHint=true` and `destructiveHint=false`
- install and sync set `readOnlyHint=false`, `destructiveHint=true`, `idempotentHint=false`, and `openWorldHint=true`

The host application remains responsible for human approval, but Aptitude must still make mutating behavior obvious and require explicit filesystem targets.

## Verification Expectations

Relevant verification lives in:

- `tests/unit/interfaces/mcp/test_server.py`
- `tests/unit/interfaces/mcp/test_formatting.py`
- `tests/unit/interfaces/mcp/test_mcp_main.py`
- `tests/unit/shared/test_imports.py`

Changes to tools, resources, prompts, entrypoints, output formats, or annotations must update those tests in the same change.
