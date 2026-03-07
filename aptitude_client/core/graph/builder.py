"""Dependency graph construction from skill manifests."""

from typing import Dict, Iterable, List, Set

import networkx as nx

from aptitude_client.core.graph.errors import DuplicateSkillNameError
from aptitude_client.core.graph.models import SkillNode
from aptitude_client.models import SkillManifest


def build_dependency_graph(manifests: Iterable[SkillManifest]) -> nx.DiGraph:
    """
    Build a directed graph from manifests.

    Edge direction is dependency -> dependent, so a topological order is an install order.
    """
    graph = nx.DiGraph()
    manifest_list = list(manifests)

    nodes_by_name: Dict[str, SkillNode] = {}
    for manifest in manifest_list:
        if manifest.name in nodes_by_name:
            raise DuplicateSkillNameError(manifest.name)

        node = SkillNode(name=manifest.name, version=manifest.version)
        nodes_by_name[manifest.name] = node
        graph.add_node(node, manifest=manifest, missing=False)

    for manifest in manifest_list:
        target_node = nodes_by_name[manifest.name]
        for dependency in manifest.dependencies:
            dependency_node = nodes_by_name.get(dependency.name)
            if dependency_node is None:
                dependency_node = SkillNode(name=dependency.name, version=None)
                if dependency_node not in graph:
                    graph.add_node(
                        dependency_node,
                        manifest=None,
                        missing=True,
                        required_versions=set(),
                    )
                required_versions = _required_versions(graph, dependency_node)
                required_versions.add(dependency.version)

            graph.add_edge(
                dependency_node,
                target_node,
                requirement=dependency.version,
            )

    return graph


def _required_versions(graph: nx.DiGraph, node: SkillNode) -> Set[str]:
    required_versions = graph.nodes[node].get("required_versions")
    if required_versions is None:
        required_versions = set()
        graph.nodes[node]["required_versions"] = required_versions
    return required_versions


def get_missing_nodes(graph: nx.DiGraph) -> List[SkillNode]:
    """Return nodes that are referenced as dependencies but missing manifests."""
    missing: List[SkillNode] = []
    for node, data in graph.nodes(data=True):
        if data.get("missing"):
            missing.append(node)
    return missing
