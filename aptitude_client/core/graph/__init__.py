"""Dependency graph construction and planning APIs."""

from aptitude_client.core.graph.builder import build_dependency_graph, get_missing_nodes
from aptitude_client.core.graph.dot_export import graph_to_dot, write_graph_dot
from aptitude_client.core.graph.errors import (
    DependencyCycleError,
    DuplicateSkillNameError,
    GraphPlanningError,
)
from aptitude_client.core.graph.models import SkillNode
from aptitude_client.core.graph.planner import detect_cycles, plan_install_order
from aptitude_client.core.graph.graph_visualizer import (
    find_graph_node_by_name,
    render_dependency_tree,
)

__all__ = [
    "SkillNode",
    "GraphPlanningError",
    "DuplicateSkillNameError",
    "DependencyCycleError",
    "build_dependency_graph",
    "get_missing_nodes",
    "detect_cycles",
    "plan_install_order",
    "find_graph_node_by_name",
    "render_dependency_tree",
    "graph_to_dot",
    "write_graph_dot",
]
