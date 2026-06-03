"""Pydantic request models for the Aptitude MCP tools."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseFormat(str, Enum):
    """Supported MCP response formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    TOON = "toon"


class _StrictInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class _WorkflowPolicyInput(_StrictInput):
    selection_profile: str | None = Field(
        default=None,
        description="Optional selection profile such as balanced, low-cost, or high-trust.",
    )
    interaction_mode: Literal["auto", "always", "never"] | None = Field(
        default="never",
        description="Candidate ambiguity behavior. MCP defaults to never to avoid interactive prompts.",
    )
    allowed_trust_tiers: list[str] | None = Field(
        default=None,
        description="Optional trust-tier allow list applied as a one-call policy override.",
    )
    allowed_lifecycle_statuses: list[str] | None = Field(
        default=None,
        description="Optional lifecycle-status allow list applied as a one-call policy override.",
    )
    max_token_estimate: int | None = Field(
        default=None,
        ge=0,
        description="Optional per-skill token-estimate ceiling.",
    )
    max_content_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Optional per-skill content-size ceiling in bytes.",
    )


class SearchSkillsInput(_WorkflowPolicyInput):
    """Input for the discovery-only search tool."""

    query: str = Field(..., min_length=1, max_length=500, description="Skill search query.")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum candidates to return.")
    offset: int = Field(default=0, ge=0, description="Number of candidates to skip.")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Response format: markdown, json, or toon.",
    )


class InspectSkillInput(_WorkflowPolicyInput):
    """Input for the selected-skill inspection tool."""

    query: str = Field(..., min_length=1, max_length=500, description="Skill query or slug.")
    version: str | None = Field(default=None, description="Optional exact version.")
    select_slug: str | None = Field(
        default=None,
        description="Explicit slug to use when a query returns multiple candidates.",
    )
    preview_char_limit: int = Field(
        default=4000,
        ge=0,
        le=20000,
        description="Maximum skill content-preview characters to return.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ResolveSkillInput(_WorkflowPolicyInput):
    """Input for deterministic fresh planning without materialization."""

    query: str = Field(..., min_length=1, max_length=500, description="Skill query.")
    version: str | None = Field(default=None, description="Optional requested version.")
    select_slug: str | None = Field(default=None, description="Optional explicit selected slug.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ShowPolicyInput(_StrictInput):
    """Input for effective policy inspection."""

    cwd: Path | None = Field(
        default=None,
        description="Optional workspace directory used for config discovery.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class PreviewInstallDestinationsInput(_StrictInput):
    """Input for previewing agent install destinations without writing files."""

    agents: list[str] | None = Field(
        default=None,
        description="Agent targets to preview. Use ['*'] for all supported agents.",
    )
    scope: Literal["project", "global", "custom"] | None = Field(
        default=None,
        description="Install scope to preview: project, global, or custom.",
    )
    cwd: Path | None = Field(
        default=None,
        description="Workspace directory used for project-scope destinations.",
    )
    export_root: Path | None = Field(
        default=None,
        description="Custom export root used with scope=custom.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class InstallSkillInput(_WorkflowPolicyInput):
    """Input for fresh planning plus agent-aware skill export."""

    query: str = Field(..., min_length=1, max_length=500, description="Skill query.")
    agents: list[str] | None = Field(
        default=None,
        description="Explicit agent targets. Use ['*'] for all supported agents.",
    )
    scope: Literal["project", "global", "custom"] | None = Field(
        default=None,
        description="Explicit install scope: project, global, or custom.",
    )
    cwd: Path | None = Field(
        default=None,
        description="Workspace directory used for project-scope destinations.",
    )
    export_root: Path | None = Field(
        default=None,
        description="Custom export root used with scope=custom.",
    )
    version: str | None = Field(default=None, description="Optional requested version.")
    select_slug: str | None = Field(default=None, description="Optional explicit selected slug.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SyncLockInput(_StrictInput):
    """Input for lock-driven local materialization."""

    lock_path: Path = Field(..., description="Path to an existing Aptitude lockfile.")
    target: Path = Field(..., description="Explicit directory where locked skills are materialized.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("lock_path")
    @classmethod
    def _lock_path_must_not_be_empty(cls, value: Path) -> Path:
        if not str(value).strip():
            raise ValueError("lock_path is required")
        return value
