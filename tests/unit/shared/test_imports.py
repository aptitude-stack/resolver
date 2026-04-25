from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "aptitude_resolver",
        "aptitude_resolver.application.dto",
        "aptitude_resolver.application.queries",
        "aptitude_resolver.application.use_cases",
        "aptitude_resolver.cache",
        "aptitude_resolver.discovery",
        "aptitude_resolver.discovery.intent",
        "aptitude_resolver.discovery.query_builder",
        "aptitude_resolver.discovery.reranking",
        "aptitude_resolver.domain.errors",
        "aptitude_resolver.domain.policy",
        "aptitude_resolver.domain.policy.ranking",
        "aptitude_resolver.domain.tracing",
        "aptitude_resolver.execution",
        "aptitude_resolver.governance",
        "aptitude_resolver.interfaces.cli",
        "aptitude_resolver.interfaces.mcp",
        "aptitude_resolver.interfaces.shared",
        "aptitude_resolver.lockfile",
        "aptitude_resolver.registry",
        "aptitude_resolver.resolution.graph",
        "aptitude_resolver.resolution.normalizer",
        "aptitude_resolver.resolution.solver",
        "aptitude_resolver.resolution.validation",
        "aptitude_resolver.shared.config",
        "aptitude_resolver.shared.logging",
        "aptitude_resolver.telemetry",
    ],
)
def test_package_modules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
