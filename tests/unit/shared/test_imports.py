from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "aptitude",
        "aptitude.application.dto",
        "aptitude.application.queries",
        "aptitude.application.use_cases",
        "aptitude.cache",
        "aptitude.discovery",
        "aptitude.discovery.intent",
        "aptitude.discovery.query_builder",
        "aptitude.discovery.reranking",
        "aptitude.domain.errors",
        "aptitude.domain.policy",
        "aptitude.domain.policy.ranking",
        "aptitude.domain.tracing",
        "aptitude.execution",
        "aptitude.governance",
        "aptitude.interfaces.cli",
        "aptitude.interfaces.shared",
        "aptitude.interfaces.tui",
        "aptitude.lockfile",
        "aptitude.registry",
        "aptitude.resolution.graph",
        "aptitude.resolution.normalizer",
        "aptitude.resolution.solver",
        "aptitude.resolution.validation",
        "aptitude.shared.config",
        "aptitude.shared.logging",
        "aptitude.telemetry",
    ],
)
def test_package_modules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
