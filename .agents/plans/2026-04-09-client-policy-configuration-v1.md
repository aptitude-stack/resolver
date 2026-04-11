# Client Policy Configuration V1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add layered client-side policy discovery and inspection for Aptitude with system, user, and workspace scopes plus a read-only `aptitude policy show` command.

**Architecture:** Keep raw config discovery in `shared/config`, effective merge logic and inspection DTOs in `application`, and the CLI as a thin rendering layer. Fresh-planning commands use live effective policy, while `sync --lock` remains lock-driven and does not reapply current policy.

**Tech Stack:** Python 3.11+, Typer, Pydantic, pytest, Rich

---

### Task 1: Config discovery and typed inspection DTOs

**Files:**
- Modify: `src/aptitude_resolver/shared/config/aptitude_config.py`
- Modify: `src/aptitude_resolver/shared/config/__init__.py`
- Create: `src/aptitude_resolver/application/dto/policy_config_dto.py`
- Modify: `src/aptitude_resolver/application/dto/__init__.py`
- Test: `tests/unit/shared/config/test_aptitude_config.py`

- [ ] Add system config path discovery for Windows and Unix-like platforms.
- [ ] Add typed application DTOs for discovered config layers and effective policy/selection reporting.
- [ ] Export the new discovery helpers and DTOs from their package boundaries.
- [ ] Add unit coverage for user/workspace/system discovery and raw config loading.

### Task 2: Effective merge logic and policy report builder

**Files:**
- Modify: `src/aptitude_resolver/application/composition.py`
- Modify: `src/aptitude_resolver/domain/policy/models.py` only if extra serialization helpers are needed
- Test: `tests/unit/application/test_composition.py`

- [ ] Extend selection precedence to `default < system < user < workspace < env < CLI`.
- [ ] Extend policy merging to `default -> system -> user -> workspace -> CLI` with restrictive-only semantics.
- [ ] Preserve `sync --lock` behavior unchanged.
- [ ] Add an application-level builder that returns a full policy report for CLI inspection, including discovered paths, raw layer contributions, and effective merged values.
- [ ] Add tests for precedence, restrictive-only merging, invalid layer errors, and report shape.

### Task 3: CLI policy inspection surface

**Files:**
- Modify: `src/aptitude_resolver/interfaces/cli/app.py`
- Modify: `src/aptitude_resolver/interfaces/cli/catalog.py`
- Test: `tests/unit/interfaces/cli/test_help_surface.py`
- Test: `tests/unit/interfaces/cli/test_app.py`

- [ ] Add `aptitude policy show` with human-readable output and `--json`.
- [ ] Keep the command read-only and reuse application-built report data.
- [ ] Update root help, command help, and manifest output to include the policy command and explain config scopes.
- [ ] Add CLI tests for `policy show`, JSON output, and updated help/manifest surfaces.

### Task 4: Architecture and user-facing docs

**Files:**
- Modify: `docs/architecture/selection-and-governance.md`
- Modify: `docs/architecture/system-overview.md` if config layering or policy inspection needs mention
- Modify: `docs/roadmap/client-policy-summary.md`
- Create: `docs/roadmap/client-policy-configuration.md`

- [ ] Update the canonical policy/selection precedence docs to match the implemented behavior.
- [ ] Document the v1 scope decision: no `aptitude config set/edit/delete`, no `--config-file`, no `APTITUDE_CONFIG_FILE`.
- [ ] Explain config ownership and locations for system, user, and workspace scopes.

### Task 5: Verification

**Files:**
- Verify only

- [ ] Run focused config/composition tests.
- [ ] Run CLI/help/policy command tests.
- [ ] Run a combined targeted test slice before completion.
