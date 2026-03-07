"""Dependency resolver APIs for graph-based planning."""

from aptitude_client.core.resolver.in_memory_provider import (
    InMemoryManifestProvider,
    build_mvp_sample_manifests,
)
from aptitude_client.core.resolver.models import MissingDependency, ResolutionResult
from aptitude_client.core.resolver.provider import ManifestProvider
from aptitude_client.core.resolver.service import DependencyResolver

__all__ = [
    "ManifestProvider",
    "InMemoryManifestProvider",
    "build_mvp_sample_manifests",
    "DependencyResolver",
    "MissingDependency",
    "ResolutionResult",
]
