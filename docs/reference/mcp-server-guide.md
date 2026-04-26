# Aptitude MCP Server Guide

This guide explains how to set up and use the Aptitude MCP server, what tools it exposes, why it is useful, and how it fits into the engineering design of Aptitude.

MCP stands for Model Context Protocol. It is a standard way for AI assistants and agent applications to call external tools, read resources, and use prompts through a consistent interface.

For Aptitude, MCP turns the resolver into an agent-facing package manager for AI skills.

## Why Use Aptitude Through MCP?

Aptitude already knows how to discover skills, rank candidates, resolve dependencies, enforce governance, generate lockfiles, and materialize skills locally.

The MCP server lets an AI assistant use those capabilities directly instead of asking the user to copy commands back and forth.

This is recommended because:

- the assistant can search and inspect skills before recommending one
- the assistant can preview the exact resolved graph and lockfile before installation
- the assistant can explain why a skill was selected using Aptitude trace data
- install and sync still go through Aptitude governance and lockfile rules
- filesystem-writing actions are explicit MCP tools with destructive annotations
- the assistant does not need to know registry internals or resolver internals

In short: MCP lets agents use Aptitude safely as a resolver, not as a pile of ad hoc shell commands.

## What You Need To Download

Required:

- Python `>=3.10`
- `uv`
- the Aptitude project checkout or the installed `aptitude-resolver` package
- Aptitude Server connection settings:
  - `APTITUDE_SERVER_BASE_URL`
  - `APTITUDE_READ_TOKEN`

Recommended for testing:

- Node.js
- MCP Inspector, run through `npx`

Optional MCP clients:

- Claude Desktop
- Claude Code
- Cursor or Windsurf-style MCP-capable coding clients
- any local MCP host that supports stdio servers

For local development in this repository:

```bash
uv sync --extra dev
```

This installs Aptitude and its development dependencies, including the MCP SDK and TOON formatter from `pyproject.toml`.

## New User Setup From Zero

Use this path if the user does not already have `aptitude-resolver`.

### Option A: Use the repository checkout

This is the best path before the MCP feature has been published to PyPI, or when a developer wants to test the current branch.

1. Install Python `>=3.10`.

Check:

```bash
python --version
```

2. Install `uv`.

Follow the official `uv` install instructions for the operating system, then check:

```bash
uv --version
```

3. Clone the Aptitude repository.

```bash
git clone <APTITUDE_REPOSITORY_URL>
cd aptitude-client
```

Replace `<APTITUDE_REPOSITORY_URL>` with the real repository URL used by the team.

4. Install Aptitude dependencies.

```bash
uv sync --extra dev
```

5. Configure the Aptitude Server connection.

Create a `.env` file in the repository root:

```env
APTITUDE_SERVER_BASE_URL=http://localhost:8000
APTITUDE_READ_TOKEN=reader-token
```

Replace these example values with the real Aptitude Server URL and read token. Without these values, registry-backed tools such as search, inspect, resolve, install, and sync cannot talk to the server.

6. Verify the CLI can start.

```bash
uv run aptitude --help
uv run aptitude policy show
```

7. Verify the MCP server entrypoint exists.

```bash
uv run aptitude-mcp
```

The command is expected to wait for MCP protocol messages. Stop it with `Ctrl+C` if running manually in a terminal.

8. Add the MCP server to the chosen MCP client.

Use this command/args pair:

```text
command: uv
args: --directory <ABSOLUTE_PATH_TO_APTITUDE_REPO> run aptitude-mcp
```

On this development machine, the path is:

```text
C:\Dev\apptitude-client\aptitude-client
```

### Option B: Use the published package

Use this path after a release containing the MCP server is published.

1. Install Python `>=3.10`.

2. Install `uv`.

3. Install Aptitude as a user tool.

```bash
uv tool install aptitude-resolver
```

4. Configure environment variables in the shell or operating-system environment:

```bash
export APTITUDE_SERVER_BASE_URL=https://your-aptitude-server.example
export APTITUDE_READ_TOKEN=your-read-token
```

On Windows PowerShell:

```powershell
$env:APTITUDE_SERVER_BASE_URL = "https://your-aptitude-server.example"
$env:APTITUDE_READ_TOKEN = "your-read-token"
```

5. Verify:

