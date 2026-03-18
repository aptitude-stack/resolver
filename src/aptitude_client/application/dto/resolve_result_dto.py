"""Result DTOs for exact skill resolution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResolveCoordinateDto(BaseModel):
    """Client-facing exact coordinate."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str


class ResolveSkillSummaryDto(BaseModel):
    """Minimal skill summary exposed by the CLI result."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    rendered_summary: str
    lifecycle_status: str
    trust_tier: str


class ResolveDependencyDto(BaseModel):
    """One direct dependency in the CLI result."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str
    optional: bool = False
    markers: list[str] = Field(default_factory=list)


class ResolveResultDto(BaseModel):
    """Stable exact-resolve result for the initial CLI slice."""

    model_config = ConfigDict(frozen=True)

    requested_query: str | None = None
    resolution_strategy: Literal["exact", "discovery"] | None = None
    requested_coordinate: ResolveCoordinateDto
    selected_coordinate: ResolveCoordinateDto
    skill: ResolveSkillSummaryDto
    dependencies: list[ResolveDependencyDto] = Field(default_factory=list)
    status: Literal["resolved"] = "resolved"
