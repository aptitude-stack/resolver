"""Domain model for logical skill identity records."""

from __future__ import annotations

from dataclasses import dataclass

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class SkillIdentity:
    """Logical skill identity plus its current version pointer."""

    slug: str
    status: str
    current_version: SkillCoordinate | None
    current_lifecycle_status: str | None
    current_trust_tier: str | None
    current_published_at: str | None
    created_at: str | None
    updated_at: str | None
