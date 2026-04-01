"""Normalize dependency selectors into exact coordinates."""

from __future__ import annotations

from aptitude.domain.errors import UnsupportedDependencyShapeError
from aptitude.domain.models import DependencySpec, SkillCoordinate


def normalize_dependency_selector(
    source: SkillCoordinate,
    dependency: DependencySpec,
) -> SkillCoordinate:
    """Normalize a direct dependency selector into one exact coordinate."""

    if dependency.version is None:
        raise UnsupportedDependencyShapeError(
            source.slug,
            source.version,
            "only exact dependency versions are supported in the current resolver flow",
        )

    return SkillCoordinate(slug=dependency.slug, version=dependency.version)
