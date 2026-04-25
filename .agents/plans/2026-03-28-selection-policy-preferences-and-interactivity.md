# Selection Policy, Preferences, And Interactivity Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit selection preferences, profile-aware reranking, and explicit interaction modes to the Aptitude client, then layer config loading and explainability on top without weakening determinism or execution boundaries.

**Architecture:** Keep hard policy separate from soft selection preferences. Hard legality remains in `governance/`, soft candidate preference stays in `discovery/`, final root selection stays in `resolver/`, and the CLI remains an interface-only layer that parses flags and prompts when allowed. Preference metadata may explain fresh planning, but execution must remain driven only by locked nodes, edges, and install order.

**Tech Stack:** Python, Typer, dataclasses, Pydantic DTOs, pytest

---

## Scope Summary

The current baseline already has:

- candidate-policy filtering before ranking
- graph governance before lock generation
- deterministic final candidate selection
- hidden TTY-based prompting for root ambiguity
- lock-driven execution and `sync --lock`

The remaining gaps are:

1. There is no explicit `SelectionPreferences` model.
2. The reranker does not yet implement `balanced`, `low-cost`, and `high-trust` profiles.
3. Interaction behavior is implicit and based only on TTY detection.
4. There is no user-facing config or CLI preference surface.
5. The effective profile and interaction mode are not surfaced clearly in trace or lock explainability metadata.

---

## Milestone 1: Core Selection Behavior

### Task 1: Freeze the canonical docs for the smaller selection scope

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`
- Review: `C:\Dev\apptitude-client\aptitude-client\README.md`

- [ ] Add an explicit distinction between `PolicyContext` and `SelectionPreferences`.
- [ ] Define only the supported phase-1 profiles:
  - `balanced`
  - `low-cost`
  - `high-trust`
- [ ] Explicitly defer `latest` to a later milestone.
- [ ] Define interaction modes:
  - `auto`
  - `always`
  - `never`
- [ ] Define that prompting is allowed only for root candidate ambiguity, never for recursive dependency resolution.
- [ ] Define that preference metadata may explain planning decisions but must not become an execution dependency.

### Task 2: Add the `SelectionPreferences` model

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\selection.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\__init__.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\domain\policy\test_selection_preferences.py`

- [ ] Create `SelectionPreferences` with:
  - `profile`
  - `interaction_mode`
- [ ] Keep `PolicyContext` focused on hard legality only.
- [ ] Add defaults for:
  - `profile = "balanced"`
  - `interaction_mode = "auto"`
- [ ] Add unit tests for valid defaults and invalid values.

### Task 3: Make reranking profile-aware

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\discovery\reranking\candidate_reranker.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\discovery\test_candidate_reranker.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`

- [ ] Change `rerank_candidates(...)` so it accepts `SelectionPreferences`.
- [ ] Implement lexicographic profile ordering instead of weighted scores.
- [ ] Implement `balanced` ordering:
  relevance -> trust -> lower token estimate -> lower content size -> version/default quality -> semver -> publish date -> slug.
- [ ] Implement `low-cost` ordering:
  relevance -> lower token estimate -> lower content size -> trust -> lifecycle -> version/default quality -> semver -> publish date -> slug.
- [ ] Implement `high-trust` ordering:
  relevance -> trust -> lifecycle -> lower token estimate -> lower content size -> version/default quality -> semver -> publish date -> slug.
- [ ] Handle missing cost values deterministically:
  known value beats unknown for cost-sensitive comparisons, then fall back to later stable keys.
- [ ] Add tests for the key user-visible case:
  two legal candidates, one cheaper and one more trusted, with different winners under `balanced` vs `low-cost`.

### Task 4: Make interaction mode explicit in request/use-case flow

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\resolve_request_dto.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\install_dto.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\resolver\solver\candidate_selection.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_install_skill.py`

- [ ] Pass an explicit interaction mode through request/use-case flow instead of relying on a bare boolean only.
- [ ] Keep current behavior as the initial semantic baseline:
  `auto` behaves like today’s TTY-aware prompt decision.
- [ ] Implement:
  - `auto` -> prompt only when capability exists and ambiguity remains
  - `always` -> prompt on ambiguity or fail clearly when prompting is impossible
  - `never` -> never prompt; auto-pick deterministically
- [ ] Keep `--select-slug` as an exact bypass for ambiguity.
- [ ] Add regression tests proving only root candidate ambiguity can yield a prompt path.

### Task 5: Verify Milestone 1 behavior

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`

- [ ] Add tests for profile-sensitive ranking.
- [ ] Add tests for ambiguity behavior under `auto`, `always`, and `never`.
- [ ] Add tests proving prompting remains root-only.
- [ ] Run the focused suite for policy-selection behavior before moving to config.

---

## Milestone 2: Config And User Control

### Task 6: Add raw config parsing only

**Files:**
- Create: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\config\aptitude_config.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\shared\config\__init__.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\shared\config\test_aptitude_config.py`

