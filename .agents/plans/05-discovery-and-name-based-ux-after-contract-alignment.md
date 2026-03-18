# Plan 05 - Discovery And Name-Based UX After Contract Alignment

## Goal
Define the follow-up milestone that introduces discovery-driven user input only
after the server discovery contract and client version-selection rules are
reconciled.

## Stack Alignment
- Discovery runtime evidence: `docs/server-api-integration-notes.md`
- OpenAPI comparison source: `docs/openapi/repository-api-v1.json`
- MVP source: `docs/MVP.md`

## Scope
- Reconcile `POST /discovery` runtime behavior with the checked-in OpenAPI.
- Decide whether discovery remains slug-only or returns richer candidate
  objects.
- Decide how the client obtains a concrete version after a discovery result.
- Define the point where minimal resolver logic transitions from exact
  coordinate shaping to candidate selection.
- Only after those decisions are frozen, add name-based CLI UX such as:
  - `aptitude resolve pdf.extract`

## Questions This Milestone Must Resolve
- Is discovery request shape body-based long term, or does the server contract
  revert to query parameters?
- Does discovery return slug strings only, or objects with ranking metadata?
- What is the exact client flow from discovery candidate to concrete version?
- Does the client need a current-version or list-version runtime endpoint
  before name-based resolution can be safe?
- What deterministic tie-break rule applies when multiple candidates or
  multiple versions are available?

## Architecture Impact
- This milestone is the bridge between the exact-coordinate hard cut and the
  broader CLI-first MVP described in `docs/MVP.md`.
- It prevents premature discovery UX from being built on top of an unresolved
  contract gap.

## Deliverables
- A reconciled discovery contract decision.
- A deterministic version-selection rule for the first discovery-driven flow.
- A revised CLI plan that expands beyond exact coordinates without breaking
  milestones 01-04.

## Acceptance Criteria
- Milestones 01-04 are complete before this milestone begins.
- No initial implementation depends on unverified current-version or
  list-version behavior.
- The discovery-driven flow is defined end to end before any implementer begins
  coding it.

## Test Plan
- Contract review between runtime behavior and the checked-in OpenAPI.
- Decision review for candidate and version tie-break rules.
- Revised CLI acceptance review confirming the name-based flow remains
  deterministic.
