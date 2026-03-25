"""Domain model for exact immutable skill metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class SkillMetadata:
    """Client-owned representation of a skill metadata response."""

    coordinate: SkillCoordinate
    name: str
    description: str
    tags: list[str]
    headers: dict[str, str]
    inputs_schema: dict[str, Any] | None
    outputs_schema: dict[str, Any] | None
    token_estimate: int | None
    maturity_score: float | None
    security_score: float | None
    rendered_summary: str
    content_checksum_algorithm: str
    content_checksum_digest: str
    content_size_bytes: int | None
    lifecycle_status: str
    trust_tier: str
    published_at: str
