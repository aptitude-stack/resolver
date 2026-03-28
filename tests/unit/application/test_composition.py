from __future__ import annotations

from aptitude_client.application import composition
from aptitude_client.application.use_cases import (
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SyncFromLockUseCase,
)


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
