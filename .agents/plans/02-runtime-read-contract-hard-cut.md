# Plan 02 - Runtime Read Contract Hard Cut

## Goal
Freeze the initial client read surface to the runtime-tested server behavior so
the first implementation does not depend on stale or unverified API shapes.

## Stack Alignment
- Contract evidence source: `docs/server-api-integration-notes.md`
- Client/server boundary source: `docs/scope.md`
- MVP source: `docs/MVP.md`

## Scope
- Define the first client-facing read contract as these endpoints only:
  - `GET /skills/{slug}/versions/{version}`
  - `GET /resolution/{slug}/{version}`
- Explicitly record that `POST /discovery` exists in runtime but is deferred
  from the first CLI milestone.
- Explicitly reject any dependency on unverified `current version` or
  `list versions` runtime behavior.
- Define the normalized error envelope as the only supported transport error
  shape for the first client slice.
- Define the exact response fields the client is allowed to consume from the
  runtime contract.

## Canonical Runtime Shapes For The Client

### Exact metadata read
`GET /skills/{slug}/versions/{version}`

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

Client assumptions:
- Do not consume `relationships`
- Do not consume `content_download_path`

### Direct dependency read
`GET /resolution/{slug}/{version}`

Client-consumed fields:
- `slug`
- `version`
- `depends_on[]`
- `depends_on[].slug`
- `depends_on[].version`
- `depends_on[].optional`
- `depends_on[].markers`

Client assumptions:
- Response is first-degree only
- Response does not include `extends`
- Response does not include a rich `relationships` envelope

### Error envelope

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

## Architecture Impact
- Prevents the client from mixing two incompatible read contracts during the
  first implementation.
- Keeps the first slice narrow enough to implement and test quickly.
- Forces all downstream client modules to build against a documented runtime
  truth instead of speculative target-state API shapes.

## Deliverables
- A contract decision record inside this plan and supporting docs that the
  initial slice is exact-coordinate only.
- An implementation rule that no code in milestones 03 or 04 may call
  `POST /discovery`.
- A response-field allowlist for metadata and direct dependencies.
- A transport error contract that the adapter must centralize and translate.

## Acceptance Criteria
- All implementers can point to one read contract only for the initial slice.
- No initial milestone depends on discovery UX, current-version reads, or
  version listing.
- The first client slice is fully implementable from exact coordinates alone.

## Test Plan
- Contract review against `docs/server-api-integration-notes.md`.
- Documentation review confirming the first slice is read-only and
  exact-coordinate based.
- Review that milestones 03 and 04 only refer to the two approved runtime read
  endpoints.
