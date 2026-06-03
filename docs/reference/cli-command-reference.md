# CLI Command Reference

This document lists the current Aptitude CLI surface exactly as a user can invoke it.

Examples use the installed command name:

```bash
aptitude ...
```

The same surface is also available through:

```bash
uv run aptitude ...
py -3 -m aptitude_resolver ...
```

## Required Environment

Fresh-planning and registry-backed commands use the public Aptitude registry by default and require:

- `APTITUDE_READ_TOKEN`

Set `APTITUDE_SERVER_BASE_URL` only to override the public registry, such as for local development or a self-hosted registry.

These commands need registry access:

- `aptitude search`
- `aptitude inspect`
- `aptitude install`
- `aptitude resolve`
- `aptitude sync --lock ...`

These commands do not require registry access:

- `aptitude policy show`
- `aptitude manifest`

`aptitude sync --lock ...` replays an existing lockfile without discovery or dependency solving, but it still needs registry access to download the locked skill artifacts unless those artifacts are already served by an equivalent configured registry/cache path.

## Root Command

```bash
aptitude
aptitude --help
aptitude --version
```

Behavior:

- `aptitude` with no arguments opens the install-first wizard
- `--help` shows root help
- `--version` prints the installed CLI version

## Search

```bash
aptitude search QUERY
```

Flags:

- `--prefer TEXT`
- `--allow-trust TEXT`
- `--allow-lifecycle TEXT`
- `--max-tokens INTEGER`
- `--max-content-size INTEGER`
- `--json`
- `--help`

Examples:

```bash
aptitude search "Documentation Writing"
aptitude search "Postman" --prefer high-trust
aptitude search "Postman" --allow-trust verified,internal --json
uvx aptitude-resolver search "Documentation Writing"
```

## Inspect

```bash
aptitude inspect QUERY
```

Flags:

- `--version TEXT`
- `--select-slug TEXT`
- `--prefer TEXT`
- `--interaction-mode TEXT`
- `--allow-trust TEXT`
- `--allow-lifecycle TEXT`
- `--max-tokens INTEGER`
- `--max-content-size INTEGER`
- `--preview-chars INTEGER`
- `--json`
- `--help`

Examples:

```bash
aptitude inspect "Documentation Writing"
aptitude inspect "Postman" --select-slug postman-primary
aptitude inspect "Postman" --preview-chars 1200 --json
uvx aptitude-resolver inspect "Documentation Writing"
```

## Install

```bash
aptitude install [QUERY]
```

Flags:

- `--version TEXT`
- `--select-slug TEXT`
- `--prefer TEXT`
- `--interaction-mode TEXT`
- `--allow-trust TEXT`
- `--allow-lifecycle TEXT`
- `--max-tokens INTEGER`
- `--max-content-size INTEGER`
- `--agent TEXT`
- `--scope TEXT`
- `--global`
- `--export-root PATH`
- `--json`
- `--help`

Examples:

```bash
aptitude install "Postman Primary Skill"
aptitude install "Postman" --interaction-mode always
aptitude install "Postman Primary Skill" --prefer low-cost
aptitude install "Postman" --select-slug postman-primary
aptitude install "Postman" --allow-trust verified,internal
aptitude install "Postman" --allow-lifecycle published
aptitude install "Postman" --max-tokens 500 --max-content-size 2048
aptitude install "Postman" --agent codex --scope project
aptitude install "Postman" --agent claude-code --global
aptitude install "Postman" --agent "*" --scope project
aptitude install "Postman" --agent codex --scope custom --export-root C:\skills
aptitude install "Postman Primary Skill" --json
```

By default, `install` exports agent-facing skill packages to the selected agent root and keeps Aptitude bookkeeping outside the repository. On Windows, registry artifact cache and install state live under `%LOCALAPPDATA%\aptitude\cache` and `%LOCALAPPDATA%\aptitude\state`.

## Sync

```bash
aptitude sync --lock PATH
```

Flags:

- `--lock PATH`
- `--target PATH`
- `--json`
- `--help`

Examples:

```bash
aptitude sync --lock aptitude.lock.json
aptitude sync --lock aptitude.lock.json --target demo_postman
aptitude sync --lock aptitude.lock.json --json
```

## Policy

```bash
aptitude policy --help
aptitude policy show
aptitude policy show --json
```

`policy` is a command group. In the current surface, the public subcommand is:

- `show`

Flags for `policy show`:

- `--json`
- `--help`

What it reports:

- effective selection preferences
- effective policy
- contributing config layers
- merge semantics

## Manifest

```bash
aptitude manifest
```

Purpose:

- prints the complete CLI capability map

## Hidden/Internal Preview Command

```bash
aptitude resolve QUERY
```

This is the advanced preview/debug command. It follows the fresh-planning path but stops after planning and prints structured JSON instead of materializing skills.

Flags:

- `--version TEXT`
- `--select-slug TEXT`
- `--prefer TEXT`
- `--interaction-mode TEXT`
- `--allow-trust TEXT`
- `--allow-lifecycle TEXT`
- `--max-tokens INTEGER`
- `--max-content-size INTEGER`
- `--help`

Examples:

```bash
aptitude resolve "Postman Primary Skill"
aptitude resolve "Postman" --interaction-mode never
aptitude resolve "Postman Primary Skill" --prefer high-trust
aptitude resolve "Postman Primary Skill" --allow-trust verified,internal
```

## Allowed Values

### `--prefer`

- `balanced`
- `low-cost`
- `high-trust`

### `--interaction-mode`

- `auto`
- `always`
- `never`

## Short Command Map

```text
aptitude
aptitude --help
aptitude --version

aptitude search QUERY [flags]
aptitude inspect QUERY [flags]
aptitude install [QUERY] [flags]
aptitude sync --lock PATH [flags]
aptitude policy show [--json]
aptitude manifest

aptitude resolve QUERY [flags]
```

## Current Note

`aptitude manifest` is part of the supported CLI surface. In terminals that cannot print box-drawing characters, the plain manifest falls back to ASCII separators.
