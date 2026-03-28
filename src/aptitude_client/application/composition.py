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
from aptitude_client.domain.policy import SelectionPreferences
from aptitude_client.registry import RegistryClient
from aptitude_client.shared.config import (
    AptitudeConfig,
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
    cwd: Path | None = None,
) -> tuple[ResolveSkillQueryUseCase, Callable[[], None]]:
    """Create the resolve use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        ResolveSkillQueryUseCase(
            registry_client,
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
    cwd: Path | None = None,
) -> tuple[InstallSkillUseCase, Callable[[], None]]:
    """Create the install use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return (
        InstallSkillUseCase(
            registry_client,
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
