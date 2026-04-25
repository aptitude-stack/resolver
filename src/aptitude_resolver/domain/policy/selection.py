"""Selection preference models for profile-aware candidate choice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


VALID_SELECTION_PROFILES: Final[tuple[str, ...]] = (
    "balanced",
    "low-cost",
    "high-trust",
)
VALID_INTERACTION_MODES: Final[tuple[str, ...]] = (
    "auto",
    "always",
    "never",
)


@dataclass(frozen=True)
class SelectionPreferences:
    """Soft user preference inputs that shape ranking and prompting behavior."""

    profile: str = "balanced"
    interaction_mode: str = "auto"
    profile_source: str = "default"
    interaction_mode_source: str = "default"

    def __post_init__(self) -> None:
        if self.profile not in VALID_SELECTION_PROFILES:
            raise ValueError(
                "Unknown selection profile: "
                f"{self.profile}. Expected one of {', '.join(VALID_SELECTION_PROFILES)}."
            )
        if self.interaction_mode not in VALID_INTERACTION_MODES:
            raise ValueError(
                "Unknown interaction mode: "
                f"{self.interaction_mode}. Expected one of {', '.join(VALID_INTERACTION_MODES)}."
            )
