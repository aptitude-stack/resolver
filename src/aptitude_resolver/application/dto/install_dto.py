"""DTOs for install and local materialization flows."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aptitude_resolver.application.dto.resolve_result_dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    LockfileDto,
    PolicyEvaluationDto,
    ResolvedGraphDto,
    ResolveCoordinateDto,
    TraceEntryDto,
)
from aptitude_resolver.domain.versioning import parse_skill_version


class InstallRequestDto(BaseModel):
    """Install request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    query: str
    target: Path | None = None
    version: str | None = None
    exact: bool = False
    select_slug: str | None = None
    interaction_mode: Literal["auto", "always", "never"] | None = None
    prompt_capable: bool = False
    selection_source: str | None = None
    agents: list[str] = Field(default_factory=lambda: ["codex"])
    scope: Literal["project", "global", "custom"] = "project"
    export_root: Path | None = None
    cwd: Path | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str | None) -> str | None:
        if value is not None:
            parse_skill_version(value)
        return value


class SyncRequestDto(BaseModel):
    """Sync request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    lock_path: Path
    target: Path | None = None


class InstalledSkillDto(BaseModel):
    """One exact coordinate materialized locally."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str
    install_path: str


class ExportedSkillDto(BaseModel):
    """One agent-exported skill directory."""

    model_config = ConfigDict(frozen=True)

    agent: str
    scope: str
    slug: str
    version: str
    destination_path: str
    skill_markdown_path: str


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
    exported_skills: list[ExportedSkillDto] = Field(default_factory=list)
    materialized_root: str | None = None
    lock_path: str | None = None
    export_root: str | None = None
    export_roots: dict[str, str] = Field(default_factory=dict)
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
