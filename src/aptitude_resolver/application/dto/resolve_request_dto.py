"""Request DTOs for discovery-backed skill resolution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from aptitude_resolver.domain.versioning import parse_skill_version


class ResolveQueryRequestDto(BaseModel):
    """Query-driven input for discovery-backed resolution."""

    model_config = ConfigDict(frozen=True)

    query: str
    version: str | None = None
    exact: bool = False
    select_slug: str | None = None
    interaction_mode: Literal["auto", "always", "never"] | None = None
    prompt_capable: bool = False
    selection_source: str | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str | None) -> str | None:
        if value is not None:
            parse_skill_version(value)
        return value
