# Archive Artifact Materialization

## Summary

Aptitude now installs skills from compressed `tar.zst` artifacts instead of
single markdown content files. The server endpoint path can still be named
`/content`; the client treats that response as binary archive bytes during
install and sync.

The lockfile remains the source of truth for execution. Resolution decides what
to install, the lock records the selected versions and checksum facts, and
materialization replays that locked plan.

## User View

For normal usage, the CLI commands do not change:

```bash
aptitude install "Postman Primary Skill"
aptitude sync --lock aptitude.lock.json
```

What changes is the installed shape. A skill can now contain multiple files,
such as markdown, scripts, templates, and metadata files, because the client
extracts an archive instead of writing one `content.md` file.

Install and sync still fail fast when the downloaded artifact does not match the
checksum recorded in registry metadata and the lockfile. A failed install does
not promote a partial target directory.

## Configuration

Artifact materialization has separate controls for registry downloads and local
archive extraction:

```toml
[execution]
concurrent_downloads = 8
concurrent_installs = 4
```

Defaults:

- `concurrent_downloads = 8`
- `concurrent_installs = min(os.cpu_count() or 1, 4)`

Environment overrides:

```bash
APTITUDE_CONCURRENT_DOWNLOADS=8
APTITUDE_CONCURRENT_INSTALLS=4
```

Precedence is:

```text
default -> system config -> user config -> workspace config -> environment
```

The CLI intentionally has no `--concurrent-downloads` or
`--concurrent-installs` flags. These are operational tuning settings, not normal
install choices.

## Engineer View

The registry adapter exposes `fetch_skill_artifact(...) -> bytes`. It uses the
same content endpoint paths as before, with canonical versioned paths first and
legacy fallbacks second:

```text
GET /skills/{slug}/versions/{version}/content
GET /skills/{slug}/{version}/content
```

Artifact bytes are cached by checksum when checksum metadata is available. The
cache remains advisory; correctness still comes from the lockfile and checksum
verification.

Execution runs as a two-stage pipeline:

```text
lock install order
-> bounded artifact download pool
-> checksum verification over compressed bytes
-> bounded archive extraction pool
-> deterministic result collection in lock order
-> atomic target promotion
```

Extraction is intentionally strict. The extractor rejects:

- parent-directory paths such as `../x`
- absolute paths
- drive-qualified paths
- backslash path separators
- symbolic links and hard links
- device and special members
- any destination that would escape the skill staging directory

Only regular files and directories are extracted. Scripts inside the archive are
installed as files only; materialization does not execute them.

## Zstd Runtime Support

The client supports Python `>=3.9`. Runtime zstd support is selected by feature
detection:

```python
try:
    from compression import zstd
except ImportError:
    import zstandard
```

Python 3.14 can use the standard-library `compression.zstd` module. Older
supported Python versions use the `zstandard` dependency.

## Determinism

Parallel workers must not affect observable order. These outputs are always
ordered by the lockfile install order:

- installed skill list
- execution traces
- execution plan
- lock artifacts copied into the materialized workspace

Worker completion order is deliberately ignored when returning results.
