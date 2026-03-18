"""Application use case for exact-coordinate resolution."""

from __future__ import annotations

from typing import Protocol

from aptitude_client.application.dto import ResolveRequestDto, ResolveResultDto
from aptitude_client.domain.models import DependencySpec, SkillMetadata
from aptitude_client.resolver.solver import shape_exact_resolve_result


class RegistryReadPort(Protocol):
    """Small protocol for the exact read operations this use case needs."""

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata: ...

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]: ...


class ResolveExactSkillUseCase:
    """Orchestrate exact metadata and dependency reads for the first CLI flow."""

    def __init__(self, registry_client: RegistryReadPort) -> None:
        self._registry_client = registry_client

    def execute(self, request: ResolveRequestDto) -> ResolveResultDto:
        metadata = self._registry_client.fetch_skill_metadata(
            request.slug,
            request.version,
        )
        dependencies = self._registry_client.fetch_direct_dependencies(
            request.slug,
            request.version,
        )
        return shape_exact_resolve_result(request, metadata, dependencies)
