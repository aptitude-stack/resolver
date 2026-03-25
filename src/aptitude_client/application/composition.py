"""Application-owned wiring helpers for configured use cases."""

from __future__ import annotations

from collections.abc import Callable

from aptitude_client.application.use_cases import (
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SyncFromLockUseCase,
)
from aptitude_client.registry import RegistryClient
from aptitude_client.shared.config import Settings


def build_registry_client() -> tuple[RegistryClient, Callable[[], None]]:
    """Create a registry client and its cleanup hook."""

    registry_client = RegistryClient(Settings())
    return registry_client, registry_client.close


def build_resolve_use_case() -> tuple[ResolveSkillQueryUseCase, Callable[[], None]]:
    """Create the resolve use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return ResolveSkillQueryUseCase(registry_client), close


def build_install_use_case() -> tuple[InstallSkillUseCase, Callable[[], None]]:
    """Create the install use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return InstallSkillUseCase(registry_client), close


def build_sync_use_case() -> tuple[SyncFromLockUseCase, Callable[[], None]]:
    """Create the sync use case and its cleanup hook."""

    registry_client, close = build_registry_client()
    return SyncFromLockUseCase(registry_client), close
