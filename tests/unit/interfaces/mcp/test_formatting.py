from __future__ import annotations

import json

from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    SearchSkillsResultDto,
)
from aptitude_resolver.interfaces.mcp.formatting import (
    format_response,
    paginate_items,
)
from aptitude_resolver.interfaces.mcp.models import ResponseFormat


def _candidate(slug: str, position: int) -> DiscoveryCandidateDto:
    return DiscoveryCandidateDto(
        slug=slug,
        version="1.0.0",
        name=slug.replace("-", " ").title(),
        description="Test skill",
        lifecycle_status="stable",
        trust_tier="verified",
        published_at="2026-04-24T00:00:00Z",
        ranking_position=position,
    )


def test_format_response_renders_json_for_dto() -> None:
    result = SearchSkillsResultDto(
        requested_query="postman",
        status="found",
        candidates=[_candidate("postman-primary", 1)],
    )

    payload = json.loads(format_response(result, ResponseFormat.JSON))

    assert payload["requested_query"] == "postman"
    assert payload["candidates"][0]["slug"] == "postman-primary"


def test_format_response_renders_toon() -> None:
    result = {"items": [{"slug": "postman-primary", "version": "1.0.0"}]}

    payload = format_response(result, ResponseFormat.TOON)

    assert "items[1]{slug,version}" in payload
    assert "postman-primary,1.0.0" in payload


def test_paginate_items_returns_metadata() -> None:
    candidates = [_candidate("one", 1), _candidate("two", 2)]

    payload = paginate_items(candidates, limit=1, offset=0, key="candidates")

    assert payload["total"] == 2
    assert payload["count"] == 1
    assert payload["has_more"] is True
    assert payload["next_offset"] == 1
    assert payload["candidates"][0]["slug"] == "one"
