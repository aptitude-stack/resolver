"""Application use case for local skill discovery, resolution, and install."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aptitude_resolver.application.dto import (
    ExportedSkillDto,
    InstallRequestDto,
    InstallResultDto,
    InstalledSkillDto,
    ResolveCoordinateDto,
    ResolveQueryRequestDto,
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
    trace_to_dto,
)
from aptitude_resolver.domain.errors import InvalidInstallTargetError
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences
from aptitude_resolver.execution import (
    MaterializationOptions,
    export_materialized_skills_to_agent_root,
    materialize_lockfile,
    write_install_debug_artifacts,
)
from aptitude_resolver.lockfile import (
    Lockfile,
    load_lockfile,
    merge_lockfiles,
    serialize_lockfile,
)
from aptitude_resolver.shared.config import (
    default_aptitude_state_dir,
    default_install_materialization_root,
    resolve_agent_install_roots,
)
from aptitude_resolver.telemetry import TelemetryCollector, emit_stage_timings


class InstallRegistryPort(Protocol):
    """Registry operations required for install."""

    def discover_candidate_slugs(self, query): ...

    def fetch_skill_identity(self, slug: str): ...

    def list_skill_versions(self, slug: str): ...

    def fetch_skill_metadata(self, slug: str, version: str): ...

    def fetch_direct_dependencies(self, slug: str, version: str): ...

    def fetch_skill_artifact(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> bytes: ...


class InstallSkillUseCase:
    """Resolve a skill query and materialize the result locally."""

    def __init__(
        self,
        registry_client: InstallRegistryPort,
        *,
        materialization_options: MaterializationOptions | None = None,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
    ) -> None:
        self._registry_client = registry_client
        self._materialization_options = (
            materialization_options or MaterializationOptions()
        )
        self._planner = PlanSkillResolutionQuery(
            registry_client,
            policy_context=policy_context or PolicyContext(),
            selection_preferences=selection_preferences or SelectionPreferences(),
        )

    def execute(self, request: InstallRequestDto) -> InstallResultDto:
        telemetry = TelemetryCollector()
        try:
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

            materialization_target = _materialization_target(request)
            export_roots = _export_roots(request)
            with telemetry.measure("materialization"):
                materialization = materialize_lockfile(
                    target=materialization_target,
                    lockfile=plan.lockfile,
                    registry_client=self._registry_client,
                    execution_plan=plan.execution_plan,
                    options=self._materialization_options,
                )
                trace = list(plan.trace)
                trace.extend(materialization.trace)
                write_install_debug_artifacts(
                    target=Path(materialization.materialized_root),
                    graph=plan.graph,
                    trace=trace,
                    policy_evaluations=plan.policy_evaluations,
                )
            exported_skills: list[ExportedSkillDto] = []
            with telemetry.measure("agent_export"):
                for agent, export_root in export_roots.items():
                    export_result = export_materialized_skills_to_agent_root(
                        materialized_root=Path(materialization.materialized_root),
                        lockfile=plan.lockfile,
                        destination_root=export_root,
                        agent=agent,
                        scope=request.scope,
                    )
                    trace.extend(export_result.trace)
                    exported_skills.extend(
                        ExportedSkillDto(
                            agent=item.agent,
                            scope=item.scope,
                            slug=item.slug,
                            version=item.version,
                            destination_path=item.destination_path,
                            skill_markdown_path=item.skill_markdown_path,
                            metadata_path=item.metadata_path,
                        )
                        for item in export_result.exported_skills
                    )
            lock_path = _scope_lock_path(request)
            lockfile = (
                _update_scope_lockfile(lock_path, plan.lockfile)
                if lock_path is not None
                else plan.lockfile
            )
            return InstallResultDto(
                requested_query=plan.requested_query,
                requested_version=plan.requested_version,
                status="installed",
                selection_mode=plan.selection_mode,
                selected_coordinate=ResolveCoordinateDto(
                    slug=plan.graph.root.slug,
                    version=plan.graph.root.version,
                ),
                graph=graph_to_dto(plan.graph),
                lockfile=lockfile_to_dto(lockfile),
                execution_plan=execution_plan_to_dto(materialization.execution_plan),
                installed_skills=[
                    InstalledSkillDto(
                        slug=item.slug,
                        version=item.version,
                        install_path=item.install_path,
                    )
                    for item in materialization.installed_skills
                ],
                exported_skills=exported_skills,
                materialized_root=materialization.materialized_root,
                lock_path=str(lock_path) if lock_path is not None else None,
                export_root=next(iter(export_roots.values())).as_posix()
                if len(export_roots) == 1
                else None,
                export_roots={agent: str(root) for agent, root in export_roots.items()},
                trace=[trace_to_dto(item) for item in trace],
                policy_evaluations=[
                    policy_to_dto(item) for item in plan.policy_evaluations
                ],
            )
        finally:
            emit_stage_timings(telemetry)


def _materialization_target(request: InstallRequestDto) -> Path:
    return (
        request.target.expanduser().resolve()
        if request.target is not None
        else default_install_materialization_root().resolve()
    )


def _export_roots(request: InstallRequestDto) -> dict[str, Path]:
    cwd = request.cwd
    if cwd is None and request.target is not None:
        cwd = request.target.expanduser().resolve().parent
    try:
        return resolve_agent_install_roots(
            agents=request.agents,
            scope=request.scope,
            cwd=cwd,
            export_root=request.export_root,
        )
    except ValueError as exc:
        raise InvalidInstallTargetError(str(exc)) from exc


def _scope_lock_path(request: InstallRequestDto) -> Path | None:
    if request.scope == "global":
        return default_aptitude_state_dir() / "aptitude.lock.json"
    if request.scope == "project":
        project_root = (
            request.cwd.expanduser().resolve() if request.cwd else Path.cwd().resolve()
        )
        return project_root / "aptitude.lock.json"
    return None


def _update_scope_lockfile(path: Path, lockfile: Lockfile) -> Lockfile:
    existing = load_lockfile(path) if path.exists() else None
    merged = merge_lockfiles(existing, lockfile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_lockfile(merged), encoding="utf-8")
    return merged
