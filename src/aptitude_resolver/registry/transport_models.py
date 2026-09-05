"""Pydantic transport models for the runtime registry contract."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aptitude_resolver.domain.versioning import (
    parse_semver_constraint,
    parse_skill_version,
)


SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,127})$"
MARKER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


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
    description: str | None
    tags: list[str]
    headers: dict[str, Any] = Field(default_factory=dict)
    token_estimate: int | None = None
    maturity_score: float | None = None
    security_score: float | None = None
    overall_score: float | None = None


class MetadataResponse(BaseModel):
    """Exact immutable metadata payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1, max_length=128, pattern=SLUG_PATTERN)
    version: str
    install_count: int | None = None
    star_count: int | None = None
    content: TransportContent
    metadata: TransportMetadata
    lifecycle_status: str
    trust_tier: str
    published_at: str

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        parse_skill_version(value)
        return value


class DependencySelector(BaseModel):
    """Direct dependency selector from the resolution payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1, max_length=128, pattern=SLUG_PATTERN)
    version: str | None = None
    version_constraint: str | None = Field(default=None, max_length=200)
    optional: bool | None = False
    markers: list[str] = Field(default_factory=list)

    @field_validator("optional", mode="before")
    @classmethod
    def _default_null_optional(cls, value: object) -> object:
        if value is None:
            return False
        return value

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str | None) -> str | None:
        if value is not None:
            parse_skill_version(value)
        return value

    @field_validator("version_constraint")
    @classmethod
    def _validate_version_constraint(cls, value: str | None) -> str | None:
        if value is not None:
            parse_semver_constraint(value)
        return value

    @field_validator("markers")
    @classmethod
    def _validate_markers(cls, value: list[str]) -> list[str]:
        for marker in value:
            if MARKER_PATTERN.fullmatch(marker) is None:
                raise ValueError("Dependency marker does not match the registry pattern.")
        return value

    @model_validator(mode="after")
    def _validate_selector_shape(self) -> DependencySelector:
        if (self.version is None) == (self.version_constraint is None):
            raise ValueError(
                "Dependency selector must include exactly one of `version` or `version_constraint`."
            )
        return self


class DirectDependenciesResponse(BaseModel):
    """Direct dependency payload."""

    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1, max_length=128, pattern=SLUG_PATTERN)
    version: str
    depends_on: list[DependencySelector] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        parse_skill_version(value)
        return value


class DiscoveryResponse(BaseModel):
    """Runtime discovery payload."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[str] = Field(default_factory=list)

    @field_validator("candidates")
    @classmethod
    def _validate_candidates(cls, value: list[str]) -> list[str]:
        pattern = re.compile(SLUG_PATTERN)
        for slug in value:
            if pattern.fullmatch(slug) is None:
                raise ValueError("Discovery candidate slug does not match the registry pattern.")
        return value


class SkillVersionListEntryResponse(BaseModel):
    """Compact immutable version entry returned by the live list endpoint."""

    model_config = ConfigDict(extra="ignore")

    version: str
    lifecycle_status: str | None = None
    trust_tier: str | None = None
    published_at: str | None = None
    is_current_default: bool = False

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        parse_skill_version(value)
        return value


class SkillVersionListResponse(BaseModel):
    """Version list payload for one skill identity."""

    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1, max_length=128, pattern=SLUG_PATTERN)
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
