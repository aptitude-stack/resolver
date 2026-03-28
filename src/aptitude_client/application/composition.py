"""Application-owned wiring helpers for configured use cases."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aptitude_client.application.use_cases import (
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SyncFromLockUseCase,
)
from aptitude_client.domain.errors import InvalidClientConfigurationError
from aptitude_client.domain.policy import PolicyContext, SelectionPreferences
from aptitude_client.registry import RegistryClient
from aptitude_client.shared.config import (
    AptitudeConfig,
    PolicyConfig,
    SelectionConfig,
    Settings,
    load_user_aptitude_config,
    load_workspace_aptitude_config,
    read_env_selection_overrides,
)


def build_registry_client() -> tuple[RegistryClient, Callable[[], None]]:
    """Create a registry client and its cleanup hook."""

    registry_client = RegistryClient(Settings())
    return registry_client, registry_client.close


def _effective_selection_preferences(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    cwd: Path | None = None,
) -> SelectionPreferences:
    """Build one effective selection-preference object from all current sources."""

    default_preferences = SelectionPreferences()
    sources = [
        (
            "user_config",
            "user config",
            _selection_config(load_user_aptitude_config, "user config"),
        ),
        (
            "workspace_config",
            "workspace config",
            _selection_config(
                lambda: load_workspace_aptitude_config(cwd),
                "workspace config",
            ),
        ),
        ("environment", "environment", read_env_selection_overrides()),
        (
            "cli_override",
            "CLI override",
            SelectionConfig(
                profile=selection_profile_override,
                interaction_mode=interaction_mode_override,
            )
            if selection_profile_override is not None or interaction_mode_override is not None
            else None
        ),
    ]

    effective_profile = default_preferences.profile
    effective_profile_source = "default"
    effective_profile_error_source = "default"
    effective_interaction_mode = default_preferences.interaction_mode
    effective_interaction_source = "default"
    effective_interaction_error_source = "default"

    for source_id, _source_name, selection_config in sources:
        if selection_config is None:
            continue
        if selection_config.profile is not None:
            effective_profile = selection_config.profile
            effective_profile_source = source_id
            effective_profile_error_source = _source_name
        if selection_config.interaction_mode is not None:
            effective_interaction_mode = selection_config.interaction_mode
            effective_interaction_source = source_id
            effective_interaction_error_source = _source_name

    try:
        return SelectionPreferences(
            profile=effective_profile,
            interaction_mode=effective_interaction_mode,
            profile_source=effective_profile_source,
            interaction_mode_source=effective_interaction_source,
        )
    except ValueError as exc:
        source = (
            effective_profile_error_source
            if "profile" in str(exc).lower()
            else effective_interaction_error_source
        )
        raise InvalidClientConfigurationError(source, str(exc)) from exc


def _effective_policy_context(
    *,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> PolicyContext:
    """Build one effective policy object from defaults, workspace policy, and CLI."""

    default_policy = PolicyContext()
    workspace_policy_config = _policy_config(
        lambda: load_workspace_aptitude_config(cwd),
        "workspace config",
    )
    policy = _apply_policy_override(default_policy, workspace_policy_config, source="workspace_config")
    cli_policy_config = PolicyConfig(
        allowed_trust_tiers=allowed_trust_tiers_override,
        allowed_lifecycle_statuses=allowed_lifecycle_statuses_override,
        max_token_estimate=max_token_estimate_override,
        max_content_size_bytes=max_content_size_bytes_override,
    )
    has_cli_override = any(
        value is not None
        for value in (
            allowed_trust_tiers_override,
            allowed_lifecycle_statuses_override,
            max_token_estimate_override,
            max_content_size_bytes_override,
        )
    )
    if has_cli_override:
        policy = _apply_policy_override(policy, cli_policy_config, source="cli_override")

    return policy


def _apply_policy_override(
    base: PolicyContext,
    override: PolicyConfig | None,
    *,
    source: str,
) -> PolicyContext:
    """Apply one stricter-only policy override layer onto an existing policy."""

    if override is None:
        return base

    try:
        validated_override = PolicyContext(
            profile=base.profile,
            source=source,
            allowed_lifecycle_statuses=(
                list(override.allowed_lifecycle_statuses)
                if override.allowed_lifecycle_statuses is not None
                else list(base.allowed_lifecycle_statuses)
            ),
            allowed_trust_tiers=(
                list(override.allowed_trust_tiers)
                if override.allowed_trust_tiers is not None
                else list(base.allowed_trust_tiers)
            ),
            max_token_estimate=override.max_token_estimate,
            max_content_size_bytes=override.max_content_size_bytes,
            max_total_token_estimate=override.max_total_token_estimate,
            max_total_content_size_bytes=override.max_total_content_size_bytes,
        )
        return PolicyContext(
            profile=base.profile,
            source=source,
            allowed_lifecycle_statuses=_stricter_allowed_values(
                base.allowed_lifecycle_statuses,
                validated_override.allowed_lifecycle_statuses
                if override.allowed_lifecycle_statuses is not None
                else None,
            ),
            allowed_trust_tiers=_stricter_allowed_values(
                base.allowed_trust_tiers,
                validated_override.allowed_trust_tiers
                if override.allowed_trust_tiers is not None
                else None,
            ),
            max_token_estimate=_stricter_ceiling(
                base.max_token_estimate,
                validated_override.max_token_estimate,
            ),
            max_content_size_bytes=_stricter_ceiling(
                base.max_content_size_bytes,
                validated_override.max_content_size_bytes,
            ),
            max_total_token_estimate=_stricter_ceiling(
                base.max_total_token_estimate,
                validated_override.max_total_token_estimate,
            ),
            max_total_content_size_bytes=_stricter_ceiling(
                base.max_total_content_size_bytes,
                validated_override.max_total_content_size_bytes,
            ),
        )
    except ValueError as exc:
        error_source = "workspace config" if source == "workspace_config" else "CLI override"
        raise InvalidClientConfigurationError(error_source, str(exc)) from exc


def _policy_config(
    loader: Callable[[], AptitudeConfig | None],
    source_name: str,
) -> PolicyConfig | None:
    """Load one optional config source and return just its policy section."""

    try:
        config = loader()
    except ValueError as exc:
        raise InvalidClientConfigurationError(source_name, str(exc)) from exc
    if config is None:
        return None
    return config.policy


def _stricter_allowed_values(base: list[str], override: list[str] | None) -> list[str]:
    if override is None:
        return list(base)
    override_set = set(override)
    return [value for value in base if value in override_set]


def _stricter_ceiling(base: int | None, override: int | None) -> int | None:
    if override is None:
        return base
    if base is None:
        return override
    return min(base, override)


def _selection_config(
    loader: Callable[[], AptitudeConfig | None],
    source_name: str,
) -> SelectionConfig | None:
    """Load one optional config source and return just its selection section."""

    try:
        config = loader()
    except ValueError as exc:
        raise InvalidClientConfigurationError(source_name, str(exc)) from exc
    if config is None:
        return None
    return config.selection


def build_resolve_use_case(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> tuple[ResolveSkillQueryUseCase, Callable[[], None]]:
    """Create the resolve use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        ResolveSkillQueryUseCase(
            registry_client,
            policy_context=_effective_policy_context(
                allowed_trust_tiers_override=allowed_trust_tiers_override,
                allowed_lifecycle_statuses_override=allowed_lifecycle_statuses_override,
                max_token_estimate_override=max_token_estimate_override,
                max_content_size_bytes_override=max_content_size_bytes_override,
                cwd=cwd,
            ),
            selection_preferences=_effective_selection_preferences(
                selection_profile_override=selection_profile_override,
                interaction_mode_override=interaction_mode_override,
                cwd=cwd,
            ),
        ),
        close,
    )


def build_install_use_case(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> tuple[InstallSkillUseCase, Callable[[], None]]:
    """Create the install use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        InstallSkillUseCase(
            registry_client,
            policy_context=_effective_policy_context(
                allowed_trust_tiers_override=allowed_trust_tiers_override,
                allowed_lifecycle_statuses_override=allowed_lifecycle_statuses_override,
                max_token_estimate_override=max_token_estimate_override,
                max_content_size_bytes_override=max_content_size_bytes_override,
                cwd=cwd,
            ),
            selection_preferences=_effective_selection_preferences(
                selection_profile_override=selection_profile_override,
                interaction_mode_override=interaction_mode_override,
                cwd=cwd,
            ),
        ),
        close,
    )


def build_sync_use_case() -> tuple[SyncFromLockUseCase, Callable[[], None]]:
    """Create the sync use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return SyncFromLockUseCase(registry_client), close
