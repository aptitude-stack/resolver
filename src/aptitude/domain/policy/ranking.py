"""Shared deterministic rank helpers for trust and lifecycle comparisons."""

from __future__ import annotations

from typing import Final


TRUST_TIER_RANKS: Final[dict[str, int]] = {
    "verified": 2,
    "internal": 1,
    "untrusted": 0,
}
LIFECYCLE_STATUS_RANKS: Final[dict[str, int]] = {
    "published": 2,
    "deprecated": 1,
    "archived": 0,
}


def trust_tier_rank(value: str | None) -> int:
    """Return the deterministic rank for one trust tier."""

    if value is None:
        return -1
    return TRUST_TIER_RANKS.get(value, -1)


def lifecycle_status_rank(value: str | None) -> int:
    """Return the deterministic rank for one lifecycle status."""

    if value is None:
        return -1
    return LIFECYCLE_STATUS_RANKS.get(value, -1)
