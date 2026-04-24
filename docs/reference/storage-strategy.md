# Storage Strategy

This document describes how aptitude stores and materializes local state today.

## Current Strategy

- registry data is read remotely through `registry/`
- immutable metadata and artifact bytes may be cached locally as advisory optimizations
- lockfiles are the durable local execution input
- materialization downloads compressed `tar.zst` skill artifacts, verifies
  checksums, safely extracts archive contents into a staging directory, and then
  promotes the completed workspace into the requested target

## Constraints

- caches must never become a hidden source of truth
- lock replay must remain valid without discovery or dependency solving
- checksum verification happens during materialization, not as an afterthought
- archive extraction must reject unsafe paths, links, device members, and path
  escapes before writing to the final target

## Deferred Areas

- richer cache invalidation strategy beyond current advisory behavior
- broader local storage abstractions if plugins, SDK, or MCP surfaces require them
