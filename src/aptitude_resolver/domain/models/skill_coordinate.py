"""Domain model for exact immutable skill coordinates."""

from __future__ import annotations

from dataclasses import dataclass

from aptitude_resolver.domain.versioning import parse_skill_version


@dataclass(frozen=True)
class SkillCoordinate:
    """Immutable skill identity for one exact version."""

    slug: str
    version: str

    def __post_init__(self) -> None:
        parse_skill_version(self.version)
