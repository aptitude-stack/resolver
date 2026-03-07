"""Cycle detection and install-order planning over dependency graphs."""

from typing import List

import networkx as nx

from aptitude_client.core.graph.errors import DependencyCycleError
from aptitude_client.core.graph.models import SkillNode


def detect_cycles(graph: nx.DiGraph) -> List[List[SkillNode]]:
    """Detect dependency cycles and return them as ordered node paths."""
    return [list(cycle) for cycle in nx.simple_cycles(graph)]


def plan_install_order(graph: nx.DiGraph) -> List[SkillNode]:
    """
    Produce install order using topological sorting.

    Raises:
        DependencyCycleError: If cycles exist in the graph.
    """
    cycles = detect_cycles(graph)
    if cycles:
        raise DependencyCycleError(cycles=cycles)

    return list(nx.topological_sort(graph))
