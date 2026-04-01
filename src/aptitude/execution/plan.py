"""Execution plan models and lock-driven preview builder."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from aptitude.lockfile import Lockfile, replay_lockfile


@dataclass(frozen=True)
class ExecutionStep:
    """One planned action for future runtime execution."""

    node_id: str
    skill: str
    version: str
    artifact_ref: str
    action: str


@dataclass(frozen=True)
class ExecutionPlan:
    """Execution plan preview generated from a lockfile."""

    steps: list[ExecutionStep] = field(default_factory=list)


def build_execution_plan(lockfile: Lockfile) -> ExecutionPlan:
    """Build a deterministic execution plan from locked install order."""

    replayed = replay_lockfile(lockfile)
    return ExecutionPlan(
        steps=[
            ExecutionStep(
                node_id=node.node_id,
                skill=node.slug,
                version=node.version,
                artifact_ref=node.artifact_ref,
                action="materialize_local_skill",
            )
            for node in replayed.install_order
        ]
    )


def execution_plan_to_dict(execution_plan: ExecutionPlan) -> dict[str, object]:
    """Convert an execution plan into a JSON-safe structure."""

    return {
        "steps": [
            {
                "node_id": step.node_id,
                "skill": step.skill,
                "version": step.version,
                "artifact_ref": step.artifact_ref,
                "action": step.action,
            }
            for step in execution_plan.steps
        ]
    }


def serialize_execution_plan(execution_plan: ExecutionPlan) -> str:
    """Serialize an execution plan preview to JSON."""

    return json.dumps(execution_plan_to_dict(execution_plan), indent=2)