- [ ] Add raw config parsing for:
  - `[selection]`
  - only the minimum policy sections strictly needed by current defaults
- [ ] Support workspace `aptitude.toml`.
- [ ] Support user config discovery for the current OS.
- [ ] Support env-based overrides for selection preference fields where practical.
- [ ] Keep `shared/config` limited to parsing and file discovery.
- [ ] Do not put merge semantics or business rules into `shared/config`.

### Task 7: Add precedence/merge rules in application composition

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\composition.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\models.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\domain\policy\selection.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\test_composition.py`

- [ ] Build one effective `SelectionPreferences` in composition using:
  CLI override -> env -> workspace config -> user config -> default.
- [ ] Add only the minimum merge behavior needed for current policy defaults.
- [ ] Explicitly defer broader org-policy merge semantics beyond what is strictly needed later.
- [ ] Add unit tests for precedence behavior.

### Task 8: Add CLI flags for user control

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\interfaces\cli\app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_app.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\interfaces\cli\test_help_surface.py`

- [ ] Add:
  - `--prefer balanced|low-cost|high-trust`
  - `--interaction-mode auto|always|never`
- [ ] Keep existing flags:
  - `--version`
  - `--select-slug`
  - `--target`
  - `--json`
- [ ] Update help text to explain preference vs interaction mode clearly.
- [ ] Add CLI coverage for flag parsing and precedence with config defaults.

### Task 9: Explicit deferrals for Milestone 2

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\ARCHITECTURE.md`
- Modify: `C:\Dev\apptitude-client\aptitude-client\docs\RULES.md`

- [ ] Explicitly defer:
  - `latest` profile
  - hard policy CLI flags such as `--max-tokens`, `--max-content-size`, `--allow-trust`
  - broad org-policy merge semantics

---

## Milestone 3: Explainability Only

### Task 10: Add trace enrichment for effective selection behavior

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\queries\plan_skill_resolution.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\resolution_mapping.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\resolve_result_dto.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_resolve_skill_query.py`

- [ ] Emit trace entries for:
  - effective selection profile
  - effective interaction mode
  - preference source when applicable
- [ ] Add a trace explanation for why the winning candidate beat the alternatives under the chosen profile.
- [ ] Keep trace payloads small and deterministic.

### Task 11: Add minimal lock explainability metadata for the chosen profile

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\model.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\serializer.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\lockfile\parser.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\use_cases\resolution_mapping.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\src\aptitude_client\application\dto\resolve_result_dto.py`
- Test: `C:\Dev\apptitude-client\aptitude-client\tests\unit\lockfile\test_lockfile.py`

- [ ] Persist only the minimal explainability metadata needed for the chosen profile.
- [ ] Keep that metadata clearly separate from execution-critical lock data.
- [ ] Add parse/serialize round-trip tests.
- [ ] Add explicit regression coverage proving execution still depends only on locked nodes, edges, and install order.

### Task 12: Verify `sync --lock` remains independent from preference metadata

**Files:**
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\application\use_cases\test_sync_from_lock.py`
- Modify: `C:\Dev\apptitude-client\aptitude-client\tests\unit\execution\test_materialize.py`

- [ ] Add tests proving `sync --lock` does not need selection preference metadata to execute correctly.
- [ ] Confirm preference metadata is explainability-only and not an execution dependency.

---

## Recommended Execution Order

1. Milestone 1: `SelectionPreferences`, profile-aware reranking, explicit interaction mode, tests
2. Milestone 2: raw config parsing, precedence/merge, CLI flags
3. Milestone 3: trace enrichment and minimal lock explainability metadata

## Validation Commands

- `py -3 -m pytest tests/unit/domain/policy/test_selection_preferences.py tests/unit/discovery/test_candidate_reranker.py tests/unit/application/use_cases/test_resolve_skill_query.py tests/unit/application/use_cases/test_install_skill.py -v`
- `py -3 -m pytest tests/unit/shared/config/test_aptitude_config.py tests/unit/application/test_composition.py tests/unit/interfaces/cli/test_app.py tests/unit/interfaces/cli/test_help_surface.py -v`
- `py -3 -m pytest tests/unit/lockfile/test_lockfile.py tests/unit/application/use_cases/test_sync_from_lock.py tests/unit/execution/test_materialize.py -v`
- `py -3 -m pytest -v`

## Notes

- Do not let preference logic weaken hard policy constraints.
- Do not make dependency resolution interactive.
- Do not introduce any execution dependency on preference metadata.
- Keep `sync --lock` free of fresh-planning preference requirements.
- Keep `latest` and hard policy CLI flags out of the first implementation wave.
