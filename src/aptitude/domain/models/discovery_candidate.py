"""Domain model for enriched discovery candidates."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude.domain.models.skill_coordinate import SkillCoordinate
from aptitude.domain.models.version_summary import VersionSummary


@dataclass(frozen=True)
class DiscoveryCandidate:
    """Enriched candidate with selected version preview and ranking details."""

    slug: str
    selected_version: VersionSummary
    labels: list[str]
    matched_labels: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)
    ranking_position: int | None = None
    selection_details: list[str] = field(default_factory=list)
    selection_reason: str | None = None

    @property
    def selected_coordinate(self) -> SkillCoordinate:
        return self.selected_version.coordinate
