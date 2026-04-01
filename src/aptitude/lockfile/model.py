"""Lockfile models describing one fully resolved system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LockRoot:
    """Original request context and selected root captured in the lock."""

    request: str
    requested_version: str | None
    selected_node_id: str
    selection_mode: str


@dataclass(frozen=True)
class LockedSkill:
    """One immutable locked skill node."""

    node_id: str
    slug: str
    version: str
    artifact_ref: str
    name: str
    description: str
    tags: list[str]
    headers: dict[str, str]
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str
    published_at: str
    content_checksum_algorithm: str
    content_checksum_digest: str
    content_size_bytes: int | None


@dataclass(frozen=True)
class LockedEdge:
    """One explicit dependency relationship between locked nodes."""

    source_node_id: str
    target_node_id: str
    edge_type: str = "depends_on"
    optional: bool = False
    markers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GovernanceSnapshotEntry:
    """One policy evaluation recorded in the lock."""

    rule: str
    passed: bool
    message: str
    node_id: str | None = None


@dataclass(frozen=True)
class PolicySnapshot:
    """Minimal policy snapshot persisted with one lockfile."""

    profile: str
    source: str
    allowed_lifecycle_statuses: list[str]
    allowed_trust_tiers: list[str]
    max_token_estimate: int | None
    max_content_size_bytes: int | None
    max_total_token_estimate: int | None
    max_total_content_size_bytes: int | None


@dataclass(frozen=True)
class SelectionSnapshot:
    """Minimal explainability snapshot for chosen selection preferences."""

    profile: str
    interaction_mode: str
    profile_source: str
    interaction_mode_source: str


@dataclass(frozen=True)
class Lockfile:
    """Deterministic lock artifact used as the execution source of truth."""

    version: int
    generated_at: str | None
    client_version: str | None
    root: LockRoot
    nodes: list[LockedSkill] = field(default_factory=list)
    edges: list[LockedEdge] = field(default_factory=list)
    install_order: list[str] = field(default_factory=list)
    selection: SelectionSnapshot | None = None
    policy: PolicySnapshot | None = None
    governance: list[GovernanceSnapshotEntry] = field(default_factory=list)