```bash
aptitude --help
aptitude policy show
```

6. Configure the MCP client:

```text
command: uvx
args: aptitude-resolver mcp
```

### What The User Needs From The Team

A new user needs these pieces of information from the Aptitude team or server operator:

- the repository URL or the released package name
- the Aptitude Server base URL
- a read token for the server
- the recommended MCP client
- the target directory policy for installs, if the organization has one

If the user only wants to inspect the local policy, the server token is less important. If the user wants discovery, resolve, install, or sync, the server connection is required.

## Starting The MCP Server

From this repository:

```bash
uv run aptitude-mcp
```

The server uses local `stdio` transport. That means an MCP client starts Aptitude as a subprocess and communicates with it over standard input and output.

Do not run `aptitude-mcp` directly in a normal terminal expecting a human UI. It is meant to be launched by an MCP host.

## MCP Client Configuration

For clients that accept a JSON MCP configuration and should run the published PyPI package locally, use:

```json
{
  "mcpServers": {
    "aptitude": {
      "command": "uvx",
      "args": [
        "aptitude-resolver",
        "mcp"
      ],
      "env": {
        "APTITUDE_SERVER_BASE_URL": "http://localhost:8000",
        "APTITUDE_READ_TOKEN": "your-local-read-token"
      }
    }
  }
}
```

For clients that use command and args fields:

```text
command: uvx
args: aptitude-resolver mcp
```

If Aptitude is installed as a tool or package, the command can be simplified to the direct MCP entrypoint:

```text
command: aptitude-mcp
args:
```

## Testing With MCP Inspector

Run:

```bash
npx -y @modelcontextprotocol/inspector uv --directory C:\Dev\apptitude-client\aptitude-client run aptitude-mcp
```

On Windows PowerShell, `npx.ps1` may be blocked by execution policy. In that case use:

```powershell
npx.cmd -y @modelcontextprotocol/inspector uv --directory C:\Dev\apptitude-client\aptitude-client run aptitude-mcp
```

MCP Inspector is an interactive developer tool. It may keep running instead of exiting like a test command.

## Available Tools

### `aptitude_search_skills`

Searches for skill candidates by natural-language query.

Use it when:

- the assistant needs to find relevant skills
- the user does not know the exact slug
- the assistant needs a ranked candidate list before resolving

Key inputs:

- `query`
- `limit`
- `offset`
- `response_format`: `markdown`, `json`, or `toon`

Behavior:

- read-only
- paginated
- delegates to Aptitude discovery and ranking

### `aptitude_inspect_skill`

Inspects one selected skill.

Use it when:

- the assistant needs metadata before recommending installation
- the assistant needs available versions
- the assistant needs a bounded content preview

Key inputs:

- `query`
- `version`
- `select_slug`
- `preview_char_limit`
- `response_format`

Behavior:

- read-only
- may require `select_slug` if a query has multiple candidates
- does not resolve a dependency graph

### `aptitude_resolve_skill`

Resolves a query into a deterministic plan without materializing files.

Use it when:

- the assistant needs to preview what would be installed
- the user wants to review the lockfile or dependency graph
- the assistant needs explainability and governance results

Key inputs:

- `query`
- `version`
- `select_slug`
- policy overrides
- `response_format`

Behavior:

- read-only
- produces graph, lockfile, execution plan, trace, and policy evaluations
- follows the same fresh-planning path as the CLI resolve flow

### `aptitude_show_policy`

Shows the effective local policy and config layers.

Use it when:

- an install or resolve result seems restrictive
- the assistant needs to explain why candidates were rejected
- the user wants to understand workspace policy

Key inputs:

- `cwd`
- `response_format`

Behavior:

- read-only
- does not query registry data

### `aptitude_install_skill`

Resolves and materializes a skill into an explicit local target directory.

Use it when:

- the user has approved installation
- the assistant has already inspected or resolved the plan
- the target directory is known

Key inputs:

- `query`
- `target`
- `version`
- `select_slug`
- policy overrides
- `response_format`

Behavior:

- writes to the local filesystem
- annotated as destructive
- requires explicit `target`
- still goes through discovery, resolver, governance, lock generation, and execution planning

### `aptitude_sync_lock`

Materializes an existing Aptitude lockfile.

Use it when:

