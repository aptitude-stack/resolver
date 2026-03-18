"""Request DTOs for exact skill resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResolveRequestDto(BaseModel):
    """Exact coordinate input for the first resolve flow."""

    model_config = ConfigDict(frozen=True)

    slug: str
    version: str


class ResolveQueryRequestDto(BaseModel):
    """Query-driven input for discovery-backed resolution."""

    model_config = ConfigDict(frozen=True)

    query: str
    version: str | None = None
