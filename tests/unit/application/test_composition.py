from __future__ import annotations

import pytest

import aptitude_resolver.application.composition as composition
from aptitude_resolver.application.use_cases import (
    InspectSkillUseCase,
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SearchSkillsUseCase,
    SyncFromLockUseCase,
)
from aptitude_resolver.domain.errors import InvalidResolverConfigurationError
from aptitude_resolver.shared.config.aptitude_config import (
    AptitudeConfig,
    PolicyConfig,
    SelectionConfig,
)
from aptitude_resolver.shared.config.settings import Settings


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


def test_build_search_use_case_wires_registry_and_cleanup(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)

    use_case, close = composition.build_search_use_case()

    assert isinstance(use_case, SearchSkillsUseCase)
    assert len(FakeRegistryClient.instances) == 1
    assert isinstance(FakeRegistryClient.instances[0].settings, FakeSettings)

    close()

    assert FakeRegistryClient.instances[0].closed is True


def test_build_inspect_use_case_wires_registry_and_cleanup(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)

    use_case, close = composition.build_inspect_use_case()

    assert isinstance(use_case, InspectSkillUseCase)
    assert len(FakeRegistryClient.instances) == 1
    assert isinstance(FakeRegistryClient.instances[0].settings, FakeSettings)

    close()

    assert FakeRegistryClient.instances[0].closed is True


def test_build_registry_client_reports_missing_environment_variables_cleanly(
    monkeypatch,
) -> None:
    monkeypatch.setattr(composition, "Settings", lambda: Settings(_env_file=None))
    monkeypatch.delenv("APTITUDE_SERVER_BASE_URL", raising=False)
    monkeypatch.delenv("APTITUDE_READ_TOKEN", raising=False)

    with pytest.raises(InvalidResolverConfigurationError) as exc_info:
        composition.build_registry_client()

    assert exc_info.value.source == "environment"
    assert (
        exc_info.value.details == "Missing required environment variables: "
        "APTITUDE_SERVER_BASE_URL, APTITUDE_READ_TOKEN."
    )


def test_build_resolve_use_case_merges_selection_preferences_with_cli_precedence(
    monkeypatch,
) -> None:
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


def test_build_resolve_use_case_raises_for_invalid_selection_preference_source(
    monkeypatch,
) -> None:
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

    with pytest.raises(InvalidResolverConfigurationError) as exc_info:
        composition.build_resolve_use_case()

    assert "workspace config" in str(exc_info.value)


@pytest.mark.parametrize(
    (
        "user_config",
        "workspace_config",
        "env_config",
        "cli_profile",
        "cli_mode",
        "expected",
    ),
    [
        (
            None,
            None,
            None,
            None,
            None,
            ("balanced", "auto", "default", "default"),
        ),
        (
            SelectionConfig(profile="high-trust", interaction_mode="always"),
            None,
            None,
            None,
            None,
            ("high-trust", "always", "user_config", "user_config"),
        ),
        (
            SelectionConfig(profile="high-trust", interaction_mode="always"),
            SelectionConfig(profile="balanced", interaction_mode="never"),
            None,
            None,
            None,
            ("balanced", "never", "workspace_config", "workspace_config"),
        ),
        (
            SelectionConfig(profile="high-trust", interaction_mode="always"),
            SelectionConfig(profile="balanced", interaction_mode="never"),
            SelectionConfig(profile="low-cost", interaction_mode="auto"),
            None,
            None,
            ("low-cost", "auto", "environment", "environment"),
        ),
        (
            SelectionConfig(profile="high-trust", interaction_mode="always"),
            SelectionConfig(profile="balanced", interaction_mode="never"),
            SelectionConfig(profile="low-cost", interaction_mode="auto"),
            "high-trust",
            "never",
            ("high-trust", "never", "cli_override", "cli_override"),
        ),
    ],
)
def test_build_resolve_use_case_selection_precedence_covers_default_to_cli(
    monkeypatch,
    user_config: SelectionConfig | None,
    workspace_config: SelectionConfig | None,
    env_config: SelectionConfig | None,
    cli_profile: str | None,
    cli_mode: str | None,
    expected: tuple[str, str, str, str],
) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition,
        "load_user_aptitude_config",
        lambda: (
            AptitudeConfig(selection=user_config) if user_config is not None else None
        ),
    )
    monkeypatch.setattr(
        composition,
        "load_workspace_aptitude_config",
        lambda cwd=None: (
            AptitudeConfig(selection=workspace_config)
            if workspace_config is not None
            else None
        ),
    )
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: env_config
    )

    use_case, close = composition.build_resolve_use_case(
        selection_profile_override=cli_profile,
        interaction_mode_override=cli_mode,
    )

    preferences = use_case._planner._selection_preferences
    assert preferences.profile == expected[0]
    assert preferences.interaction_mode == expected[1]
    assert preferences.profile_source == expected[2]
    assert preferences.interaction_mode_source == expected[3]

    close()
    assert FakeRegistryClient.instances[0].closed is True


