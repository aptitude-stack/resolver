





"""Resolver provider interfaces for future registry-backed resolution."""

from typing import Iterable, Optional, Protocol

from aptitude_client.models import SkillManifest


class ManifestProvider(Protocol):
    """Abstract source of skill manifests for resolver workflows."""

    def list_manifests(self) -> Iterable[SkillManifest]:
        """Return candidate manifests available to the resolver."""
        ...

    def get_manifest(self, name: str) -> Optional[SkillManifest]:
        """Return a manifest by skill name."""
        ...
