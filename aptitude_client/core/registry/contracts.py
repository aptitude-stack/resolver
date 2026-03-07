"""Explicit registry response contracts for the current MVP."""

from typing import List

from pydantic import BaseModel, ConfigDict

from aptitude_client.models import SkillManifest, SkillSummary


class ListSkillsResponse(BaseModel):
    """Contract for `GET /skills` responses."""

    model_config = ConfigDict(extra="forbid")

    skills: List[SkillSummary]


class GetSkillResponse(BaseModel):
    """Contract for `GET /skills/{name}` and `GET /skills/{name}/{version}` responses."""

    model_config = ConfigDict(extra="forbid")

    skill: SkillManifest
