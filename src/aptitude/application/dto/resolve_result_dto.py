"""Result DTOs for discovery-driven resolve flows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResolveCoordinateDto(BaseModel):
    """Client-facing exact coordinate."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str


class ResolveSkillSummaryDto(BaseModel):
    """Minimal skill summary exposed by CLI result payloads."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    runtime: str | None = None
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str


class LockRootDto(BaseModel):
    """Root request metadata stored in the lockfile."""

    model_config = ConfigDict(frozen=True)

    request: str
    requested_version: str | None = None
    selected_node_id: str
    selection_mode: str


class LockedSkillDto(BaseModel):
    """One locked skill node exposed to interfaces."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    slug: str
    version: str
    artifact_ref: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str
    published_at: str
    content_checksum: dict[str, Any] = Field(default_factory=dict)


class LockedEdgeDto(BaseModel):
    """One explicit lock dependency edge."""

    model_config = ConfigDict(frozen=True)

    source_node_id: str
    target_node_id: str
    edge_type: str = "depends_on"
    optional: bool = False
    markers: list[str] = Field(default_factory=list)


class GovernanceSnapshotDto(BaseModel):
    """One governance snapshot entry stored in the lock."""

    model_config = ConfigDict(frozen=True)

    rule: str
    passed: bool
    message: str
    node_id: str | None = None


class PolicySnapshotDto(BaseModel):
    """Minimal policy snapshot stored in the lock."""

    model_config = ConfigDict(frozen=True)

    profile: str
    source: str
    allowed_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_trust_tiers: list[str] = Field(default_factory=list)
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None
    max_total_token_estimate: int | None = None
    max_total_content_size_bytes: int | None = None


class SelectionSnapshotDto(BaseModel):
    """Minimal selection explainability metadata stored in the lock."""

    model_config = ConfigDict(frozen=True)

    profile: str
    interaction_mode: str
    profile_source: str
    interaction_mode_source: str


class LockfileDto(BaseModel):
    """Client-facing lock artifact."""

    model_config = ConfigDict(frozen=True)

    version: int
    generated_at: str | None = None
    client_version: str | None = None
    root: LockRootDto
    nodes: list[LockedSkillDto] = Field(default_factory=list)
    edges: list[LockedEdgeDto] = Field(default_factory=list)
    install_order: list[str] = Field(default_factory=list)
    selection: SelectionSnapshotDto | None = None
    policy: PolicySnapshotDto | None = None
    governance: list[GovernanceSnapshotDto] = Field(default_factory=list)


class ExecutionStepDto(BaseModel):
    """One planned execution step."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    skill: str
    version: str
    artifact_ref: str
    action: str


class ExecutionPlanDto(BaseModel):
    """Execution plan preview exposed to interfaces."""

    model_config = ConfigDict(frozen=True)

    steps: list[ExecutionStepDto] = Field(default_factory=list)


class TraceEntryDto(BaseModel):
    """One trace entry emitted by the client."""

    model_config = ConfigDict(frozen=True)

    stage: str
    action: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationDto(BaseModel):
    """One policy evaluation attached to a result."""

    model_config = ConfigDict(frozen=True)

    rule: str
    passed: bool
    message: str
    coordinate: ResolveCoordinateDto | None = None


class DiscoveryCandidateDto(BaseModel):
    """One ranked candidate shown to the user or used automatically."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    matched_labels: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    runtime: str | None = None
    lifecycle_status: str
    trust_tier: str
    token_estimate: int | None = None
    content_size_bytes: int | None = None
    published_at: str
    ranking_position: int
    selection_details: list[str] = Field(default_factory=list)
    selection_reason: str | None = None


class ResolvedSkillNodeDto(BaseModel):
    """One exact node in the resolved graph."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    runtime: str | None = None
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str
    published_at: str


class ResolvedEdgeDto(BaseModel):
    """One graph edge in the resolved graph."""

    model_config = ConfigDict(frozen=True)

    source: ResolveCoordinateDto
    target: ResolveCoordinateDto
    edge_type: str = "depends_on"
    optional: bool = False
    markers: list[str] = Field(default_factory=list)


class ConflictDto(BaseModel):
    """One structured conflict in the resolved graph."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    coordinates: list[ResolveCoordinateDto] = Field(default_factory=list)


class ResolvedGraphDto(BaseModel):
    """Resolved dependency graph output."""

    model_config = ConfigDict(frozen=True)

    root: ResolveCoordinateDto
    nodes: list[ResolvedSkillNodeDto] = Field(default_factory=list)
    edges: list[ResolvedEdgeDto] = Field(default_factory=list)
    install_order: list[ResolveCoordinateDto] = Field(default_factory=list)
    conflicts: list[ConflictDto] = Field(default_factory=list)


class ResolveQueryResultDto(BaseModel):
    """Discovery-driven query result for the current CLI flow."""

    model_config = ConfigDict(frozen=True)

    requested_query: str
    requested_version: str | None = None
    status: Literal["selection_required", "resolved"]
    selection_mode: str | None = None
    candidates: list[DiscoveryCandidateDto] = Field(default_factory=list)
    selected_coordinate: ResolveCoordinateDto | None = None
    selected_skill: ResolveSkillSummaryDto | None = None
    graph: ResolvedGraphDto | None = None
    lockfile: LockfileDto | None = None
    execution_plan: ExecutionPlanDto | None = None
    trace: list[TraceEntryDto] = Field(default_factory=list)
    policy_evaluations: list[PolicyEvaluationDto] = Field(default_factory=list)
