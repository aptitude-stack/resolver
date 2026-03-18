"""Domain model for exact immutable skill metadata."""

from __future__ import annotations

from dataclasses import dataclass

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class SkillMetadata:
    """Client-owned representation of a skill metadata response."""

    coordinate: SkillCoordinate
    name: str
    description: str
    tags: list[str]
    rendered_summary: str
    content_checksum_algorithm: str
    content_checksum_digest: str
    lifecycle_status: str
    trust_tier: str
    published_at: str
