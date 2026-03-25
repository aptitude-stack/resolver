"""DTOs for install and local materialization flows."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aptitude_client.application.dto.resolve_result_dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    LockfileDto,
    PolicyEvaluationDto,
    ResolvedGraphDto,
    ResolveCoordinateDto,
    TraceEntryDto,
)


class InstallRequestDto(BaseModel):
    """Install request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    query: str
    target: Path
    version: str | None = None
    select_slug: str | None = None
    interactive: bool = False
    selection_source: str | None = None


class SyncRequestDto(BaseModel):
    """Sync request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    lock_path: Path
    target: Path


class InstalledSkillDto(BaseModel):
    """One exact coordinate materialized locally."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str
    install_path: str


class InstallResultDto(BaseModel):
    """Install command output."""

    model_config = ConfigDict(frozen=True)

    requested_query: str
    requested_version: str | None = None
    status: Literal["selection_required", "installed"]
    selection_mode: str | None = None
    candidates: list[DiscoveryCandidateDto] = Field(default_factory=list)
    selected_coordinate: ResolveCoordinateDto | None = None
    graph: ResolvedGraphDto | None = None
    lockfile: LockfileDto | None = None
    execution_plan: ExecutionPlanDto | None = None
    installed_skills: list[InstalledSkillDto] = Field(default_factory=list)
    materialized_root: str | None = None
    trace: list[TraceEntryDto] = Field(default_factory=list)
    policy_evaluations: list[PolicyEvaluationDto] = Field(default_factory=list)


class SyncResultDto(BaseModel):
    """Sync command output."""

    model_config = ConfigDict(frozen=True)

    lock_path: str
    requested_query: str
    status: Literal["synced"]
    selection_mode: str | None = None
    selected_coordinate: ResolveCoordinateDto | None = None
    lockfile: LockfileDto
    execution_plan: ExecutionPlanDto
    installed_skills: list[InstalledSkillDto] = Field(default_factory=list)
    materialized_root: str | None = None
    trace: list[TraceEntryDto] = Field(default_factory=list)
