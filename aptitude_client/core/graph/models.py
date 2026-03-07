"""Graph node models for dependency planning."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SkillNode:
    """A graph node identifying a skill, with optional selected version."""

    name: str
    version: Optional[str] = None

    @property
    def key(self) -> str:
        """Stable human-readable key used in plans and diagnostics."""
        if self.version:
            return f"{self.name}@{self.version}"
        return self.name
