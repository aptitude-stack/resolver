"""Conflict helpers for deterministic graph resolution."""

from __future__ import annotations

from aptitude_client.domain.errors import VersionConflictError
from aptitude_client.domain.models import SkillCoordinate


def ensure_no_version_conflict(
    selected_versions: dict[str, SkillCoordinate],
    coordinate: SkillCoordinate,
) -> None:
    """Reject the same slug resolving to multiple versions."""

    existing = selected_versions.get(coordinate.slug)
    if existing is not None and existing.version != coordinate.version:
        raise VersionConflictError(
            coordinate.slug,
            [existing.version, coordinate.version],
        )
