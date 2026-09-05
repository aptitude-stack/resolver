# API Contract

## Current Registry Paths

The resolver currently reads from the live registry through these runtime paths:

- `POST /discovery`
- `GET /skills/{slug}/versions`
- `GET /skills/{slug}/versions/{version}`
- `GET /resolution/{slug}/{version}`
- `GET /skills/{slug}/versions/{version}/content`

The client keeps legacy fallbacks for older server deployments:

- `GET /skills/{slug}`
- `GET /skills/{slug}/{version}`
- `GET /skills/{slug}/{version}/content`

## Runtime Assumptions

- the server is the source of immutable metadata and artifact facts
- the artifact endpoint path is still named `/content`, but the install payload
  is binary `tar.zst` bytes
- final ranking, version choice, dependency solving, and lock generation remain local resolver behavior
- `sync --lock` must replay an existing lock without calling discovery or dependency solving

## Version and Selector Contract

Resolver inputs and registry responses use strict SemVer, including the full
`major.minor.patch` form and optional prerelease or build metadata. PEP 440
forms such as `1.2` and `2.0rc1` are rejected, including in lockfiles. Build
metadata is ignored for ordering while the authored version string remains
unchanged for immutable lookups.

Dependency constraints are comma-separated AND expressions with one or more
comparators (`=`, `==`, `!=`, `<`, `<=`, `>`, `>=`), strict SemVer operands,
and a maximum length of 200 characters; bare versions are not constraints.
Selectors contain exactly one of `version` or `version_constraint`. Dependency
slugs use the registry's lowercase slug pattern and markers use
`^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`, preserving marker order and duplicates.
Null `optional` values are interpreted as `false`. Resolver metadata transport
omits separate input and output schema fields.

## Checksum Contract

- checksum algorithm: `sha256`
- checksum verification happens during materialization
- checksum verification is applied to compressed artifact bytes unless registry
  metadata explicitly defines a different checksum scope
- mismatch must fail fast as `ContentChecksumMismatchError`
