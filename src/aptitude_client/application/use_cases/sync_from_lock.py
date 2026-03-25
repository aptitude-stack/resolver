"""Application use case for lock-driven sync and materialization."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aptitude_client.application.dto import (
    InstalledSkillDto,
    ResolveCoordinateDto,
    SyncRequestDto,
    SyncResultDto,
)
from aptitude_client.application.use_cases.resolution_mapping import (
    execution_plan_to_dto,
    lockfile_to_dto,
    trace_to_dto,
)
from aptitude_client.domain.errors import InvalidLockfileError
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.execution import materialize_lockfile
from aptitude_client.lockfile import load_lockfile


class SyncRegistryPort(Protocol):
    """Registry operations required for lock-driven sync."""

    def fetch_skill_content(self, slug: str, version: str) -> str: ...


class SyncFromLockUseCase:
    """Materialize a locked system without discovery or resolution."""

    def __init__(self, registry_client: SyncRegistryPort) -> None:
        self._registry_client = registry_client

    def execute(self, request: SyncRequestDto) -> SyncResultDto:
        lock_path = request.lock_path.resolve()
        if not lock_path.exists():
            raise InvalidLockfileError(f"Lockfile not found: {lock_path}")
        if not lock_path.is_file():
            raise InvalidLockfileError(f"Lockfile path is not a file: {lock_path}")

        lockfile = load_lockfile(lock_path)
        trace = [
            TraceEntry(
                stage="lockfile",
                action="load_lockfile",
                message=f"Loaded lockfile from {lock_path}.",
                data={"path": str(lock_path)},
            )
        ]
        materialization = materialize_lockfile(
            target=request.target,
            lockfile=lockfile,
            registry_client=self._registry_client,
        )
        trace.extend(materialization.trace)

        selected_coordinate = _selected_coordinate(lockfile.root.selected_node_id)
        return SyncResultDto(
            lock_path=str(lock_path),
            requested_query=lockfile.root.request,
            status="synced",
            selection_mode=lockfile.root.selection_mode,
            selected_coordinate=selected_coordinate,
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
            materialized_root=materialization.materialized_root,
            trace=[trace_to_dto(item) for item in trace],
        )


def _selected_coordinate(node_id: str) -> ResolveCoordinateDto:
    slug, version = node_id.rsplit("@", maxsplit=1)
    return ResolveCoordinateDto(slug=slug, version=version)
