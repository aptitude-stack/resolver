"""Application use case for version-aware skill inspection."""

from __future__ import annotations

from typing import Protocol

from aptitude_resolver.application.dto import (
    InspectSkillRequestDto,
    InspectSkillResultDto,
    ResolveCoordinateDto,
)
from aptitude_resolver.application.queries import RankSkillCandidatesQuery
from aptitude_resolver.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    metadata_to_dto,
    trace_to_dto,
    version_to_inspect_dto,
)
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences
from aptitude_resolver.resolution.solver import select_final_candidate


class InspectRegistryPort(Protocol):
    """Registry operations required for inspection."""

    def discover_candidate_slugs(self, query): ...

    def fetch_skill_identity(self, slug: str): ...

    def list_skill_versions(self, slug: str): ...

    def fetch_skill_metadata(self, slug: str, version: str): ...

    def fetch_skill_content(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ): ...


class InspectSkillUseCase:
    """Inspect one selected skill without resolving a dependency graph."""

    def __init__(
        self,
        registry_client: InspectRegistryPort,
        *,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
    ) -> None:
        self._registry_client = registry_client
        self._selection_preferences = selection_preferences or SelectionPreferences()
        self._rank_candidates = RankSkillCandidatesQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=self._selection_preferences,
        )

    def execute(self, request: InspectSkillRequestDto) -> InspectSkillResultDto:
        ranked = self._rank_candidates.execute(
            query=request.query,
            version=request.version,
            interaction_mode=request.interaction_mode,
        )
        effective_interaction_mode = (
            request.interaction_mode or self._selection_preferences.interaction_mode
        )
        trace = list(ranked.trace)
        selection = select_final_candidate(
            query=request.query,
            candidates=ranked.candidates,
            select_slug=request.select_slug,
            interaction_mode=effective_interaction_mode,
            prompt_capable=request.prompt_capable,
            selection_source=request.selection_source,
        )
        trace.extend(selection.trace)
        if selection.selected_candidate is None or selection.selection_mode is None:
            return InspectSkillResultDto(
                requested_query=request.query,
                requested_version=request.version,
                status="selection_required",
                candidates=[candidate_to_dto(item) for item in ranked.candidates],
                trace=[trace_to_dto(item) for item in trace],
            )

        candidate = selection.selected_candidate
        metadata = self._registry_client.fetch_skill_metadata(
            candidate.slug,
            candidate.selected_coordinate.version,
        )
        content = self._registry_client.fetch_skill_content(
            candidate.slug,
            candidate.selected_coordinate.version,
            checksum_algorithm=metadata.content_checksum_algorithm,
            checksum_digest=metadata.content_checksum_digest,
        )
        preview, truncated = _content_preview(content, limit=request.preview_char_limit)
        available_versions = self._registry_client.list_skill_versions(candidate.slug)

        return InspectSkillResultDto(
            requested_query=request.query,
            requested_version=request.version,
            status="inspected",
            selection_mode=selection.selection_mode,
            candidates=[candidate_to_dto(item) for item in ranked.candidates],
            selected_coordinate=ResolveCoordinateDto(
                slug=candidate.slug,
                version=candidate.selected_coordinate.version,
            ),
            skill=metadata_to_dto(metadata),
            available_versions=[version_to_inspect_dto(item) for item in available_versions],
            content_preview=preview,
            content_preview_truncated=truncated,
            trace=[trace_to_dto(item) for item in trace],
        )


def _content_preview(content: str, *, limit: int) -> tuple[str, bool]:
    """Return a bounded preview for terminal inspection surfaces."""

    if len(content) <= limit:
        return content, False
    if limit <= 3:
        return content[:limit], True
    return content[: limit - 3].rstrip() + "...", True
