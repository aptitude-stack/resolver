"""Domain models for resolved dependency graphs."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class ResolvedSkillNode:
    """One exact immutable node in the resolved graph."""

    coordinate: SkillCoordinate
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
    token_estimate: int | None
    maturity_score: float | None
    security_score: float | None


@dataclass(frozen=True)
class DependencyEdge:
    """Directed relationship between two resolved graph nodes."""

    source: SkillCoordinate
    target: SkillCoordinate
    edge_type: str = "depends_on"
    optional: bool = False
    markers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConflictRecord:
    """Structured conflict attached to a resolved graph."""

    code: str
    message: str
    coordinates: list[SkillCoordinate] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionGraph:
    """Deterministic graph output produced by the client resolver."""

    root: SkillCoordinate
    nodes: list[ResolvedSkillNode]
    edges: list[DependencyEdge]
    install_order: list[SkillCoordinate]
    conflicts: list[ConflictRecord] = field(default_factory=list)
