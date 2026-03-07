"""Tree-style visualization helpers for dependency graphs."""

from typing import List, Optional, Set

import networkx as nx

from aptitude_client.core.graph.models import SkillNode


def render_dependency_tree(graph: nx.DiGraph, root_node: SkillNode) -> str:
    """Render dependencies as a Unicode tree starting from the given root node."""
    branch, last_branch, pipe, space = _tree_tokens()
    lines: List[str] = [_format_node_label(graph, root_node, is_root=True)]

    dependencies = list(graph.predecessors(root_node))
    for index, dependency in enumerate(dependencies):
        is_last = index == len(dependencies) - 1
        lines.extend(
            _render_dependency_branch(
                graph=graph,
                node=dependency,
                prefix="",
                is_last=is_last,
                path={root_node},
                branch=branch,
                last_branch=last_branch,
                pipe=pipe,
                space=space,
            )
        )
    return "\n".join(lines)


def find_graph_node_by_name(graph: nx.DiGraph, skill_name: str) -> Optional[SkillNode]:
    """Find the first non-missing graph node matching a skill name."""
    for node, data in graph.nodes(data=True):
        if node.name == skill_name and not data.get("missing"):
            return node
    return None


def _render_dependency_branch(
    graph: nx.DiGraph,
    node: SkillNode,
    prefix: str,
    is_last: bool,
    path: Set[SkillNode],
    branch: str,
    last_branch: str,
    pipe: str,
    space: str,
) -> List[str]:
    connector = last_branch if is_last else branch
    line = f"{prefix}{connector}{_format_node_label(graph, node, is_root=False)}"
    lines = [line]

    if node in path:
        lines[-1] = f"{line} [cycle]"
        return lines

    dependencies = list(graph.predecessors(node))
    if not dependencies:
        return lines

    next_prefix = f"{prefix}{space if is_last else pipe}"
    next_path = set(path)
    next_path.add(node)
    for index, dependency in enumerate(dependencies):
        child_is_last = index == len(dependencies) - 1
        lines.extend(
            _render_dependency_branch(
                graph=graph,
                node=dependency,
                prefix=next_prefix,
                is_last=child_is_last,
                path=next_path,
                branch=branch,
                last_branch=last_branch,
                pipe=pipe,
                space=space,
            )
        )
    return lines


def _format_node_label(graph: nx.DiGraph, node: SkillNode, *, is_root: bool) -> str:
    label = node.name
    if is_root:
        label = f"{label} [root]"
    if graph.nodes[node].get("missing"):
        return f"{label} [missing]"
    return label


def _tree_tokens() -> tuple[str, str, str, str]:
    return ("\u251c\u2500\u2500 ", "\u2514\u2500\u2500 ", "\u2502   ", "    ")
