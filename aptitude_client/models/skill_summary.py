"""Skill summary model."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class SkillSummary(BaseModel):
    """Compact skill projection for listing/search-style endpoints."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    author: Optional[str] = None
    stars: Optional[int] = None
    downloads: Optional[int] = None
