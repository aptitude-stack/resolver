"""Deterministic resolver-side version selection."""

from __future__ import annotations

from packaging.version import Version

from aptitude_resolver.domain.models import VersionSummary
from aptitude_resolver.domain.policy import lifecycle_status_rank, trust_tier_rank


def select_preferred_version(
    versions: list[VersionSummary],
    *,
    allowed_lifecycle_statuses: list[str] | None = None,
) -> VersionSummary:
    """Select one immutable version using deterministic resolver-owned rules."""

    if not versions:
        raise ValueError("At least one version is required for selection.")

    filtered = list(versions)
    if allowed_lifecycle_statuses:
        filtered = [
            version
            for version in filtered
            if version.lifecycle_status in allowed_lifecycle_statuses
        ] or filtered

    return sorted(
        filtered,
        key=lambda version: (
            int(version.is_current_default),
            lifecycle_status_rank(version.lifecycle_status),
            trust_tier_rank(version.trust_tier),
            Version(version.coordinate.version),
            version.published_at,
            version.coordinate.slug,
            version.coordinate.version,
        ),
        reverse=True,
    )[0]
