"""Errors for dependency graph construction and planning."""

from typing import List

from aptitude_client.core.graph.models import SkillNode


class GraphPlanningError(Exception):
    """Base error for dependency graph planning failures."""


class DuplicateSkillNameError(GraphPlanningError):
    """Raised when input manifests contain duplicate names for unsupported multi-version input."""

    def __init__(self, skill_name: str) -> None:
        self.skill_name = skill_name
        super().__init__(
            f"Duplicate manifest name '{skill_name}' is not supported in Phase 4 graph planning."
        )


class DependencyCycleError(GraphPlanningError):
    """Raised when a dependency cycle is detected in the graph."""

    def __init__(self, cycles: List[List[SkillNode]]) -> None:
        self.cycles = cycles
        cycle_text = "; ".join(" -> ".join(node.key for node in cycle) for cycle in cycles)
        super().__init__(f"Dependency cycle detected: {cycle_text}")
