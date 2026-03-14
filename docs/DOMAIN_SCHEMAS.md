
# DOMAIN_SCHEMAS.md

This document defines the **initial domain schemas** used by the Aptitude Client.

These schemas represent the core data structures used during:

- discovery
- dependency resolution
- planning
- execution preparation

These schemas are intentionally **minimal MVP versions**.
They will evolve as the project grows.

Agents should treat these as the **current canonical structures** unless a plan explicitly updates them.

---

# 1. SkillManifest

Represents metadata describing a skill available in the registry.

Purpose:
- discovery results
- dependency resolution
- execution planning

Example JSON:

{
  "id": "pdf.extract",
  "name": "PDF Extract",
  "version": "1.2.0",
  "description": "Extract text from PDF documents",
  "dependencies": [
    {
      "skill": "filesystem.read",
      "constraint": ">=1.0.0"
    }
  ]
}

Fields:

| Field | Type | Required | Description |
|------|------|----------|-------------|
| id | string | yes | unique skill identifier |
| name | string | yes | human readable name |
| version | string | yes | semantic version |
| description | string | no | skill description |
| dependencies | list[DependencySpec] | no | dependencies required by the skill |

---

# 2. DependencySpec

Represents a dependency requirement for a skill.

Example:

{
  "skill": "filesystem.read",
  "constraint": ">=1.0.0"
}

Fields:

| Field | Type | Required | Description |
|------|------|----------|-------------|
| skill | string | yes | dependent skill id |
| constraint | string | yes | version constraint (semver style) |

---

# 3. VersionConstraint

Represents version requirements used during dependency resolution.

Examples:

>=1.0.0
^2.1.0
~1.5.0
==3.0.1

Supported operators (initial MVP):

| Operator | Meaning |
|--------|--------|
| == | exact version |
| >= | minimum version |
| ^ | compatible version |
| ~ | patch-compatible version |

The resolver will interpret these constraints during dependency solving.

---

# 4. ResolutionResult

Represents the output of the dependency resolver.

Example:

{
  "resolved_skills": [
    {
      "skill": "pdf.extract",
      "version": "1.2.0"
    },
    {
      "skill": "filesystem.read",
      "version": "1.3.1"
    }
  ],
  "conflicts": [],
  "decision_trace": []
}

Fields:

| Field | Type | Description |
|------|------|-------------|
| resolved_skills | list | final selected versions |
| conflicts | list | dependency conflicts |
| decision_trace | list | resolution reasoning steps |

---

# 5. Lockfile

Represents the deterministic output of resolution.

Lockfiles ensure reproducible installations.

Example:

{
  "version": 1,
  "skills": [
    {
      "skill": "pdf.extract",
      "version": "1.2.0"
    },
    {
      "skill": "filesystem.read",
      "version": "1.3.1"
    }
  ]
}

Fields:

| Field | Type | Description |
|------|------|-------------|
| version | integer | lockfile format version |
| skills | list | resolved skill versions |

---

# 6. ExecutionPlan

Represents the ordered execution plan produced by the client.

Example:

{
  "steps": [
    {
      "skill": "filesystem.read",
      "action": "read_file"
    },
    {
      "skill": "pdf.extract",
      "action": "extract_text"
    }
  ]
}

Fields:

| Field | Type | Description |
|------|------|-------------|
| steps | list | ordered execution steps |

Each step contains:

| Field | Type | Description |
|------|------|-------------|
| skill | string | skill responsible for execution |
| action | string | action to perform |

---

# 7. DecisionTrace (Optional)

Represents reasoning steps used during dependency resolution.

Example:

{
  "decision": "selected filesystem.read@1.3.1",
  "reason": "highest compatible version"
}

Purpose:

- debugging
- explainability
- deterministic traceability

Fields:

| Field | Type | Description |
|------|------|-------------|
| decision | string | resolver decision |
| reason | string | explanation for the decision |

---

# Notes

These schemas represent **MVP structures only**.

Future versions may extend them with:

- skill capabilities
- artifact hashes
- registry metadata
- policy annotations
- execution environment requirements
