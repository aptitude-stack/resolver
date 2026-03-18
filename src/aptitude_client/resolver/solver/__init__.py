"""Resolver solver package."""

from aptitude_client.resolver.solver.discovery_selection import select_discovery_candidate
from aptitude_client.resolver.solver.exact_resolve import shape_exact_resolve_result

__all__ = ["select_discovery_candidate", "shape_exact_resolve_result"]
