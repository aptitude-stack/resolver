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

## Checksum Contract

- checksum algorithm: `sha256`
- checksum verification happens during materialization
- checksum verification is applied to compressed artifact bytes unless registry
  metadata explicitly defines a different checksum scope
- mismatch must fail fast as `ContentChecksumMismatchError`
