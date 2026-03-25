"""Policy models for future governance and current validation seams."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class PolicyContext:
    """Policy inputs provided to graph validation."""

    allowed_lifecycle_statuses: list[str] = field(
        default_factory=lambda: ["published", "deprecated", "archived"]
    )


@dataclass(frozen=True)
class PolicyEvaluation:
    """One policy decision attached to a resolved graph."""

    rule: str
    passed: bool
    message: str
    coordinate: SkillCoordinate | None = None
