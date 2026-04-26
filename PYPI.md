# Aptitude Resolver

Aptitude Resolver is a deterministic, package-manager-style resolver for AI skills.

It turns a human request for a skill into a governed install plan: discovery, candidate selection, dependency resolution, policy checks, lockfile generation, and local materialization.

The resolver is the client-side half of Aptitude:

- Aptitude Server owns registry data, metadata, immutable artifacts, and discovery indexes.
- Aptitude Resolver owns intent handling, candidate selection, dependency solving, governance, lock generation, and execution planning.

## Install

Install the published package as a CLI tool:

```bash
uv tool install aptitude-resolver
aptitude --help
```

Run it without a persistent install:

```bash
uvx aptitude-resolver --help
```

The package installs these console commands:

- `aptitude`
- `aptitude-resolver`
- `aptitude-mcp`

`aptitude` is the command most users should run.
For MCP hosts that should launch the published package without a persistent install, use `uvx aptitude-resolver mcp`.

## Configure Registry Access

Registry-backed commands need an Aptitude Server URL and read token:

```bash
export APTITUDE_SERVER_BASE_URL=https://your-aptitude-server.example
export APTITUDE_READ_TOKEN=your-read-token
```

For local development against the default server:

```bash
export APTITUDE_SERVER_BASE_URL=http://localhost:8000
export APTITUDE_READ_TOKEN=reader-token
```

`aptitude policy show` can still inspect local policy without contacting the registry.

## Usage

Launch the install-first wizard:

```bash
aptitude
```

Install a skill by query:

```bash
aptitude install "Postman Primary Skill"
```

Inspect effective local policy and config layers:

```bash
aptitude policy show
```

Replay an existing lockfile:

```bash
aptitude sync --lock aptitude.lock.json
```

Show the full command and flag surface:

```bash
aptitude manifest
```

## MCP Server

Aptitude ships a local stdio MCP server for agents and MCP-compatible apps. The recommended MCP host configuration runs the published PyPI package locally through `uvx`:

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

The MCP server process still runs locally. `uvx` only resolves the published package and starts its `mcp` command over stdio.

The MCP server exposes tools for search, inspect, resolve, policy inspection, install, and lock sync. Mutating tools require explicit filesystem targets.

If Aptitude is already installed as a persistent tool, MCP hosts can also use the direct executable:

```json
{
  "mcpServers": {
    "aptitude": {
      "command": "aptitude-mcp",
      "args": [],
      "env": {
        "APTITUDE_SERVER_BASE_URL": "http://localhost:8000",
        "APTITUDE_READ_TOKEN": "your-local-read-token"
      }
    }
  }
}
```

Replace `APTITUDE_READ_TOKEN` with a token accepted by the target Aptitude Server.

## What Works Today

- discovery-backed query resolution
- candidate version selection
- recursive dependency graph resolution
- policy filtering and graph governance
- lockfile generation and replay
- archive-based skill materialization from verified `tar.zst` artifacts
- local config loading from `aptitude.toml`
- CLI and MCP interfaces

## Source

Source and contributor documentation live in the project repository:

https://github.com/aptitude-stack/resolver