- the user already has a lockfile
- the assistant should reproduce a locked skill environment
- no fresh discovery or dependency solving should happen

Key inputs:

- `lock_path`
- `target`
- `response_format`

Behavior:

- writes to the local filesystem
- annotated as destructive
- requires explicit `lock_path` and `target`
- follows lock replay, not fresh planning

## Available Resources

The server exposes these read-only resources:

- `aptitude://manifest`
- `aptitude://policy/effective`
- `aptitude://docs/architecture`
- `aptitude://docs/cli-interface`

These help an assistant understand Aptitude without scraping files manually.

## Available Prompts

The server exposes these prompts:

- `aptitude_plan_install`
- `aptitude_compare_candidates`
- `aptitude_sync_from_lock`

Prompts are guidance for the MCP client. They do not bypass Aptitude logic.

## Recommended Agent Workflow

For a fresh install:

```text
user request
-> aptitude_search_skills
-> aptitude_inspect_skill for likely candidates
-> aptitude_resolve_skill
-> user reviews selected coordinate, lockfile, and plan
-> aptitude_install_skill with explicit target
```

For lock replay:

```text
user provides lockfile and target
-> aptitude_sync_lock
```

For troubleshooting:

```text
unexpected result
-> aptitude_show_policy
-> inspect trace from resolve/search output
-> adjust query, select_slug, or policy inputs
```

## Engineering Explanation

Aptitude is intentionally layered:

```text
interfaces -> application -> discovery/resolution/governance/lockfile/execution/registry
```

The MCP server lives in `interfaces/mcp`. It is an adapter layer, not a new resolver.

It owns:

- MCP tool registration
- Pydantic input validation
- response formatting
- MCP annotations
- resources and prompts
- conversion of resolver errors into agent-readable messages

It does not own:

- candidate selection
- dependency solving
- governance decisions
- registry transport
- lockfile semantics
- materialization rules

That design matters because the same rules apply whether the user works through CLI, MCP, or a future SDK. MCP does not create a shortcut around the resolver.

## Why `stdio` For Version 1?

The first Aptitude MCP server is local and uses `stdio`.

This is the recommended v1 transport because:

- Aptitude is currently a local resolver and materializer
- MCP clients commonly launch local stdio tools as subprocesses
- no HTTP server, port management, auth server, or deployment layer is needed
- filesystem-writing tools remain local to the user machine
- the transport is simple to test with MCP Inspector

Remote Streamable HTTP should be considered later if Aptitude needs multi-client access, remote hosting, OAuth-style authorization, or centralized organizational services.

## Why Use The Official Python MCP SDK?

Aptitude is a Python project and already uses Pydantic DTOs.

The official MCP Python SDK is a good fit because:

- it provides `FastMCP`, a concise server API
- tool schemas are generated from typed functions and Pydantic models
- it supports tools, resources, prompts, stdio, and Streamable HTTP
- it keeps the implementation close to the MCP protocol
- it avoids building protocol plumbing manually

The project baseline is Python `>=3.10` so the MCP SDK can be used directly.

## Why Support TOON?

Aptitude outputs can be large: candidates, traces, graphs, lockfiles, and execution plans.

The MCP server supports:

- `markdown` for readable assistant responses
- `json` for exact structured data
- `toon` for compact structured output

TOON is useful when an agent needs structure but should spend fewer tokens than full JSON would require.

## Safety Notes

Read-only tools are annotated as read-only and non-destructive.

Install and sync are annotated as destructive because they write files. They require explicit paths and should be called only after the user understands the target and intended result.

The host application may add its own approval prompts, but the server itself still makes mutating operations explicit.

## Troubleshooting

If the MCP client cannot start the server:

- run `uv sync --extra dev`
- check that Python is `>=3.10`
- check that `uv run aptitude-mcp` works when launched by a client
- use MCP Inspector for development

If Inspector does not start from PowerShell:

- use `npx.cmd` instead of `npx`
- check Node.js is installed
- check PowerShell execution policy if using `npx.ps1`

If Aptitude tools return configuration errors:

- run `aptitude policy show`
- check required environment variables
- check workspace `aptitude.toml`
- inspect `aptitude://policy/effective`

If install or sync fails:

- verify the target path
- verify the lockfile path for sync
- inspect the resolver or materialization error
- retry only after understanding the failed step
