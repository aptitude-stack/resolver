"""Execution-owned export of materialized Aptitude skills into agent roots."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from aptitude_resolver.domain.errors import InvalidArtifactError
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.lockfile import Lockfile, replay_lockfile


@dataclass(frozen=True)
class ExportedSkill:
    """One materialized skill exported into an agent-compatible location."""

    agent: str
    scope: str
    slug: str
    version: str
    destination_path: str
    skill_markdown_path: str


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
    for coordinate in replayed.install_order:
        node_id = f"{coordinate.slug}@{coordinate.version}"
        source_dir = materialized_root / "skills" / coordinate.slug / coordinate.version
        export_source_dir = _resolve_export_source_dir(source_dir)
        content_path = export_source_dir / "content.md"
        existing_skill_markdown_path = export_source_dir / "SKILL.md"
        export_dir = destination_root / coordinate.slug
        export_dir.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=f".{coordinate.slug.replace('.', '_')}-",
            dir=destination_root,
        ) as temp_dir:
            staging_dir = Path(temp_dir)
            skill_markdown_path = staging_dir / "SKILL.md"
            _copy_agent_resources(source_dir=export_source_dir, staging_dir=staging_dir)
            if content_path.exists():
                shutil.copy2(content_path, skill_markdown_path)
            elif not existing_skill_markdown_path.exists():
                raise InvalidArtifactError(
                    coordinate.slug,
                    coordinate.version,
                    "Expected content.md or SKILL.md in the materialized artifact.",
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


def _copy_agent_resources(*, source_dir: Path, staging_dir: Path) -> None:
    """Copy bundled skill resources while normalizing the main markdown file."""

    def ignore(_path: str, names: list[str]) -> set[str]:
        return {"content.md", "metadata.json"} & set(names)

    shutil.copytree(source_dir, staging_dir, dirs_exist_ok=True, ignore=ignore)


def _resolve_export_source_dir(source_dir: Path) -> Path:
    """Return the directory whose contents should become the agent skill package."""

    if (source_dir / "content.md").exists() or (source_dir / "SKILL.md").exists():
        return source_dir

    # Temporary compatibility for currently published artifacts. Remove this
    # after the registry publishes SKILL.md at the archive root again.
    bundled_source_dir = source_dir / "skill-bundle"
    if (bundled_source_dir / "SKILL.md").exists():
        return bundled_source_dir

    return source_dir
