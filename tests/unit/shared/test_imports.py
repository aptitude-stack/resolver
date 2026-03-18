from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "aptitude_client",
        "aptitude_client.application.dto",
        "aptitude_client.application.use_cases",
        "aptitude_client.interfaces.cli",
        "aptitude_client.registry",
        "aptitude_client.resolver.solver",
        "aptitude_client.shared.config",
        "aptitude_client.shared.logging",
        "aptitude_client.domain.errors",
    ],
)
def test_package_modules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
