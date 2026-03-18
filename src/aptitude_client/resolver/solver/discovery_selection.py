"""Deterministic discovery candidate selection rules."""

from __future__ import annotations

from aptitude_client.domain.errors import DiscoveryAmbiguousMatchError, DiscoveryNoCandidatesError


def select_discovery_candidate(query: str, candidates: list[str]) -> str:
    """Select a single candidate deterministically or raise a structured error."""

    if not candidates:
        raise DiscoveryNoCandidatesError(query)

    if query in candidates:
        return query

    if len(candidates) == 1:
        return candidates[0]

    raise DiscoveryAmbiguousMatchError(query, candidates)
