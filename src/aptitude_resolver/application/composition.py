"""Application-owned wiring helpers for configured use cases."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from aptitude_resolver.application.dto import (
    ConfigLayerDto,
    EffectivePolicyReportDto,
    PolicyConfigSnapshotDto,
    PolicyMergeSemanticsDto,
    SelectionConfigSnapshotDto,
)
from aptitude_resolver.application.use_cases import (
    InspectSkillUseCase,
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SearchSkillsUseCase,
    SyncFromLockUseCase,
)
from aptitude_resolver.domain.errors import InvalidResolverConfigurationError
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences
from aptitude_resolver.registry import RegistryClient
from aptitude_resolver.shared.config import (
    AptitudeConfig,
    PolicyConfig,
    SelectionConfig,
    Settings,
    describe_settings_validation_error,
    discover_workspace_config_path,
    load_system_aptitude_config,
    load_user_aptitude_config,
    load_workspace_aptitude_config,
    read_env_selection_overrides,
    resolve_system_config_path,
    resolve_user_config_path,
)

_SELECTION_PRECEDENCE = [
    "default",
    "system_config",
    "user_config",
    "workspace_config",
    "environment",
    "cli_override",
]
_POLICY_APPLICATION_ORDER = [
    "default",
    "system_config",
    "user_config",
    "workspace_config",
    "cli_override",
]


@dataclass(frozen=True)
class _ConfigLayerState:
    """One loaded configuration layer before DTO rendering."""

    source: str
    label: str
    active: bool
    path: Path | None = None
    selection: SelectionConfig | None = None
    policy: PolicyConfig | None = None


def build_registry_client() -> tuple[RegistryClient, Callable[[], None]]:
    """Create a registry client and its cleanup hook."""

    try:
        settings = Settings()
    except ValidationError as exc:
        raise InvalidResolverConfigurationError(
            "environment", describe_settings_validation_error(exc)
        ) from exc

    registry_client = RegistryClient(settings)
    return registry_client, registry_client.close


def _default_selection_config() -> SelectionConfig:
    preferences = SelectionPreferences()
    return SelectionConfig(
        profile=preferences.profile,
        interaction_mode=preferences.interaction_mode,
    )


def _default_policy_config() -> PolicyConfig:
    policy = PolicyContext()
    return PolicyConfig(
        allowed_lifecycle_statuses=list(policy.allowed_lifecycle_statuses),
        allowed_trust_tiers=list(policy.allowed_trust_tiers),
        max_token_estimate=policy.max_token_estimate,
        max_content_size_bytes=policy.max_content_size_bytes,
        max_total_token_estimate=policy.max_total_token_estimate,
        max_total_content_size_bytes=policy.max_total_content_size_bytes,
    )


def _load_optional_config(
    loader: Callable[[], AptitudeConfig | None],
    source_name: str,
) -> AptitudeConfig | None:
    try:
        return loader()
    except ValueError as exc:
        raise InvalidResolverConfigurationError(source_name, str(exc)) from exc


def _file_config_layer(
    *,
    source: str,
    label: str,
    path: Path | None,
    loader: Callable[[], AptitudeConfig | None],
) -> _ConfigLayerState:
    config = _load_optional_config(loader, label)
    return _ConfigLayerState(
        source=source,
        label=label,
        path=path,
        active=config is not None,
        selection=None if config is None else config.selection,
        policy=None if config is None else config.policy,
    )


def _config_layers(
    *,
    cwd: Path | None = None,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
) -> list[_ConfigLayerState]:
    workspace_path = discover_workspace_config_path(cwd)
    cli_selection = (
        SelectionConfig(
            profile=selection_profile_override,
            interaction_mode=interaction_mode_override,
        )
        if selection_profile_override is not None
        or interaction_mode_override is not None
        else None
    )
    cli_policy = (
        PolicyConfig(
            allowed_trust_tiers=allowed_trust_tiers_override,
            allowed_lifecycle_statuses=allowed_lifecycle_statuses_override,
            max_token_estimate=max_token_estimate_override,
            max_content_size_bytes=max_content_size_bytes_override,
        )
        if any(
            value is not None
            for value in (
                allowed_trust_tiers_override,
                allowed_lifecycle_statuses_override,
                max_token_estimate_override,
                max_content_size_bytes_override,
            )
        )
        else None
    )

    return [
        _ConfigLayerState(
            source="default",
            label="default",
            active=True,
            selection=_default_selection_config(),
            policy=_default_policy_config(),
        ),
        _file_config_layer(
            source="system_config",
            label="system config",
            path=resolve_system_config_path(),
            loader=load_system_aptitude_config,
        ),
        _file_config_layer(
            source="user_config",
            label="user config",
            path=resolve_user_config_path(),
            loader=load_user_aptitude_config,
        ),
        _file_config_layer(
            source="workspace_config",
            label="workspace config",
            path=workspace_path,
            loader=lambda: load_workspace_aptitude_config(cwd),
        ),
        _ConfigLayerState(
            source="environment",
            label="environment",
            active=read_env_selection_overrides() is not None,
            selection=read_env_selection_overrides(),
        ),
        _ConfigLayerState(
            source="cli_override",
            label="CLI override",
            active=cli_selection is not None or cli_policy is not None,
            selection=cli_selection,
            policy=cli_policy,
        ),
    ]


def _effective_selection_preferences_from_layers(
    layers: list[_ConfigLayerState],
) -> SelectionPreferences:
    """Build one effective selection-preference object from current sources."""

    default_preferences = SelectionPreferences()
    effective_profile = default_preferences.profile
    effective_profile_source = "default"
    effective_profile_error_source = "default"
    effective_interaction_mode = default_preferences.interaction_mode
    effective_interaction_source = "default"
    effective_interaction_error_source = "default"

    for layer in layers:
        selection_config = layer.selection
        if selection_config is None:
            continue
        if selection_config.profile is not None:
            effective_profile = selection_config.profile
            effective_profile_source = layer.source
            effective_profile_error_source = layer.label
        if selection_config.interaction_mode is not None:
            effective_interaction_mode = selection_config.interaction_mode
            effective_interaction_source = layer.source
            effective_interaction_error_source = layer.label

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
        raise InvalidResolverConfigurationError(source, str(exc)) from exc


def _effective_policy_context_from_layers(
    layers: list[_ConfigLayerState],
) -> PolicyContext:
    """Build one effective policy object from current sources."""

    policy = PolicyContext()
    policy_layers = {layer.source: layer for layer in layers}
    for source in _POLICY_APPLICATION_ORDER[1:]:
        override = policy_layers[source].policy
        if override is None:
            continue
        policy = _apply_policy_override(policy, override, source=source)
    return policy


def _effective_selection_preferences(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    cwd: Path | None = None,
) -> SelectionPreferences:
    return _effective_selection_preferences_from_layers(
        _config_layers(
            cwd=cwd,
            selection_profile_override=selection_profile_override,
            interaction_mode_override=interaction_mode_override,
        )
    )


def _effective_policy_context(
    *,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> PolicyContext:
    return _effective_policy_context_from_layers(
        _config_layers(
            cwd=cwd,
            allowed_trust_tiers_override=allowed_trust_tiers_override,
            allowed_lifecycle_statuses_override=allowed_lifecycle_statuses_override,
            max_token_estimate_override=max_token_estimate_override,
            max_content_size_bytes_override=max_content_size_bytes_override,
        )
    )


def build_effective_policy_report(
    *,
    cwd: Path | None = None,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
) -> EffectivePolicyReportDto:
    """Build a read-only inspection payload for effective client policy."""

    effective_cwd = (cwd or Path.cwd()).resolve()
    layers = _config_layers(
        cwd=effective_cwd,
        selection_profile_override=selection_profile_override,
        interaction_mode_override=interaction_mode_override,
        allowed_trust_tiers_override=allowed_trust_tiers_override,
        allowed_lifecycle_statuses_override=allowed_lifecycle_statuses_override,
        max_token_estimate_override=max_token_estimate_override,
        max_content_size_bytes_override=max_content_size_bytes_override,
    )
    selection = _effective_selection_preferences_from_layers(layers)
    policy = _effective_policy_context_from_layers(layers)

    return EffectivePolicyReportDto(
        cwd=str(effective_cwd),
        effective_selection=SelectionConfigSnapshotDto(
            profile=selection.profile,
            interaction_mode=selection.interaction_mode,
            profile_source=selection.profile_source,
            interaction_mode_source=selection.interaction_mode_source,
        ),
        effective_policy=PolicyConfigSnapshotDto(
            source=policy.source,
            allowed_lifecycle_statuses=list(policy.allowed_lifecycle_statuses),
            allowed_trust_tiers=list(policy.allowed_trust_tiers),
            max_token_estimate=policy.max_token_estimate,
            max_content_size_bytes=policy.max_content_size_bytes,
            max_total_token_estimate=policy.max_total_token_estimate,
            max_total_content_size_bytes=policy.max_total_content_size_bytes,
        ),
        layers=[_config_layer_dto(layer) for layer in layers],
        semantics=PolicyMergeSemanticsDto(
            selection_precedence=list(_SELECTION_PRECEDENCE),
            policy_application_order=list(_POLICY_APPLICATION_ORDER),
            selection_rule="last non-null value wins by precedence",
            policy_rule=(
                "restrictive-only: allowed lists intersect and numeric ceilings "
                "take the minimum"
            ),
        ),
    )


def _config_layer_dto(layer: _ConfigLayerState) -> ConfigLayerDto:
    return ConfigLayerDto(
        source=layer.source,
        label=layer.label,
        path=None if layer.path is None else str(layer.path),
        active=layer.active,
        selection=_selection_snapshot_from_config(layer.selection),
        policy=_policy_snapshot_from_config(layer.policy),
    )


def _selection_snapshot_from_config(
    config: SelectionConfig | None,
) -> SelectionConfigSnapshotDto | None:
    if config is None:
        return None
    return SelectionConfigSnapshotDto(
        profile=config.profile,
        interaction_mode=config.interaction_mode,
    )


def _policy_snapshot_from_config(
    config: PolicyConfig | None,
) -> PolicyConfigSnapshotDto | None:
    if config is None:
        return None
    return PolicyConfigSnapshotDto(
        allowed_lifecycle_statuses=(
            list(config.allowed_lifecycle_statuses)
            if config.allowed_lifecycle_statuses is not None
            else None
        ),
        allowed_trust_tiers=(
            list(config.allowed_trust_tiers)
            if config.allowed_trust_tiers is not None
            else None
        ),
        max_token_estimate=config.max_token_estimate,
        max_content_size_bytes=config.max_content_size_bytes,
        max_total_token_estimate=config.max_total_token_estimate,
        max_total_content_size_bytes=config.max_total_content_size_bytes,
    )


def _apply_policy_override(
    base: PolicyContext,
    override: PolicyConfig,
    *,
    source: str,
) -> PolicyContext:
    """Apply one stricter-only policy override layer onto an existing policy."""

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
        raise InvalidResolverConfigurationError(
            _source_error_label(source), str(exc)
        ) from exc


def _source_error_label(source: str) -> str:
    return {
        "system_config": "system config",
        "user_config": "user config",
        "workspace_config": "workspace config",
        "cli_override": "CLI override",
        "environment": "environment",
        "default": "default",
    }.get(source, source)


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


def build_search_use_case(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> tuple[SearchSkillsUseCase, Callable[[], None]]:
    """Create the search use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        SearchSkillsUseCase(
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


def build_inspect_use_case(
    *,
    selection_profile_override: str | None = None,
    interaction_mode_override: str | None = None,
    allowed_trust_tiers_override: list[str] | None = None,
    allowed_lifecycle_statuses_override: list[str] | None = None,
    max_token_estimate_override: int | None = None,
    max_content_size_bytes_override: int | None = None,
    cwd: Path | None = None,
) -> tuple[InspectSkillUseCase, Callable[[], None]]:
    """Create the inspect use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        InspectSkillUseCase(
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
