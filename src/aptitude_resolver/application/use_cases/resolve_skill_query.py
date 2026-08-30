"""Application use case for discovery-backed skill resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aptitude_resolver.application.dto import (
    ResolveQueryRequestDto,
    ResolveQueryResultDto,
)
from aptitude_resolver.application.queries import (
    PlanSkillResolutionQuery,
    SelectionRequiredResult,
)
from aptitude_resolver.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    resolution_to_dto,
    trace_to_dto,
)
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences


class ResolveRegistryPort(Protocol):
    """Registry operations required for discovery and recursive resolution."""

    def discover_candidate_slugs(self, query): ...

    def fetch_skill_identity(self, slug: str): ...

    def list_skill_versions(self, slug: str): ...

    def fetch_skill_metadata(self, slug: str, version: str): ...

    def fetch_direct_dependencies(self, slug: str, version: str): ...


class ResolveSkillQueryUseCase:
    """Resolve user queries into deterministic recursive graphs."""

    def __init__(
        self,
        registry_client: ResolveRegistryPort,
        *,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
        cwd: Path | None = None,
    ) -> None:
        self._planner = PlanSkillResolutionQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=selection_preferences or SelectionPreferences(),
            cwd=cwd,
        )

    def execute(self, request: ResolveQueryRequestDto) -> ResolveQueryResultDto:
        plan = self._planner.execute(request)
        if isinstance(plan, SelectionRequiredResult):
            return ResolveQueryResultDto(
                requested_query=plan.requested_query,
                requested_version=plan.requested_version,
                status="selection_required",
                candidates=[candidate_to_dto(item) for item in plan.candidates],
                trace=[trace_to_dto(item) for item in plan.trace],
            )
        return resolution_to_dto(plan)
