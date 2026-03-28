"""Domain model for exact immutable skill coordinates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillCoordinate:
    """Immutable skill identity for one exact version."""

    slug: str
    version: str
