"""Lock-driven local materialization of locked skills."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from aptitude_client.domain.errors import ContentChecksumMismatchError
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.execution.plan import (
    ExecutionPlan,
    build_execution_plan,
    serialize_execution_plan,
)
from aptitude_client.lockfile import (
    Lockfile,
    LockedSkill,
    replay_lockfile,
    serialize_lockfile,
)


class RegistryContentPort(Protocol):
    """Artifact content reads required for materialization."""

    def fetch_skill_content(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> str: ...


@dataclass(frozen=True)
class MaterializedSkill:
    """One lock-driven skill materialized to disk."""

    slug: str
    version: str
    install_path: str


@dataclass(frozen=True)
class MaterializationResult:
    """Result of materializing one lockfile locally."""

    installed_skills: list[MaterializedSkill] = field(default_factory=list)
    materialized_root: str = ""
    execution_plan: ExecutionPlan = field(default_factory=ExecutionPlan)
    trace: list[TraceEntry] = field(default_factory=list)


def materialize_lockfile(
    *,
    target: Path,
    lockfile: Lockfile,
    registry_client: RegistryContentPort,
    execution_plan: ExecutionPlan | None = None,
) -> MaterializationResult:
    """Materialize a local workspace from lock data only."""

    replayed = replay_lockfile(lockfile)
    execution_plan = execution_plan or build_execution_plan(lockfile)
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    # Keep the staging directory under target.parent so promotion to target stays
    # on the same volume, which keeps the final replace safe on Windows.
    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}-", dir=target.parent
    ) as temp_dir:
        staging_root = Path(temp_dir)
        installed_skills: list[MaterializedSkill] = []
        trace: list[TraceEntry] = []

        for node in replayed.install_order:
            content = registry_client.fetch_skill_content(
                node.slug,
                node.version,
                checksum_algorithm=node.content_checksum_algorithm,
                checksum_digest=node.content_checksum_digest,
            )
            _verify_checksum(node, content)

            skill_dir = staging_root / "skills" / node.slug / node.version
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "content.md").write_text(content, encoding="utf-8")
            (skill_dir / "metadata.json").write_text(
                json.dumps(_metadata_to_dict(node), indent=2),
                encoding="utf-8",
            )
            installed_skills.append(
                MaterializedSkill(
                    slug=node.slug,
                    version=node.version,
                    install_path=str(skill_dir),
                )
            )
            trace.append(
                TraceEntry(
                    stage="execution",
                    action="materialize_locked_skill",
                    message=f"Materialized locked skill {node.node_id}.",
                    data={
                        "node_id": node.node_id,
                        "install_path": str(skill_dir),
                    },
                )
            )

        resolution_dir = staging_root / "resolution"
        resolution_dir.mkdir(parents=True, exist_ok=True)
        (resolution_dir / "aptitude.lock.json").write_text(
            serialize_lockfile(lockfile),
            encoding="utf-8",
        )
        (resolution_dir / "execution-plan.json").write_text(
            serialize_execution_plan(execution_plan),
            encoding="utf-8",
        )

        if target.exists():
            shutil.rmtree(target)
        staging_root.replace(target)

    return MaterializationResult(
        installed_skills=installed_skills,
        materialized_root=str(target),
        execution_plan=execution_plan,
        trace=trace,
    )


def _verify_checksum(node: LockedSkill, content: str) -> None:
    actual_digest = hashlib.new(
        node.content_checksum_algorithm,
        content.encode("utf-8"),
    ).hexdigest()
    if actual_digest != node.content_checksum_digest:
        raise ContentChecksumMismatchError(
            node.slug,
            node.version,
            node.content_checksum_algorithm,
            node.content_checksum_digest,
            actual_digest,
        )


def _metadata_to_dict(node: LockedSkill) -> dict[str, object]:
    return {
        "slug": node.slug,
        "version": node.version,
        "name": node.name,
        "description": node.description,
        "tags": list(node.tags),
        "headers": dict(node.headers),
        "rendered_summary": node.rendered_summary,
        "lifecycle_status": node.lifecycle_status,
        "trust_tier": node.trust_tier,
        "published_at": node.published_at,
        "artifact_ref": node.artifact_ref,
        "content_checksum": {
            "algorithm": node.content_checksum_algorithm,
            "digest": node.content_checksum_digest,
            "size_bytes": node.content_size_bytes,
        },
    }
