"""Runtime model."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class Runtime(BaseModel):
    """Defines runtime compatibility details for a skill."""

    model_config = ConfigDict(extra="forbid")

    agent: str
    model: Optional[str] = None
