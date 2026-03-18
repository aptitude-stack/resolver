"""Pydantic transport models for the runtime registry contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransportChecksum(BaseModel):
    """Checksum payload from the registry."""

    model_config = ConfigDict(extra="ignore")

    algorithm: str
    digest: str


class TransportContent(BaseModel):
    """Content subsection of the metadata payload."""

    model_config = ConfigDict(extra="ignore")

    checksum: TransportChecksum
    rendered_summary: str


class TransportMetadata(BaseModel):
    """Metadata subsection of the metadata payload."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    tags: list[str]


class MetadataResponse(BaseModel):
    """Runtime-tested exact metadata payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    version: str
    content: TransportContent
    metadata: TransportMetadata
    lifecycle_status: str
    trust_tier: str
    published_at: str


class DependencySelector(BaseModel):
    """Direct dependency selector from the resolution payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    version: str
    optional: bool = False
    markers: list[str] = Field(default_factory=list)


class DirectDependenciesResponse(BaseModel):
    """Runtime-tested direct dependency payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    version: str
    depends_on: list[DependencySelector] = Field(default_factory=list)


class DiscoveryResponse(BaseModel):
    """Runtime-tested discovery payload."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[str] = Field(default_factory=list)


class TransportError(BaseModel):
    """Normalized error payload from the registry."""

    model_config = ConfigDict(extra="ignore")

    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ErrorEnvelope(BaseModel):
    """Normalized error envelope from the registry."""

    model_config = ConfigDict(extra="ignore")

    error: TransportError
