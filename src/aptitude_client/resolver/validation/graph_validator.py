"""Validate resolved graphs before policy evaluation and install."""

from __future__ import annotations

from aptitude_client.domain.models import ResolutionGraph


def validate_resolution_graph(graph: ResolutionGraph) -> None:
    """Validate internal graph consistency."""

    node_keys = {(node.coordinate.slug, node.coordinate.version) for node in graph.nodes}
    for edge in graph.edges:
        if (edge.source.slug, edge.source.version) not in node_keys:
            raise ValueError("Resolution graph edge source was not present in nodes.")
        if (edge.target.slug, edge.target.version) not in node_keys:
            raise ValueError("Resolution graph edge target was not present in nodes.")
