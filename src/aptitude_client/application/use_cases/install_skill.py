"""Application use case for local skill discovery, resolution, and install."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aptitude_client.application.dto import (
    InstallRequestDto,
    InstallResultDto,
    InstalledSkillDto,
    ResolveQueryRequestDto,
)
from aptitude_client.application.queries import PlanSkillResolutionQuery, SelectionRequiredResult
from aptitude_client.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    execution_plan_to_dto,
    graph_to_dto,
    lockfile_to_dto,
    policy_to_dto,
    trace_to_dto,
)
from aptitude_client.domain.policy import PolicyContext, SelectionPreferences
from aptitude_client.execution import materialize_lockfile, write_install_debug_artifacts


class InstallRegistryPort(Protocol):
    """Registry operations required for install."""

    def discover_candidate_slugs(self, query): ...

    def fetch_skill_identity(self, slug: str): ...

    def list_skill_versions(self, slug: str): ...

    def fetch_skill_metadata(self, slug: str, version: str): ...

    def fetch_direct_dependencies(self, slug: str, version: str): ...

    def fetch_skill_content(self, slug: str, version: str): ...


class InstallSkillUseCase:
    """Resolve a skill query and materialize the result locally."""

    def __init__(
        self,
        registry_client: InstallRegistryPort,
        *,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
    ) -> None:
        self._registry_client = registry_client
        self._planner = PlanSkillResolutionQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=selection_preferences or SelectionPreferences(),
        )

    def execute(self, request: InstallRequestDto) -> InstallResultDto:
        plan = self._planner.execute(
            ResolveQueryRequestDto(
                query=request.query,
                version=request.version,
                select_slug=request.select_slug,
                interaction_mode=request.interaction_mode,
                prompt_capable=request.prompt_capable,
                selection_source=request.selection_source,
            )
        )
        if isinstance(plan, SelectionRequiredResult):
            return InstallResultDto(
                requested_query=plan.requested_query,
                requested_version=plan.requested_version,
                status="selection_required",
                candidates=[candidate_to_dto(item) for item in plan.candidates],
                trace=[trace_to_dto(item) for item in plan.trace],
            )

        materialization = materialize_lockfile(
            target=request.target,
            lockfile=plan.lockfile,
            registry_client=self._registry_client,
            execution_plan=plan.execution_plan,
        )
        trace = list(plan.trace)
        trace.extend(materialization.trace)
        write_install_debug_artifacts(
            target=Path(materialization.materialized_root),
            graph=plan.graph,
            trace=trace,
            policy_evaluations=plan.policy_evaluations,
        )
        return InstallResultDto(
            requested_query=plan.requested_query,
            requested_version=plan.requested_version,
            status="installed",
            selection_mode=plan.selection_mode,
            selected_coordinate={
                "slug": plan.graph.root.slug,
                "version": plan.graph.root.version,
            },
            graph=graph_to_dto(plan.graph),
            lockfile=lockfile_to_dto(plan.lockfile),
            execution_plan=execution_plan_to_dto(materialization.execution_plan),
            installed_skills=[
                InstalledSkillDto(
                    slug=item.slug,
                    version=item.version,
                    install_path=item.install_path,
                )
                for item in materialization.installed_skills
            ],
            materialized_root=materialization.materialized_root,
            trace=[trace_to_dto(item) for item in trace],
            policy_evaluations=[policy_to_dto(item) for item in plan.policy_evaluations],
        )
