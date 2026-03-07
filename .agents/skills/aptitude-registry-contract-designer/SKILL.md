---
name: aptitude-registry-contract-designer
description: Design versionable Aptitude registry API contracts and client integration boundaries. Use when defining REST endpoints, request/response schemas, and structured error models for skill discovery and artifact retrieval.
---
# Aptitude Registry Contract Designer

## Purpose
Design the Aptitude registry API contracts and the corresponding client-side integration boundaries.

## Responsibilities
- Define REST endpoints for skill discovery and retrieval.
- Design response/request schemas.
- Separate metadata discovery from artifact download.
- Keep contracts versionable and explicit.

## Registry Concepts
The registry should support:
- search skills
- fetch skill metadata
- fetch specific skill versions
- publish skill artifacts
- fetch scores/security metadata
- future deprecation/yank semantics

## Suggested Endpoints
- GET /skills
- GET /skills/{name}
- GET /skills/{name}/{version}
- POST /publish
- GET /skills/{name}/{version}/artifact
- GET /skills/{name}/{version}/security
- GET /skills/{name}/{version}/metrics

## Design Rules
- Use Pydantic models for client-side contract models.
- Keep transport models separate from internal domain models where helpful.
- Support future pagination, auth, and filtering.
- Error responses must be structured and predictable.

## Definition of Done
Contract work is complete only if:
- endpoints are named consistently
- response models are explicit
- errors are modeled
- future extensibility is preserved