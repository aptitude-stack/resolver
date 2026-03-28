from __future__ import annotations

import pytest

from aptitude_client.application import composition
from aptitude_client.application.use_cases import (
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SyncFromLockUseCase,
)
from aptitude_client.domain.errors import InvalidClientConfigurationError
from aptitude_client.shared.config.aptitude_config import AptitudeConfig, SelectionConfig


class FakeSettings:
    pass


class FakeRegistryClient:
    instances: list["FakeRegistryClient"] = []

    def __init__(self, settings) -> None:
        self.settings = settings
        self.closed = False
        self.__class__.instances.append(self)

    def close(self) -> None:
        self.closed = True


def test_build_resolve_use_case_wires_registry_and_cleanup(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)

    use_case, close = composition.build_resolve_use_case()

    assert isinstance(use_case, ResolveSkillQueryUseCase)
    assert len(FakeRegistryClient.instances) == 1
    assert isinstance(FakeRegistryClient.instances[0].settings, FakeSettings)

    close()

    assert FakeRegistryClient.instances[0].closed is True


def test_build_install_use_case_wires_registry_and_cleanup(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)

    use_case, close = composition.build_install_use_case()

    assert isinstance(use_case, InstallSkillUseCase)
    assert len(FakeRegistryClient.instances) == 1
    assert isinstance(FakeRegistryClient.instances[0].settings, FakeSettings)

    close()

    assert FakeRegistryClient.instances[0].closed is True


def test_build_resolve_use_case_merges_selection_preferences_with_cli_precedence(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition,
        "load_workspace_aptitude_config",
        lambda cwd=None: AptitudeConfig(
            selection=SelectionConfig(profile="balanced", interaction_mode="auto")
        ),
    )
    monkeypatch.setattr(
        composition,
        "load_user_aptitude_config",
        lambda: AptitudeConfig(selection=SelectionConfig(profile="high-trust")),
    )
    monkeypatch.setattr(
        composition,
        "read_env_selection_overrides",
        lambda env=None: SelectionConfig(profile="low-cost", interaction_mode="always"),
    )

    use_case, close = composition.build_resolve_use_case(
        selection_profile_override="high-trust",
        interaction_mode_override="never",
    )

    assert isinstance(use_case, ResolveSkillQueryUseCase)
    assert use_case._planner._selection_preferences.profile == "high-trust"
    assert use_case._planner._selection_preferences.interaction_mode == "never"

    close()
    assert FakeRegistryClient.instances[0].closed is True


def test_build_resolve_use_case_raises_for_invalid_selection_preference_source(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition,
        "load_workspace_aptitude_config",
        lambda cwd=None: AptitudeConfig(selection=SelectionConfig(profile="cheapest")),
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition,
        "read_env_selection_overrides",
        lambda env=None: SelectionConfig(),
    )

    with pytest.raises(InvalidClientConfigurationError) as exc_info:
        composition.build_resolve_use_case()

    assert "workspace config" in str(exc_info.value)


def test_build_sync_use_case_wires_registry_and_cleanup(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)

    use_case, close = composition.build_sync_use_case()

    assert isinstance(use_case, SyncFromLockUseCase)
    assert len(FakeRegistryClient.instances) == 1
    assert isinstance(FakeRegistryClient.instances[0].settings, FakeSettings)

    close()

    assert FakeRegistryClient.instances[0].closed is True
