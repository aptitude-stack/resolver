"""Normalize dependency selectors into exact coordinates."""

from __future__ import annotations

from aptitude_resolver.domain.errors import UnsupportedDependencyShapeError
from aptitude_resolver.domain.models import DependencySpec, SkillCoordinate
from aptitude_resolver.domain.versioning import parse_skill_version


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

    try:
        parse_skill_version(dependency.version)
    except ValueError as exc:
        raise UnsupportedDependencyShapeError(
            source.slug,
            source.version,
            f"dependency version must be strict SemVer: {dependency.version}",
        ) from exc

    return SkillCoordinate(slug=dependency.slug, version=dependency.version)
