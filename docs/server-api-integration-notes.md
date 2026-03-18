# Server API Integration Notes

## Purpose

This document summarizes the server behavior that is currently validated by the
Postman collection in `docs/openapi/API.postman_collection.json`.

Its goal is to help implement `aptitude-client` against the server that is
actually running today, while also calling out differences from the checked-in
OpenAPI file at `docs/openapi/repository-api-v1.json`.

## Sources Reviewed

- `docs/openapi/API.postman_collection.json`
- `docs/openapi/New Environment.postman_environment.json`
- `docs/openapi/repository-api-v1.json`
- `docs/MVP.md`
- `docs/scope.md`

## Important Conclusion

For initial client implementation, treat the Postman collection as the best
evidence of the server contract that is currently working end to end.

The OpenAPI file is still valuable, but it appears to be partially out of sync
with the runtime behavior exercised by Postman. Client code should not blindly
assume the OpenAPI paths and payload shapes are the active ones without
reconciling them first.

For the current implementation hard cut, also follow
`docs/runtime-read-contract-hard-cut.md`, which narrows the first client slice
to exact-coordinate reads only.

## Confirmed Environment and Auth Model

The Postman environment defines:

- `baseUrl = http://localhost:8000`
- `readToken = reader-token`
- `publishToken = publisher-token`
- `adminToken = admin-token`

This implies three bearer-token roles:

- read access for fetch and discovery
- publish access for immutable version creation
- admin access for lifecycle changes

All business endpoints in the Postman collection send:

- `Authorization: Bearer <token>`

Health endpoints do not require a token in the collection.

## Confirmed Runtime Endpoints from Postman

### Health

- `GET /healthz`
- `GET /readyz`

Observed behavior:

- `healthz` returns HTTP `200`
- `readyz` returns HTTP `200`
- `readyz` includes a `database` check with status `ok`

### Publish immutable skill version

- `POST /skill-versions`

Used with `publishToken`.

Request body includes:

- `slug`
- `version`
- `content.raw_markdown`
- `content.rendered_summary`
- `metadata`
- `relationships`

Observed behavior:

- success returns HTTP `201`
- duplicate publish returns HTTP `409`
- invalid payload returns HTTP `422`

Important response note:

The Postman tests explicitly expect the publish response to omit:

- `relationships`
- `content_download_path`

That means the client should not rely on publish responses echoing the full
relationship graph, even if the request contains it.

### Update lifecycle status

- `PATCH /skills/{slug}/versions/{version}/status`

Used with `adminToken`.

Observed request body:

```json
{
  "status": "deprecated",
  "note": "Postman sanity lifecycle transition for authenticated admin coverage."
}
```

Observed behavior:

- success returns HTTP `200`
- response includes `slug`, `version`, `status`, `trust_tier`,
  `is_current_default`, and `lifecycle_changed_at`

### Fetch exact immutable metadata

- `GET /skills/{slug}/versions/{version}`

Used with `readToken`.

Observed behavior:

- success returns HTTP `200`
- missing version returns HTTP `404`
- invalid semver path returns HTTP `422`

Important response note:

The Postman tests expect this metadata response to omit:

- `relationships`
- `content_download_path`

So the current runtime behavior appears leaner than the OpenAPI example.

### Fetch exact immutable markdown content

- `GET /skills/{slug}/versions/{version}/content`

Used with `readToken`.

Observed behavior:

- success returns HTTP `200`
- response body is raw markdown
- `Content-Type` includes `text/markdown; charset=utf-8`
- `Cache-Control` is `public, immutable`
- `ETag` equals the content checksum digest
- `Content-Length` matches the markdown body length
- missing version returns HTTP `404`

This endpoint is important if the client later needs full content, but it is
not required for the first MVP resolve flow.

### Discovery

- `POST /discovery`

Used with `readToken`.

Observed request body:

```json
{
  "name": "Postman Primary Skill",
  "description": "Primary sanity skill for collection coverage",
  "tags": ["postman", "sanity", "primary"]
}
```

Observed behavior:

- success returns HTTP `200`
- response contains `candidates`, which is an array of slugs
- missing required discovery input returns HTTP `422`
- a minimal body containing only `name` also succeeds at runtime

Important note:

This is materially different from the checked-in OpenAPI file, which documents
`GET /discovery/skills/search` with query parameters and compact candidate
objects.

