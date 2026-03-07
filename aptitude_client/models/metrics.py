"""Metrics model."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class Metrics(BaseModel):
    """Optional performance and usage metrics for a skill."""

    model_config = ConfigDict(extra="forbid")

    tokens: Optional[int] = None
    latency: Optional[str] = None
