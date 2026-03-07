"""DOT/Graphviz export helpers for dependency graphs."""

from pathlib import Path
from typing import Optional

import networkx as nx

from aptitude_client.core.graph.models import SkillNode


def graph_to_dot(graph: nx.DiGraph, root_node: Optional[SkillNode] = None) -> str:
    """Convert dependency graph to DOT text."""
    lines = [
        "digraph aptitude_dependencies {",
        "  rankdir=TB;",
        '  node [shape=box, style="rounded"];',
    ]

    for node, data in sorted(graph.nodes(data=True), key=lambda item: item[0].key):
        node_id = _node_id(node)
        label = node.name
        attrs = []

        if node.version:
            label = f"{label}\\n{node.version}"
        if data.get("missing"):
            label = f"{label} [missing]"
            attrs.append('color="red"')
            attrs.append('style="rounded,dashed"')
        elif root_node is not None and node == root_node:
            label = f"{label} [root]"
            attrs.append('color="blue"')
            attrs.append('penwidth="2"')

        attrs.insert(0, f'label="{label}"')
        lines.append(f"  {node_id} [{', '.join(attrs)}];")

    for source, target, edge_data in sorted(
        graph.edges(data=True), key=lambda edge: (edge[0].key, edge[1].key)
    ):
        source_id = _node_id(source)
        target_id = _node_id(target)
        requirement = edge_data.get("requirement")
        if requirement:
            lines.append(f'  {source_id} -> {target_id} [label="{requirement}"];')
        else:
            lines.append(f"  {source_id} -> {target_id};")

    lines.append("}")
    return "\n".join(lines)


def write_graph_dot(graph: nx.DiGraph, output_path: str, root_node: Optional[SkillNode] = None) -> None:
    """Write DOT representation to disk."""
    dot_text = graph_to_dot(graph=graph, root_node=root_node)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dot_text, encoding="utf-8")


def _node_id(node: SkillNode) -> str:
    key = node.key.replace("@", "_").replace("-", "_").replace(".", "_")
    return f'"{key}"'
