"""Resolver-owned final candidate selection for ranked discovery results."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptitude_client.domain.errors import (
    InteractiveSelectionUnavailableError,
    SelectionSlugNotFoundError,
)
from aptitude_client.domain.models import DiscoveryCandidate
from aptitude_client.domain.tracing import TraceEntry


@dataclass(frozen=True)
class FinalCandidateSelection:
    """One resolver-owned final candidate selection outcome."""

    selected_candidate: DiscoveryCandidate | None
    selection_mode: str | None
    trace: list[TraceEntry] = field(default_factory=list)


def select_final_candidate(
    *,
    query: str,
    candidates: list[DiscoveryCandidate],
    select_slug: str | None,
    interaction_mode: str,
    prompt_capable: bool,
    selection_source: str | None = None,
) -> FinalCandidateSelection:
    """Select the winning candidate from an already-ranked candidate list."""

    if select_slug is not None:
        candidate = next((item for item in candidates if item.slug == select_slug), None)
        if candidate is None:
            raise SelectionSlugNotFoundError(
                query,
                select_slug,
                [item.slug for item in candidates],
            )
        selection_mode = (
            "interactive_choice"
            if selection_source == "interactive"
            else "explicit_slug"
        )
        return FinalCandidateSelection(
            selected_candidate=candidate,
            selection_mode=selection_mode,
        )

    if len(candidates) == 1:
        return FinalCandidateSelection(
            selected_candidate=candidates[0],
            selection_mode="single_candidate",
        )

    if interaction_mode == "always":
        if not prompt_capable:
            raise InteractiveSelectionUnavailableError(query)
        return FinalCandidateSelection(
            selected_candidate=None,
            selection_mode=None,
        )

    if interaction_mode == "auto" and prompt_capable:
        return FinalCandidateSelection(
            selected_candidate=None,
            selection_mode=None,
        )

    candidate = candidates[0]
    return FinalCandidateSelection(
        selected_candidate=candidate,
        selection_mode="non_interactive_top_ranked",
        trace=[
            TraceEntry(
                stage="selection",
                action="auto_select_top_ranked",
                message=(
                    "Multiple candidates remained in non-interactive mode; selected the top-ranked candidate deterministically."
                ),
                data={
                    "slug": candidate.slug,
                    "version": candidate.selected_coordinate.version,
                },
            )
        ],
    )
