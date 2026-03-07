"""In-memory manifest provider for local resolver MVP flows."""

from typing import Dict, Iterable, List, Optional

from aptitude_client.core.resolver.provider import ManifestProvider
from aptitude_client.models import Dependency, Runtime, SkillManifest


class InMemoryManifestProvider(ManifestProvider):
    """Dictionary-backed provider keyed by skill name."""

    def __init__(self, manifests: Iterable[SkillManifest]) -> None:
        self._manifests_by_name: Dict[str, SkillManifest] = {}
        for manifest in manifests:
            self._manifests_by_name[manifest.name] = manifest

    def list_manifests(self) -> Iterable[SkillManifest]:
        return self._manifests_by_name.values()

    def get_manifest(self, name: str) -> Optional[SkillManifest]:
        return self._manifests_by_name.get(name)


def build_mvp_sample_manifests() -> List[SkillManifest]:
    """Create a small local manifest set for resolver MVP demonstration."""
    return [
        SkillManifest(
            name="telemetry",
            version="1.0.0",
            description="Shared telemetry skill.",
            dependencies=[],
            runtime=Runtime(agent="aptitude"),
        ),
        SkillManifest(
            name="core-agent",
            version="1.0.0",
            description="Core reasoning agent skill.",
            dependencies=[Dependency(name="telemetry", version=">=1.0.0")],
            runtime=Runtime(agent="aptitude"),
        ),
        SkillManifest(
            name="prompt-pack",
            version="1.0.0",
            description="Reusable prompt templates.",
            dependencies=[Dependency(name="template-lib", version=">=1.0.0")],
            runtime=Runtime(agent="aptitude"),
        ),
        SkillManifest(
            name="assistant-suite",
            version="1.0.0",
            description="Top-level assistant bundle.",
            dependencies=[
                Dependency(name="core-agent", version=">=1.0.0"),
                Dependency(name="prompt-pack", version=">=1.0.0"),
            ],
            runtime=Runtime(agent="aptitude"),
        ),
    ]