### Resolution

- `GET /resolution/{slug}/{version}`

Used with `readToken`.

Observed behavior:

- success returns HTTP `200`
- response contains only direct `depends_on` declarations
- response does not include `extends`
- response does not include a full `relationships` object
- invalid semver path returns HTTP `422`
- missing version returns HTTP `404`

This means the currently tested server resolution endpoint is not performing a
full solve. It is exposing direct immutable dependency declarations for an exact
coordinate, which aligns with the client/server boundary defined in `docs/scope.md`.

## Normalized Error Contract

The Postman collection consistently validates this error shape:

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

Observed error codes include:

- `INVALID_REQUEST`
- `DUPLICATE_SKILL_VERSION`
- `SKILL_VERSION_NOT_FOUND`

Client code should centralize parsing of this envelope inside `registry/` and
translate it into explicit client-side errors.

## OpenAPI Drift to Reconcile

The checked-in OpenAPI file and the Postman collection are not fully aligned.

### Differences observed

- OpenAPI documents `GET /discovery/skills/search`
- Postman uses `POST /discovery`

- OpenAPI documents `POST /resolution/relationships:batch`
- Postman uses `GET /resolution/{slug}/{version}`

- OpenAPI examples for exact metadata include `relationships` and
  `content_download_path`
- Postman tests expect both fields to be absent from the runtime response

- OpenAPI search response is a rich object under `results`
- Postman discovery response appears to be a simpler object containing
  `candidates`

### Recommendation

Until the contract is reconciled, implementation should be guided by this rule:

- runtime-tested Postman behavior is the source of truth for the initial client adapter
- the OpenAPI file should be updated later to match the runtime contract, or the
  server should be changed to match the OpenAPI file

Do not mix the two contracts inside the client.

## What This Means for `aptitude-client`

There are two different truths to keep separate:

- the long-term product direction still includes discovery-driven resolution
- the current implementation hard cut starts with exact coordinates only

For the current implementation slice, the client should assume this flow:

1. CLI receives an exact `slug` and `version`
2. application use case fetches exact immutable metadata using
   `GET /skills/{slug}/versions/{version}`
3. application use case fetches direct dependencies using
   `GET /resolution/{slug}/{version}`
4. the resolver shapes a deterministic output without candidate search or
   version choice

`POST /discovery` is now usable in the client for query-to-slug selection, but
the runtime still exposes no current-version or version-list route. That means
the current name-based CLI flow still requires `--version`.

Current discovery-backed client flow:

1. CLI receives a query string and `--version`
2. if the query looks like an exact slug and exact fetch succeeds, resolve directly
3. otherwise call `POST /discovery` with `{ "name": "<query>" }`
4. if one candidate is returned, use that slug with the supplied version
5. if multiple candidates are returned, surface a deterministic ambiguity error
6. fetch exact metadata and direct dependencies for the selected slug and supplied version

## Recommended Client Implementation Boundaries

### `shared/config`

Own:

- base URL
- bearer token
- timeouts

### `registry/`

Own:

- HTTP transport
- auth header injection
- request and response parsing
- error-envelope parsing
- transport-to-domain mapping

Do not leak raw server payloads outside this layer if we can avoid it.

### `discovery/`

Own:

- user-intent interpretation
- discovery request construction
- candidate shaping and reranking
- discovery-specific orchestration over registry clients

### `application/use_cases`

Own:

- workflow sequencing
- calling discovery when discovery is part of the path
- calling exact fetch and dependency read for the exact-coordinate path
- deterministic selection rules
- shaping a stable CLI result DTO

### `resolver/solver`

For the first slice, own only minimal deterministic logic:

- exact version handling
- direct dependency shaping from `depends_on`
- stable result assembly with preserved dependency order

## Testing Recommendation

- keep the product target pointed at the real running server
- prefer opt-in live integration tests around `registry/` for contract proof
- do not build a mock server as a primary project deliverable
- use higher-layer fakes only where isolated application or CLI tests need them

The current live proof for the read adapter lives under `tests/integration/registry/`.

## Follow-Up Work Suggested

- Reconcile `docs/openapi/repository-api-v1.json` with the tested Postman contract.
- Add a version-lookup route to the server before supporting discovery without `--version`.
- Expand the registry client surface only after the runtime contract for each new endpoint is confirmed.
- Add example request and response DTO mappings for the client codebase.
