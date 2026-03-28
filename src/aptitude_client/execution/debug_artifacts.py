"""Execution-owned writers for supplemental install debug artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from aptitude_client.domain.models import ResolutionGraph
from aptitude_client.domain.models.skill_coordinate import SkillCoordinate
from aptitude_client.domain.policy import PolicyEvaluation
from aptitude_client.domain.tracing import TraceEntry


def write_install_debug_artifacts(
    *,
    target: Path,
    graph: ResolutionGraph,
    trace: list[TraceEntry],
    policy_evaluations: list[PolicyEvaluation],
) -> None:
    """Write supplemental debug artifacts for one installed resolution."""

    resolution_dir = target / "resolution"
    resolution_dir.mkdir(parents=True, exist_ok=True)
    (resolution_dir / "graph.json").write_text(
        json.dumps(_graph_to_dict(graph), indent=2),
        encoding="utf-8",
    )
    (resolution_dir / "trace.json").write_text(
        json.dumps([_trace_to_dict(item) for item in trace], indent=2),
        encoding="utf-8",
    )
    (resolution_dir / "policy.json").write_text(
        json.dumps([_policy_to_dict(item) for item in policy_evaluations], indent=2),
        encoding="utf-8",
    )


def _graph_to_dict(graph: ResolutionGraph) -> dict[str, object]:
    return {
        "root": _coordinate_to_dict(graph.root),
        "nodes": [
            {
                "slug": node.coordinate.slug,
                "version": node.coordinate.version,
                "name": node.name,
                "description": node.description,
                "tags": list(node.tags),
                "runtime": node.headers.get("runtime"),
                "rendered_summary": node.rendered_summary,
                "lifecycle_status": node.lifecycle_status,
                "trust_tier": node.trust_tier,
                "published_at": node.published_at,
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "source": _coordinate_to_dict(edge.source),
                "target": _coordinate_to_dict(edge.target),
                "edge_type": edge.edge_type,
                "optional": edge.optional,
                "markers": list(edge.markers),
            }
            for edge in graph.edges
        ],
        "install_order": [_coordinate_to_dict(item) for item in graph.install_order],
        "conflicts": [
            {
                "code": conflict.code,
                "message": conflict.message,
                "coordinates": [_coordinate_to_dict(item) for item in conflict.coordinates],
            }
            for conflict in graph.conflicts
        ],
    }


def _trace_to_dict(trace: TraceEntry) -> dict[str, object]:
    return {
        "stage": trace.stage,
        "action": trace.action,
        "message": trace.message,
        "data": dict(trace.data),
    }


def _policy_to_dict(policy: PolicyEvaluation) -> dict[str, object]:
    return {
        "rule": policy.rule,
        "passed": policy.passed,
        "message": policy.message,
        "coordinate": (
            _coordinate_to_dict(policy.coordinate)
            if policy.coordinate is not None
            else None
        ),
    }


def _coordinate_to_dict(coordinate: SkillCoordinate) -> dict[str, str]:
    return {
        "slug": coordinate.slug,
        "version": coordinate.version,
    }
