"""Application DTOs for effective client policy inspection."""

from __future__ import annotations

from pydantic import BaseModel


class SelectionConfigSnapshotDto(BaseModel):
    """One raw or effective selection snapshot."""

    profile: str | None = None
    interaction_mode: str | None = None
    profile_source: str | None = None
    interaction_mode_source: str | None = None


class PolicyConfigSnapshotDto(BaseModel):
    """One raw or effective policy snapshot."""

    source: str | None = None
    allowed_lifecycle_statuses: list[str] | None = None
    allowed_trust_tiers: list[str] | None = None
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None
    max_total_token_estimate: int | None = None
    max_total_content_size_bytes: int | None = None


class ConfigLayerDto(BaseModel):
    """One configuration layer that may contribute to effective settings."""

    source: str
    label: str
    path: str | None = None
    active: bool
    selection: SelectionConfigSnapshotDto | None = None
    policy: PolicyConfigSnapshotDto | None = None


class PolicyMergeSemanticsDto(BaseModel):
    """Human-readable merge rules for policy inspection output."""

    selection_precedence: list[str]
    policy_application_order: list[str]
    selection_rule: str
    policy_rule: str


class EffectivePolicyReportDto(BaseModel):
    """Full inspection payload for effective client policy and preferences."""

    cwd: str
    effective_selection: SelectionConfigSnapshotDto
    effective_policy: PolicyConfigSnapshotDto
    layers: list[ConfigLayerDto]
    semantics: PolicyMergeSemanticsDto
