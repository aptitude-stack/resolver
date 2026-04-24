"""Application use case for ranked terminal discovery."""

from __future__ import annotations

from typing import Protocol

from aptitude_resolver.application.dto import SearchSkillsRequestDto, SearchSkillsResultDto
from aptitude_resolver.application.queries import RankSkillCandidatesQuery
from aptitude_resolver.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    trace_to_dto,
)
from aptitude_resolver.domain.models import (
    DiscoveryQuery,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences


class SearchRegistryPort(Protocol):
    """Registry operations required for search."""

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]: ...

    def fetch_skill_identity(self, slug: str) -> SkillIdentity: ...

    def list_skill_versions(self, slug: str) -> list[VersionSummary]: ...

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata: ...


class SearchSkillsUseCase:
    """Search skills without materializing or resolving a dependency graph."""

    def __init__(
        self,
        registry_client: SearchRegistryPort,
        *,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
    ) -> None:
        self._rank_candidates = RankSkillCandidatesQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=selection_preferences or SelectionPreferences(),
        )

    def execute(self, request: SearchSkillsRequestDto) -> SearchSkillsResultDto:
        ranked = self._rank_candidates.execute(query=request.query)
        return SearchSkillsResultDto(
            requested_query=ranked.requested_query,
            status="found",
            candidates=[candidate_to_dto(item) for item in ranked.candidates],
            trace=[trace_to_dto(item) for item in ranked.trace],
        )
