from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "aptitude_client",
        "aptitude_client.application.dto",
        "aptitude_client.application.queries",
        "aptitude_client.application.use_cases",
        "aptitude_client.cache",
        "aptitude_client.discovery",
        "aptitude_client.discovery.intent",
        "aptitude_client.discovery.query_builder",
        "aptitude_client.discovery.reranking",
        "aptitude_client.domain.errors",
        "aptitude_client.domain.policy",
        "aptitude_client.domain.policy.ranking",
        "aptitude_client.domain.tracing",
        "aptitude_client.execution",
        "aptitude_client.governance",
        "aptitude_client.interfaces.cli",
        "aptitude_client.lockfile",
        "aptitude_client.registry",
        "aptitude_client.resolver.graph",
        "aptitude_client.resolver.normalizer",
        "aptitude_client.resolver.solver",
        "aptitude_client.resolver.validation",
        "aptitude_client.shared.config",
        "aptitude_client.shared.logging",
        "aptitude_client.telemetry",
    ],
)
def test_package_modules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
