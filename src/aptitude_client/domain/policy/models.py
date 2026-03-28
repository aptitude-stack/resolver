"""Policy models for governance inputs and evaluation results."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_client.domain.models.skill_coordinate import SkillCoordinate


@dataclass(frozen=True)
class PolicyContext:
    """Policy inputs provided to candidate and graph governance."""

    profile: str = "default"
    source: str = "client_default"

    allowed_lifecycle_statuses: list[str] = field(
        default_factory=lambda: ["published", "deprecated", "archived"]
    )
    allowed_trust_tiers: list[str] = field(
        default_factory=lambda: ["verified", "internal", "untrusted"]
    )
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None


@dataclass(frozen=True)
class PolicyEvaluation:
    """One policy decision attached to a resolved graph."""

    rule: str
    passed: bool
    message: str
    coordinate: SkillCoordinate | None = None
