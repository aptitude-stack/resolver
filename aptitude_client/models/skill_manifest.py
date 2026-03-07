"""Skill manifest model."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from aptitude_client.models.dependency import Dependency
from aptitude_client.models.metrics import Metrics
from aptitude_client.models.runtime import Runtime


class SkillManifest(BaseModel):
    """Top-level manifest describing a versioned AI skill artifact."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    author: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[Dependency]
    runtime: Runtime
    metrics: Optional[Metrics] = None
    security_score: Optional[float] = None
    stars: Optional[int] = None
    downloads: Optional[int] = None
