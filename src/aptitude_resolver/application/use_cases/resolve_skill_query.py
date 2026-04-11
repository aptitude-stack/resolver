"""Application use case for discovery-backed skill resolution."""

from __future__ import annotations

from typing import Protocol

from aptitude_resolver.application.dto import (
    ResolveCoordinateDto,
    ResolveQueryRequestDto,
    ResolveQueryResultDto,
)
from aptitude_resolver.application.queries import (
    PlanSkillResolutionQuery,
    SelectionRequiredResult,
)
from aptitude_resolver.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    execution_plan_to_dto,
    graph_to_dto,
    lockfile_to_dto,
    policy_to_dto,
    selected_skill_to_dto,
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
    ) -> None:
        self._planner = PlanSkillResolutionQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=selection_preferences or SelectionPreferences(),
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
        return ResolveQueryResultDto(
            requested_query=plan.requested_query,
            requested_version=plan.requested_version,
            status="resolved",
            selection_mode=plan.selection_mode,
            candidates=[candidate_to_dto(item) for item in plan.candidates],
            selected_coordinate=ResolveCoordinateDto(
                slug=plan.graph.root.slug,
                version=plan.graph.root.version,
            ),
            selected_skill=selected_skill_to_dto(plan),
            graph=graph_to_dto(plan.graph),
            lockfile=lockfile_to_dto(plan.lockfile),
            execution_plan=execution_plan_to_dto(plan.execution_plan),
            trace=[trace_to_dto(item) for item in plan.trace],
            policy_evaluations=[
                policy_to_dto(item) for item in plan.policy_evaluations
            ],
        )
