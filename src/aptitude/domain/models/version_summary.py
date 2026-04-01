"""Domain model for one immutable version summary."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class VersionSummary:
    """Version summary used for candidate ranking and version selection."""

    coordinate: SkillCoordinate
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    rendered_summary: str = ""
    lifecycle_status: str = "published"
    trust_tier: str = "untrusted"
    published_at: str = ""
    content_checksum_algorithm: str | None = None
    content_checksum_digest: str | None = None
    content_size_bytes: int | None = None
    token_estimate: int | None = None
    maturity_score: float | None = None
    security_score: float | None = None
    is_current_default: bool = False
