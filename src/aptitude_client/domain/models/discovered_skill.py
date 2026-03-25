"""Domain model for one skill discovered before resolver-owned version selection."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_client.domain.models.version_summary import VersionSummary


@dataclass(frozen=True)
class DiscoveredSkill:
    """One discovered skill identity plus the versions visible to the client."""

    slug: str
    available_versions: list[VersionSummary] = field(default_factory=list)
