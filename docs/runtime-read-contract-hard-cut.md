# Runtime Read Contract Hard Cut

## Purpose

This document freezes the initial implementation contract for `aptitude-client`.

It exists to remove ambiguity between:

- the long-term product direction in `docs/MVP.md`
- the broader architectural target in `docs/scope.md`
- the runtime-tested server behavior summarized in `docs/server-api-integration-notes.md`

For milestones `01` through `04` in `.agents/plans/`, this file is the
decision record for what the client is allowed to build against.

## Initial Contract Decision

The first implementation slice is exact-coordinate, read-only, and uses only
the runtime-tested server read endpoints below:

- `GET /skills/{slug}/versions/{version}`
- `GET /resolution/{slug}/{version}`

The first implementation slice does not call:

- `POST /discovery`
- `GET /discovery/skills/search`
- any current-version endpoint
- any version-listing endpoint

## Why This Hard Cut Exists

The checked-in OpenAPI file and the Postman-tested runtime behavior are not
fully aligned.

The client therefore needs one narrow, documented contract that is:

- currently testable
- sufficient for a first end-to-end slice
- small enough to avoid speculative implementation

This hard cut allows milestones `03` and `04` to proceed without depending on:

- unresolved discovery request/response shape
- unverified current-version behavior
- unverified version-listing behavior
- mixed use of runtime and stale spec examples

## Approved Runtime Shapes

### Exact Metadata

Route:

- `GET /skills/{slug}/versions/{version}`

Client-consumed fields:

- `slug`
- `version`
- `metadata.name`
- `metadata.description`
- `metadata.tags`
- `content.rendered_summary`
- `content.checksum.algorithm`
- `content.checksum.digest`
- `lifecycle_status`
- `trust_tier`
- `published_at`

Do not consume:

- `relationships`
- `content_download_path`

### Direct Dependencies

Route:

- `GET /resolution/{slug}/{version}`

Client-consumed fields:

- `slug`
- `version`
- `depends_on[]`
- `depends_on[].slug`
- `depends_on[].version`
- `depends_on[].optional`
- `depends_on[].markers`

Assumptions:

- response is first-degree only
- dependency order is server-authored and must be preserved
- response does not include `extends`
- response does not include a rich `relationships` envelope

### Error Envelope

The client supports only this normalized transport error shape in the first
slice:

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

Client-consumed error codes for the first slice:

- `SKILL_VERSION_NOT_FOUND`
- `INVALID_REQUEST`

## Implementation Boundary For The First Slice

The transport boundary for milestones `03` and `04` is `src/aptitude_client/registry/`.

That means:

- the registry adapter owns raw HTTP behavior
- application code consumes client-owned models and errors
- discovery remains out of the first executable path

## Public Client Shape For The First Slice

The first CLI flow is:

`aptitude resolve <slug> --version <version>`

Behavior:

- the CLI accepts exact coordinates only
- the application layer fetches exact metadata
- the application layer fetches direct dependencies
- the resolver shapes a deterministic result without candidate selection
- the output is stable JSON

The first slice does not yet implement:

- candidate generation
- name-based resolution
- version choice across candidates
- recursive dependency solving
- lock generation
- execution planning

## Deferred Work

`POST /discovery` is deferred to a later milestone.

Before the client adds discovery-driven UX such as:

`aptitude resolve pdf.extract`

the project must first resolve:

- whether discovery remains body-based or query-based
- whether discovery returns slug strings only or richer candidate objects
- how the client derives an exact version after discovery
- what deterministic tie-break rule applies when multiple candidates or
  versions exist

## Implementation Rule

Until a later milestone explicitly revises this document:

- milestones `03` and `04` may only use the two approved runtime read routes
- no implementation may mix Postman runtime behavior with conflicting OpenAPI
  examples in the same client path
- exact coordinates are the only allowed input contract for the first
  end-to-end slice
