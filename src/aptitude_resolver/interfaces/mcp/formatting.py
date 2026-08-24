"""Response formatting helpers for Aptitude MCP tools."""

from __future__ import annotations

import json
from typing import Any

import toons
from pydantic import BaseModel

from aptitude_resolver.application.dto import (
    EffectivePolicyReportDto,
    InspectSkillResultDto,
    InstallResultDto,
    ResolveQueryResultDto,
    SearchSkillsResultDto,
    SyncResultDto,
)
from aptitude_resolver.interfaces.mcp.models import ResponseFormat


_SCORE_SCALE = {
    "normalized_min": 0.0,
    "normalized_max": 1.0,
    "display_min": 0.0,
    "display_max": 10.0,
}
_PRIVATE_RESPONSE_KEYS = {
    "allowed_trust_tiers",
    "current_trust_tier",
    "trust",
    "trust_preference",
    "trust_tier",
    "trusttier",
}
_STRUCTURAL_SIGNAL_KEYS = {
    "decisive_signals",
    "match_reasons",
    "selection_details",
    "signals",
}


def dto_to_data(value: Any) -> Any:
    """Convert DTOs and nested values into JSON-safe Python data."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [dto_to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: dto_to_data(item) for key, item in value.items()}
    return value


def format_response(value: Any, response_format: ResponseFormat) -> str:
    """Format one response for an MCP tool."""

    if not isinstance(response_format, ResponseFormat):
        response_format = ResponseFormat(response_format)
    data = _public_data(value)
    if response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, sort_keys=True)
    if response_format == ResponseFormat.TOON:
        return toons.dumps(data)
    return _format_markdown(value, data)


def _public_data(value: Any) -> Any:
    """Build public skill output while preserving the policy contract."""

    data = dto_to_data(value)
    if isinstance(value, EffectivePolicyReportDto):
        return data
    data = _scrub(data)
    if isinstance(data, dict):
        data["score_scale"] = dict(_SCORE_SCALE)
    return data


def paginate_items(
    items: list[Any],
    *,
    limit: int,
    offset: int,
    key: str,
) -> dict[str, Any]:
    """Return a stable paginated payload for MCP list tools."""

    sliced = items[offset : offset + limit]
    next_offset = offset + len(sliced)
    has_more = next_offset < len(items)
    return {
        "total": len(items),
        "count": len(sliced),
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
        key: [dto_to_data(item) for item in sliced],
    }


def _format_markdown(value: Any, data: Any) -> str:
    if isinstance(value, SearchSkillsResultDto):
        return _format_search_result(value)
    if isinstance(value, InspectSkillResultDto):
        return _format_inspect_result(value)
    if isinstance(value, ResolveQueryResultDto):
        return _format_resolve_result(value)
    if isinstance(value, EffectivePolicyReportDto):
        return _format_policy_report(value)
    if isinstance(value, InstallResultDto):
        return _format_install_result(value)
    if isinstance(value, SyncResultDto):
        return _format_sync_result(value)
    if isinstance(data, dict) and "candidates" in data:
        return _format_paginated_candidates(data)
    return json.dumps(data, indent=2, sort_keys=True)


def _format_candidate(candidate: Any) -> str:
    labels = ", ".join(candidate.matched_labels or candidate.labels[:4])
    suffix = f" [{labels}]" if labels else ""
    score_suffix = _format_candidate_scores(candidate)
    return f"- `{candidate.slug}@{candidate.version}` - {candidate.name} ({candidate.lifecycle_status}){score_suffix}{suffix}"


def _format_search_result(result: SearchSkillsResultDto) -> str:
    lines = [f"# Aptitude Search: {result.requested_query}", ""]
    if not result.candidates:
        lines.append("No candidates returned.")
        return "\n".join(lines)
    lines.extend(_format_candidate(candidate) for candidate in result.candidates)
    return "\n".join(lines)


def _format_paginated_candidates(data: dict[str, Any]) -> str:
    lines = [
        f"# Aptitude Search: {data.get('requested_query', '')}",
        "",
        (
            f"Showing {data['count']} of {data['total']} candidates "
            f"from offset {data['offset']}."
        ),
        "",
    ]
    for candidate in data["candidates"]:
        score_suffix = _format_candidate_scores(candidate)
        lines.append(
            f"- `{candidate['slug']}@{candidate['version']}` - {candidate['name']}"
            f"{score_suffix}"
        )
    if data["has_more"]:
        lines.extend(["", f"Next offset: `{data['next_offset']}`"])
    return "\n".join(lines)


def _format_candidate_scores(candidate: Any) -> str:
    scores = []
    for label, key in (
        ("Maturity", "maturity_score"),
        ("Security", "security_score"),
        ("Overall", "overall_score"),
    ):
        score = (
            candidate.get(key)
            if isinstance(candidate, dict)
            else getattr(candidate, key, None)
        )
        if score is not None:
            scores.append(f"{label}: {_display_score(score)}/10")
    return f" ({', '.join(scores)})" if scores else ""


def _format_inspect_result(result: InspectSkillResultDto) -> str:
    lines = [f"# Aptitude Inspect: {result.requested_query}", ""]
    if result.status == "selection_required":
        lines.append("Selection required. Available candidates:")
        lines.extend(_format_candidate(candidate) for candidate in result.candidates)
        return "\n".join(lines)
    if result.selected_coordinate is not None:
        lines.append(
            f"Selected: `{result.selected_coordinate.slug}@{result.selected_coordinate.version}`"
        )
    if result.skill is not None:
        lines.extend(
            [
                "",
                f"Name: {result.skill.name}",
                f"Status: {result.skill.lifecycle_status}",
            ]
        )
        scores = []
        for label, key in (
            ("Maturity", "maturity_score"),
            ("Security", "security_score"),
            ("Overall", "overall_score"),
        ):
            score = getattr(result.skill, key)
            if score is not None:
                scores.append(f"- {label}: {_display_score(score)}/10")
        if scores:
            lines.extend(["", "## Scores", *scores])
    if result.available_versions:
        lines.extend(["", "## Versions"])
        lines.extend(
            f"- `{item.version}` ({item.lifecycle_status})"
            for item in result.available_versions
        )
    if result.content_preview:
        suffix = " (truncated)" if result.content_preview_truncated else ""
        lines.extend(
            [
                "",
                f"## Content Preview{suffix}",
                "",
                "```markdown",
                result.content_preview,
                "```",
            ]
        )
    return "\n".join(lines)


def _format_resolve_result(result: ResolveQueryResultDto) -> str:
    lines = [
        f"# Aptitude Resolve: {result.requested_query}",
        "",
        f"Status: `{result.status}`",
    ]
    if result.selected_coordinate is not None:
        lines.append(
            f"Selected: `{result.selected_coordinate.slug}@{result.selected_coordinate.version}`"
        )
    if result.graph is not None:
        lines.extend(
            [
                f"Graph nodes: {len(result.graph.nodes)}",
                f"Graph edges: {len(result.graph.edges)}",
                "Install order: "
                + ", ".join(
                    f"{item.slug}@{item.version}" for item in result.graph.install_order
                ),
            ]
        )
    if result.status == "selection_required":
        lines.extend(["", "Selection required. Available candidates:"])
        lines.extend(_format_candidate(candidate) for candidate in result.candidates)
    return "\n".join(lines)


def _format_policy_report(report: EffectivePolicyReportDto) -> str:
    policy = report.effective_policy
    selection = report.effective_selection
    return "\n".join(
        [
            "# Aptitude Effective Policy",
            "",
            f"Workspace: `{report.cwd}`",
            f"Selection profile: `{selection.profile}`",
            f"Interaction mode: `{selection.interaction_mode}`",
            f"Allowed lifecycle statuses: `{', '.join(policy.allowed_lifecycle_statuses or [])}`",
            f"Allowed trust tiers: `{', '.join(policy.allowed_trust_tiers or [])}`",
            f"Max skill tokens: `{policy.max_token_estimate if policy.max_token_estimate is not None else 'unlimited'}`",
            f"Max skill bytes: `{policy.max_content_size_bytes if policy.max_content_size_bytes is not None else 'unlimited'}`",
        ]
    )


def _format_install_result(result: InstallResultDto) -> str:
    lines = [
        f"# Aptitude Install: {result.requested_query}",
        "",
        f"Status: `{result.status}`",
    ]
    if result.selected_coordinate is not None:
        lines.append(
            f"Selected: `{result.selected_coordinate.slug}@{result.selected_coordinate.version}`"
        )
    if result.materialized_root:
        lines.append(f"Aptitude state: `{result.materialized_root}`")
    if result.export_roots:
        lines.extend(["", "## Agent Roots"])
        lines.extend(
            f"- `{agent}` -> `{path}`" for agent, path in result.export_roots.items()
        )
    if result.exported_skills:
        lines.extend(["", "## Exported Skills"])
        lines.extend(
            f"- `{item.agent}` `{item.slug}@{item.version}` -> `{item.destination_path}`"
            for item in result.exported_skills
        )
    if result.installed_skills:
        lines.extend(["", "## Aptitude Internal Skills"])
        lines.extend(
            f"- `{item.slug}@{item.version}` -> `{item.install_path}`"
            for item in result.installed_skills
        )
    if result.status == "selection_required":
        lines.extend(["", "Selection required. Available candidates:"])
        lines.extend(_format_candidate(candidate) for candidate in result.candidates)
    return "\n".join(lines)


def _format_sync_result(result: SyncResultDto) -> str:
    lines = [f"# Aptitude Sync: {result.lock_path}", "", f"Status: `{result.status}`"]
    if result.materialized_root:
        lines.append(f"Materialized root: `{result.materialized_root}`")
    if result.installed_skills:
        lines.extend(["", "## Installed Skills"])
        lines.extend(
            f"- `{item.slug}@{item.version}` -> `{item.install_path}`"
            for item in result.installed_skills
        )
    return "\n".join(lines)


def _normalized_score(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return round(max(0.0, min(1.0, float(value))), 4)


def _display_score(value: Any) -> str:
    normalized = _normalized_score(value)
    return "n/a" if normalized is None else f"{normalized * 10:.1f}"


def _scrub(value: Any, *, structural: bool = False) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in _PRIVATE_RESPONSE_KEYS:
                continue
            if _is_private_trust_policy_entry(item):
                continue
            if structural and _is_private_structural_signal(item):
                continue
            scrubbed[key] = _scrub(
                item,
                structural=structural or normalized_key in _STRUCTURAL_SIGNAL_KEYS,
            )
        return scrubbed
    if isinstance(value, list):
        return [
            _scrub(item, structural=structural)
            for item in value
            if not _is_private_trust_policy_entry(item)
            and not (structural and _is_private_structural_signal(item))
        ]
    return value


def _is_private_trust_policy_entry(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and str(value.get("rule", "")).casefold() == "allowed_trust_tiers"
        and "passed" in value
        and "message" in value
    )


def _is_private_structural_signal(value: Any) -> bool:
    return value == "higher_trust_tier"
