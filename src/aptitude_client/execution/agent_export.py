"""Execution-owned export of materialized Aptitude skills into agent roots."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.lockfile import Lockfile, replay_lockfile


APTITUDE_AGENT_SIDECAR = ".aptitude-export.json"


@dataclass(frozen=True)
class ExportedSkill:
    """One materialized skill exported into an agent-compatible location."""

    agent: str
    scope: str
    slug: str
    version: str
    destination_path: str
    skill_markdown_path: str
    metadata_path: str


@dataclass(frozen=True)
class AgentExportResult:
    """Result of exporting one materialized workspace into an agent root."""

    destination_root: str
    exported_skills: list[ExportedSkill] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


def export_materialized_skills_to_agent_root(
    *,
    materialized_root: Path,
    lockfile: Lockfile,
    destination_root: Path,
    agent: str,
    scope: str,
) -> AgentExportResult:
    """Copy materialized skills into one agent root using an unversioned layout."""

    materialized_root = materialized_root.resolve()
    destination_root = destination_root.resolve()
    destination_root.mkdir(parents=True, exist_ok=True)

    replayed = replay_lockfile(lockfile)
    exported_skills: list[ExportedSkill] = []
    trace: list[TraceEntry] = []
    nodes_by_id = {node.node_id: node for node in lockfile.nodes}

    for coordinate in replayed.install_order:
        node_id = f"{coordinate.slug}@{coordinate.version}"
        node = nodes_by_id[node_id]
        source_dir = materialized_root / "skills" / coordinate.slug / coordinate.version
        content_path = source_dir / "content.md"
        export_dir = destination_root / coordinate.slug
        export_dir.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=f".{coordinate.slug.replace('.', '_')}-",
            dir=destination_root,
        ) as temp_dir:
            staging_dir = Path(temp_dir)
            skill_markdown_path = staging_dir / "SKILL.md"
            metadata_path = staging_dir / APTITUDE_AGENT_SIDECAR
            shutil.copy2(content_path, skill_markdown_path)
            metadata_path.write_text(
                json.dumps(
                    {
                        "tool": "aptitude",
                        "agent": agent,
                        "scope": scope,
                        "slug": coordinate.slug,
                        "version": coordinate.version,
                        "artifact_ref": node.artifact_ref,
                        "lifecycle_status": node.lifecycle_status,
                        "trust_tier": node.trust_tier,
                        "content_checksum": {
                            "algorithm": node.content_checksum_algorithm,
                            "digest": node.content_checksum_digest,
                            "size_bytes": node.content_size_bytes,
                        },
                        "workspace_materialized_root": str(materialized_root),
                        "workspace_install_path": str(source_dir),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            if export_dir.exists():
                shutil.rmtree(export_dir)
            staging_dir.replace(export_dir)

        exported_skills.append(
            ExportedSkill(
                agent=agent,
                scope=scope,
                slug=coordinate.slug,
                version=coordinate.version,
                destination_path=str(export_dir),
                skill_markdown_path=str(export_dir / "SKILL.md"),
                metadata_path=str(export_dir / APTITUDE_AGENT_SIDECAR),
            )
        )
        trace.append(
            TraceEntry(
                stage="execution",
                action="export_agent_skill",
                message=f"Exported {node_id} to the {agent} {scope} skill root.",
                data={
                    "agent": agent,
                    "scope": scope,
                    "destination_path": str(export_dir),
                },
            )
        )

    return AgentExportResult(
        destination_root=str(destination_root),
        exported_skills=exported_skills,
        trace=trace,
    )
