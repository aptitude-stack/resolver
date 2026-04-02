"""Policy models for governance inputs and evaluation results."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_resolver.domain.policy.ranking import (
    LIFECYCLE_STATUS_RANKS,
    TRUST_TIER_RANKS,
)
from aptitude_resolver.domain.models.skill_coordinate import SkillCoordinate


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
    max_total_token_estimate: int | None = None
    max_total_content_size_bytes: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allowed_lifecycle_statuses",
            _normalize_allowed_values(
                self.allowed_lifecycle_statuses,
                ordered_values=tuple(LIFECYCLE_STATUS_RANKS),
                field_name="allowed_lifecycle_statuses",
            ),
        )
        object.__setattr__(
            self,
            "allowed_trust_tiers",
            _normalize_allowed_values(
                self.allowed_trust_tiers,
                ordered_values=tuple(TRUST_TIER_RANKS),
                field_name="allowed_trust_tiers",
            ),
        )
        if self.max_token_estimate is not None and self.max_token_estimate < 0:
            raise ValueError("max_token_estimate must be greater than or equal to 0.")
        if self.max_content_size_bytes is not None and self.max_content_size_bytes < 0:
            raise ValueError(
                "max_content_size_bytes must be greater than or equal to 0."
            )
        if (
            self.max_total_token_estimate is not None
            and self.max_total_token_estimate < 0
        ):
            raise ValueError(
                "max_total_token_estimate must be greater than or equal to 0."
            )
        if (
            self.max_total_content_size_bytes is not None
            and self.max_total_content_size_bytes < 0
        ):
            raise ValueError(
                "max_total_content_size_bytes must be greater than or equal to 0."
            )


@dataclass(frozen=True)
class PolicyEvaluation:
    """One policy decision attached to a resolved graph."""

    rule: str
    passed: bool
    message: str
    coordinate: SkillCoordinate | None = None


def _normalize_allowed_values(
    values: list[str],
    *,
    ordered_values: tuple[str, ...],
    field_name: str,
) -> list[str]:
    unknown = sorted(set(values) - set(ordered_values))
    if unknown:
        raise ValueError(
            f"{field_name} contains unknown values: {', '.join(unknown)}. "
            f"Expected a subset of {', '.join(ordered_values)}."
        )

    included = set(values)
    return [value for value in ordered_values if value in included]
