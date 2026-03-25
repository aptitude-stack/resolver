"""Request DTOs for discovery-backed skill resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResolveQueryRequestDto(BaseModel):
    """Query-driven input for discovery-backed resolution."""

    model_config = ConfigDict(frozen=True)

    query: str
    version: str | None = None
    select_slug: str | None = None
    interactive: bool = False
    selection_source: str | None = None
