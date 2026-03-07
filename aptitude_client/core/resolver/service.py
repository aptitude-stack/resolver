"""Resolver service coordinating graph construction and planning."""

from typing import Iterable, List, Set

import networkx as nx

from aptitude_client.core.graph import (
    DependencyCycleError,
    build_dependency_graph,
    detect_cycles,
    get_missing_nodes,
    plan_install_order,
)
from aptitude_client.core.resolver.models import MissingDependency, ResolutionResult
from aptitude_client.core.resolver.provider import ManifestProvider
from aptitude_client.models import SkillManifest


class DependencyResolver:
    """
    Dependency planning service.

    Phase 4 scope:
    - construct graph from provided manifests
    - detect cycles
    - produce install order

    Version solving is intentionally deferred to a future phase.
    """

    def resolve(self, manifests: Iterable[SkillManifest]) -> ResolutionResult:
        """Resolve dependency planning from a set of already-selected manifests."""
        graph = build_dependency_graph(manifests=manifests)
        missing_dependencies = self._collect_missing_dependencies(graph)

        cycles = detect_cycles(graph)
        if cycles:
            return ResolutionResult(
                graph=graph,
                install_order=[],
                cycles=cycles,
                missing_dependencies=missing_dependencies,
                notes="Cycle detected. Install order cannot be produced.",
            )

        try:
            install_order = plan_install_order(graph=graph)
        except DependencyCycleError as exc:
            return ResolutionResult(
                graph=graph,
                install_order=[],
                cycles=exc.cycles,
                missing_dependencies=missing_dependencies,
                notes="Cycle detected during planning. Install order cannot be produced.",
            )

        install_order = [node for node in install_order if not graph.nodes[node].get("missing")]

        notes = None
        if missing_dependencies:
            notes = "Resolution completed with missing dependencies."

        return ResolutionResult(
            graph=graph,
            install_order=install_order,
            cycles=[],
            missing_dependencies=missing_dependencies,
            notes=notes,
        )

    def resolve_skill(self, skill_name: str, provider: ManifestProvider) -> ResolutionResult:
        """
        Resolve starting from a root skill name using a provider-backed manifest traversal.

        The current phase traverses by skill name only; version-choice solving is intentionally deferred.
        """
        manifests = self._collect_manifests_recursive(skill_name=skill_name, provider=provider)
        if not manifests:
            return ResolutionResult(
                graph=nx.DiGraph(),
                install_order=[],
                cycles=[],
                missing_dependencies=[MissingDependency(name=skill_name, required_versions=[])],
                notes=f"Requested skill '{skill_name}' was not found in provider.",
            )

        return self.resolve(manifests=manifests)

    def _collect_manifests_recursive(
        self,
        skill_name: str,
        provider: ManifestProvider,
    ) -> List[SkillManifest]:
        collected: List[SkillManifest] = []
        visited: Set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            manifest = provider.get_manifest(name)
            if manifest is None:
                return

            collected.append(manifest)
            for dependency in manifest.dependencies:
                visit(dependency.name)

        visit(skill_name)
        return collected

    @staticmethod
    def _collect_missing_dependencies(graph: nx.DiGraph) -> List[MissingDependency]:
        missing_entries: List[MissingDependency] = []
        for node in get_missing_nodes(graph):
            required_versions = graph.nodes[node].get("required_versions") or set()
            missing_entries.append(
                MissingDependency(
                    name=node.name,
                    required_versions=sorted(required_versions),
                )
            )
        return sorted(missing_entries, key=lambda item: item.name)
