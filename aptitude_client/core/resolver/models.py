"""Resolver result models for explainable dependency planning."""

from dataclasses import dataclass
from typing import List, Optional

import networkx as nx

from aptitude_client.core.graph.models import SkillNode


@dataclass(frozen=True)
class MissingDependency:
    """A dependency referenced in constraints but missing from provided manifests."""

    name: str
    required_versions: List[str]


@dataclass(frozen=True)
class ResolutionResult:
    """Output of dependency planning for a given manifest set."""

    graph: nx.DiGraph
    install_order: List[SkillNode]
    cycles: List[List[SkillNode]]
    missing_dependencies: List[MissingDependency]
    notes: Optional[str] = None
