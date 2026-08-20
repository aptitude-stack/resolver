"""Domain model for discovery request construction."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_resolver.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class DiscoveryQuery:
    """Client-owned discovery request shape prior to registry transport mapping."""

    query: str
    tags: list[str] = field(default_factory=list)
    context_skills: list[SkillCoordinate] = field(default_factory=list)
