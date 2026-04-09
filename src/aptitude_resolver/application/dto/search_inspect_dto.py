"""DTOs for terminal discovery and inspection flows."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aptitude_resolver.application.dto.resolve_result_dto import (
    DiscoveryCandidateDto,
    ResolveCoordinateDto,
    TraceEntryDto,
)


class SearchSkillsRequestDto(BaseModel):
    """Discovery-only request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    query: str


class SearchSkillsResultDto(BaseModel):
    """Discovery-only result shown to the user."""

    model_config = ConfigDict(frozen=True)

    requested_query: str
    status: Literal["found"]
    candidates: list[DiscoveryCandidateDto] = Field(default_factory=list)
    trace: list[TraceEntryDto] = Field(default_factory=list)


class InspectSkillRequestDto(BaseModel):
    """Inspection request coming from the CLI layer."""

    model_config = ConfigDict(frozen=True)

    query: str
    version: str | None = None
    select_slug: str | None = None
    interaction_mode: Literal["auto", "always", "never"] | None = None
    prompt_capable: bool = False
    selection_source: str | None = None
    preview_char_limit: int = 4000


class InspectVersionDto(BaseModel):
    """One available immutable version exposed by inspect."""

    model_config = ConfigDict(frozen=True)

    version: str
    lifecycle_status: str
    trust_tier: str
    published_at: str
    is_current_default: bool = False
    token_estimate: int | None = None
    content_size_bytes: int | None = None
    rendered_summary: str | None = None


class InspectSkillSummaryDto(BaseModel):
    """Fuller skill summary for inspection surfaces."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    runtime: str | None = None
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str
    published_at: str
    token_estimate: int | None = None
    content_size_bytes: int | None = None
    maturity_score: float | None = None
    security_score: float | None = None
    content_checksum_algorithm: str | None = None
    content_checksum_digest: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class InspectSkillResultDto(BaseModel):
    """Inspection result for one selected skill."""

    model_config = ConfigDict(frozen=True)

    requested_query: str
    requested_version: str | None = None
    status: Literal["selection_required", "inspected"]
    selection_mode: str | None = None
    candidates: list[DiscoveryCandidateDto] = Field(default_factory=list)
    selected_coordinate: ResolveCoordinateDto | None = None
    skill: InspectSkillSummaryDto | None = None
    available_versions: list[InspectVersionDto] = Field(default_factory=list)
    content_preview: str | None = None
    content_preview_truncated: bool = False
    trace: list[TraceEntryDto] = Field(default_factory=list)
