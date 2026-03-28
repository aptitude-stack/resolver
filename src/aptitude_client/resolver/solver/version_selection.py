"""Deterministic client-side version selection."""

from __future__ import annotations

from packaging.version import Version

from aptitude_client.domain.models import VersionSummary


TRUST_RANK = {"verified": 2, "internal": 1, "untrusted": 0}
LIFECYCLE_RANK = {"published": 2, "deprecated": 1, "archived": 0}


def select_preferred_version(
    versions: list[VersionSummary],
    *,
    allowed_lifecycle_statuses: list[str] | None = None,
) -> VersionSummary:
    """Select one immutable version using deterministic client-owned rules."""

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
            LIFECYCLE_RANK.get(version.lifecycle_status, -1),
            TRUST_RANK.get(version.trust_tier, -1),
            Version(version.coordinate.version),
            version.published_at,
            version.coordinate.slug,
            version.coordinate.version,
        ),
        reverse=True,
    )[0]
