# Resolver Schema Surfaces

The resolver does not own a database schema in this repository. Its canonical local schema surfaces are configuration and lock data.

## Configuration Surface

Current configuration sources:

- environment variables
- system `aptitude.toml`
- user-level `aptitude.toml`
- workspace `aptitude.toml`

These sources shape policy and selection preferences, but they do not replace resolver defaults unless the precedence rules permit it.

Execution configuration is also supported:

```toml
[execution]
concurrent_downloads = 8
concurrent_installs = 4
```

Environment overrides:

- `APTITUDE_CONCURRENT_DOWNLOADS`
- `APTITUDE_CONCURRENT_INSTALLS`

Execution config precedence is default, system config, user config, workspace
config, then environment. The last non-null value wins.

## Lockfile Surface

The lockfile is the durable resolved schema for execution.

Project and global install locks are cumulative: each successful install adds a
root and its pinned graph without changing existing pins. New lockfiles write
both `roots` (the complete root set) and the legacy `root` field (the most
recent root); v1 single-root lockfiles remain readable.

It must preserve:

- selected coordinates
- graph shape
- install order
- governance outcomes
- minimal policy snapshot
- optional explainability metadata that remains non-executable
- artifact references and checksum facts needed to replay materialization

## Why This File Exists

The registry docs use `reference/schema.md` for canonical persistence shape. The resolver analogue is the set of local schema surfaces it owns directly: config and lock data.
