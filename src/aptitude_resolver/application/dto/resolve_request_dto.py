"""Request DTOs for discovery-backed skill resolution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResolveQueryRequestDto(BaseModel):
    """Query-driven input for discovery-backed resolution."""

    model_config = ConfigDict(frozen=True)

    query: str
    version: str | None = None
    select_slug: str | None = None
    interaction_mode: Literal["auto", "always", "never"] | None = None
    prompt_capable: bool = False
    selection_source: str | None = None
