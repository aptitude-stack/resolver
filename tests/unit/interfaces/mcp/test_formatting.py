from __future__ import annotations

import json

import pytest

from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    GovernanceSnapshotDto,
    InspectSkillResultDto,
    InspectSkillSummaryDto,
    InstallResultDto,
    LockRootDto,
    LockfileDto,
    PolicyEvaluationDto,
    PolicySnapshotDto,
    ResolveQueryResultDto,
    SearchSkillsResultDto,
    TraceEntryDto,
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


def test_skill_json_uses_normalized_scores_and_explicit_scale_without_trust() -> None:
    result = InspectSkillResultDto(
        requested_query="postman",
        status="inspected",
        skill=InspectSkillSummaryDto(
            name="Postman",
            description="Test skill",
            rendered_summary="Test skill",
            lifecycle_status="published",
            trust_tier="verified",
            published_at="2026-04-24T00:00:00Z",
            maturity_score=0.9,
            security_score=0.95,
            overall_score=0.87,
        ),
    )

    payload = json.loads(format_response(result, ResponseFormat.JSON))

    assert payload["score_scale"] == {
        "normalized_min": 0.0,
        "normalized_max": 1.0,
        "display_min": 0.0,
        "display_max": 10.0,
    }
    assert payload["skill"]["maturity_score"] == 0.9
    assert payload["skill"]["security_score"] == 0.95
    assert payload["skill"]["overall_score"] == 0.87
    assert "trust" not in json.dumps(payload).lower()


def test_skill_markdown_uses_ten_point_scores_without_trust() -> None:
    result = InspectSkillResultDto(
        requested_query="postman",
        status="inspected",
        skill=InspectSkillSummaryDto(
            name="Postman",
            description="Test skill",
            rendered_summary="Test skill",
            lifecycle_status="published",
            trust_tier="verified",
            published_at="2026-04-24T00:00:00Z",
            maturity_score=0.9,
            security_score=0.95,
            overall_score=0.87,
        ),
    )

    output = format_response(result, ResponseFormat.MARKDOWN)

    assert "Maturity: 9.0/10" in output
    assert "Security: 9.5/10" in output
    assert "Overall: 8.7/10" in output
    assert "trust" not in output.lower()


def test_skill_toon_keeps_normalized_scores_and_explicit_scale_without_trust() -> None:
    result = InspectSkillResultDto(
        requested_query="postman",
        status="inspected",
        skill=InspectSkillSummaryDto(
            name="Postman",
            description="Test skill",
            rendered_summary="Test skill",
            lifecycle_status="published",
            trust_tier="verified",
            published_at="2026-04-24T00:00:00Z",
            maturity_score=0.9,
            security_score=0.95,
            overall_score=0.87,
        ),
    )

    output = format_response(result, ResponseFormat.TOON)

    assert "score_scale" in output
    assert "overall_score" in output
    assert "0.87" in output
    assert "trust" not in output.lower()


def test_paginated_skill_outputs_scrub_trust_in_all_formats() -> None:
    value = {
        "requested_query": "postman",
        **paginate_items(
            [_candidate("postman-primary", 1)], limit=20, offset=0, key="candidates"
        ),
    }

    for response_format in ResponseFormat:
        output = format_response(value, response_format)
        assert "trust" not in output.lower()


def _lockfile_with_policy_trust() -> LockfileDto:
    return LockfileDto(
        version=1,
        root=LockRootDto(
            request="postman",
            selected_node_id="postman-primary@1.0.0",
            selection_mode="single_candidate",
        ),
        policy=PolicySnapshotDto(
            profile="default",
            source="client_default",
            allowed_lifecycle_statuses=["published"],
            allowed_trust_tiers=["verified"],
        ),
        governance=[
            GovernanceSnapshotDto(
                rule="allowed_trust_tiers",
                passed=True,
                message="Trust tier 'verified' is allowed.",
                node_id="postman-primary@1.0.0",
            )
        ],
    )


@pytest.mark.parametrize("result_type", ["resolve", "install"])
@pytest.mark.parametrize("response_format", [ResponseFormat.JSON, ResponseFormat.TOON])
def test_skill_machine_outputs_scrub_nested_lockfile_policy_trust(
    result_type: str,
    response_format: ResponseFormat,
) -> None:
    lockfile = _lockfile_with_policy_trust()
    result: ResolveQueryResultDto | InstallResultDto
    if result_type == "resolve":
        result = ResolveQueryResultDto(
            requested_query="postman",
            status="resolved",
            lockfile=lockfile,
            policy_evaluations=[
                PolicyEvaluationDto(
                    rule="allowed_trust_tiers",
                    passed=True,
                    message="Trust tier 'verified' is allowed.",
                )
            ],
        )
    else:
        result = InstallResultDto(
            requested_query="postman",
            status="installed",
            lockfile=lockfile,
            policy_evaluations=[
                PolicyEvaluationDto(
                    rule="allowed_trust_tiers",
                    passed=True,
                    message="Trust tier 'verified' is allowed.",
                )
            ],
        )

    output = format_response(result, response_format)

    assert "allowed_trust_tiers" not in output
    assert "Trust tier" not in output


@pytest.mark.parametrize("response_format", [ResponseFormat.JSON, ResponseFormat.TOON])
def test_skill_machine_outputs_scrub_structural_trust_signals(
    response_format: ResponseFormat,
) -> None:
    candidate = _candidate("postman-primary", 1).model_copy(
        update={
            "match_reasons": ["higher_trust_tier", "exact_name_match"],
            "selection_details": ["higher_trust_tier", "tokens=120"],
            "selection_reason": "Selection rationale remains visible.",
        }
    )
    result = ResolveQueryResultDto(
        requested_query="postman",
        status="resolved",
        candidates=[candidate],
        trace=[
            TraceEntryDto(
                stage="intent",
                action="parse_query",
                message="Trace message mentions higher_trust_tier in prose.",
                data={
                    "trust_preference": "high-trust",
                    "current_trust_tier": "verified",
                    "decisive_signals": ["higher_trust_tier", "exact_name_match"],
                },
            )
        ],
    )

    output = format_response(result, response_format)

    assert "trust_preference" not in output
    assert "current_trust_tier" not in output
    assert output.count("higher_trust_tier") == 1
    assert "Selection rationale remains visible." in output
    assert "Trace message mentions higher_trust_tier in prose." in output


def test_paginated_search_markdown_renders_available_scores_as_ten_point_values() -> (
    None
):
    candidate = _candidate("postman-primary", 1).model_copy(
        update={
            "maturity_score": 0.9,
            "security_score": 0.95,
            "overall_score": 0.87,
        }
    )
    value = {
        "requested_query": "postman",
        **paginate_items([candidate], limit=20, offset=0, key="candidates"),
    }

    output = format_response(value, ResponseFormat.MARKDOWN)

    assert "Maturity: 9.0/10" in output
    assert "Security: 9.5/10" in output
    assert "Overall: 8.7/10" in output


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