def test_build_resolve_use_case_applies_cli_policy_overrides(monkeypatch) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition, "load_workspace_aptitude_config", lambda cwd=None: None
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: None
    )

    use_case, close = composition.build_resolve_use_case(
        allowed_trust_tiers_override=["internal", "verified"],
        allowed_lifecycle_statuses_override=["deprecated", "published"],
        max_token_estimate_override=500,
        max_content_size_bytes_override=2048,
    )

    policy_context = use_case._planner._policy_context
    assert policy_context.source == "cli_override"
    assert policy_context.allowed_trust_tiers == ["verified", "internal"]
    assert policy_context.allowed_lifecycle_statuses == ["published", "deprecated"]
    assert policy_context.max_token_estimate == 500
    assert policy_context.max_content_size_bytes == 2048

    close()
    assert FakeRegistryClient.instances[0].closed is True


def test_build_resolve_use_case_raises_for_invalid_cli_policy_override(
    monkeypatch,
) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition, "load_workspace_aptitude_config", lambda cwd=None: None
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: None
    )

    with pytest.raises(InvalidResolverConfigurationError) as exc_info:
        composition.build_resolve_use_case(
            allowed_trust_tiers_override=["verified", "unknown-tier"],
        )

    assert exc_info.value.source == "CLI override"
    assert "allowed_trust_tiers" in exc_info.value.details


def test_build_resolve_use_case_merges_workspace_policy_with_stricter_cli_overrides(
    monkeypatch,
) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition,
        "load_workspace_aptitude_config",
        lambda cwd=None: AptitudeConfig(
            policy=PolicyConfig(
                allowed_trust_tiers=["verified", "internal"],
                allowed_lifecycle_statuses=["published", "deprecated"],
                max_token_estimate=500,
                max_content_size_bytes=2048,
                max_total_token_estimate=1500,
                max_total_content_size_bytes=4096,
            )
        ),
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: None
    )

    use_case, close = composition.build_resolve_use_case(
        allowed_trust_tiers_override=["verified", "untrusted"],
        allowed_lifecycle_statuses_override=["published", "archived"],
        max_token_estimate_override=800,
        max_content_size_bytes_override=1024,
    )

    policy_context = use_case._planner._policy_context
    assert policy_context.source == "cli_override"
    assert policy_context.allowed_trust_tiers == ["verified"]
    assert policy_context.allowed_lifecycle_statuses == ["published"]
    assert policy_context.max_token_estimate == 500
    assert policy_context.max_content_size_bytes == 1024
    assert policy_context.max_total_token_estimate == 1500
    assert policy_context.max_total_content_size_bytes == 4096

    close()
    assert FakeRegistryClient.instances[0].closed is True


def test_build_resolve_use_case_raises_for_invalid_workspace_policy(
    monkeypatch,
) -> None:
    FakeRegistryClient.instances = []
    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition,
        "load_workspace_aptitude_config",
        lambda cwd=None: AptitudeConfig(
            policy=PolicyConfig(allowed_lifecycle_statuses=["published", "retired"])
        ),
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: None
    )

    with pytest.raises(InvalidResolverConfigurationError) as exc_info:
        composition.build_resolve_use_case()

    assert exc_info.value.source == "workspace config"
    assert "allowed_lifecycle_statuses" in exc_info.value.details


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
