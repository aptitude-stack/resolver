"""Dependency model."""

from pydantic import BaseModel, ConfigDict


class Dependency(BaseModel):
    """Represents a skill dependency constraint."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
