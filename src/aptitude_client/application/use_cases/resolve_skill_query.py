"""Application use case for discovery-backed skill resolution."""

from __future__ import annotations

from typing import Protocol

from aptitude_client.application.dto import ResolveQueryRequestDto, ResolveRequestDto, ResolveResultDto
from aptitude_client.domain.errors import SkillNotFoundError, VersionSelectionUnavailableError
from aptitude_client.application.use_cases.resolve_exact_skill import ResolveExactSkillUseCase, RegistryReadPort
from aptitude_client.resolver.solver import select_discovery_candidate


class DiscoveryRegistryPort(RegistryReadPort, Protocol):
    """Registry operations needed for query-based resolution."""

    def discover_candidates(self, query: str) -> list[str]: ...


class ResolveSkillQueryUseCase:
    """Resolve either exact slugs or discovery-backed user queries."""

    def __init__(self, registry_client: DiscoveryRegistryPort) -> None:
        self._registry_client = registry_client
        self._exact_use_case = ResolveExactSkillUseCase(registry_client)

    def execute(self, request: ResolveQueryRequestDto) -> ResolveResultDto:
        if request.version is None:
            raise VersionSelectionUnavailableError(request.query)

        if self._should_discover_first(request.query):
            return self._resolve_via_discovery(request)

        try:
            result = self._exact_use_case.execute(
                ResolveRequestDto(slug=request.query, version=request.version)
            )
        except SkillNotFoundError:
            return self._resolve_via_discovery(request)

        return result

    def _resolve_via_discovery(self, request: ResolveQueryRequestDto) -> ResolveResultDto:
        assert request.version is not None

        candidates = self._registry_client.discover_candidates(request.query)
        selected_slug = select_discovery_candidate(request.query, candidates)

        result = self._exact_use_case.execute(
            ResolveRequestDto(slug=selected_slug, version=request.version)
        )
        return result.model_copy(
            update={
                "requested_query": request.query,
                "resolution_strategy": "discovery",
            }
        )

    @staticmethod
    def _should_discover_first(query: str) -> bool:
        return any(character.isspace() for character in query)
