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
    size_bytes: int | None = None
    rendered_summary: str | None = None


class TransportMetadata(BaseModel):
    """Metadata subsection of the metadata payload."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    tags: list[str]
    headers: dict[str, Any] = Field(default_factory=dict)
    inputs_schema: dict[str, Any] | None = None
    outputs_schema: dict[str, Any] | None = None
    token_estimate: int | None = None
    maturity_score: float | None = None
    security_score: float | None = None


class MetadataResponse(BaseModel):
    """Exact immutable metadata payload."""

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
    version: str | None = None
    version_constraint: str | None = None
    optional: bool = False
    markers: list[str] = Field(default_factory=list)


class DirectDependenciesResponse(BaseModel):
    """Direct dependency payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    version: str
    depends_on: list[DependencySelector] = Field(default_factory=list)


class DiscoveryResponse(BaseModel):
    """Runtime discovery payload."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[str] = Field(default_factory=list)


class SkillVersionListEntryResponse(BaseModel):
    """Compact immutable version entry returned by the live list endpoint."""

    model_config = ConfigDict(extra="ignore")

    version: str
    lifecycle_status: str | None = None
    trust_tier: str | None = None
    published_at: str | None = None
    is_current_default: bool = False


class SkillVersionListResponse(BaseModel):
    """Version list payload for one skill identity."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    versions: list[SkillVersionListEntryResponse] = Field(default_factory=list)


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
