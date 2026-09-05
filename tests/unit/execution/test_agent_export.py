from __future__ import annotations

from hashlib import sha256

from aptitude_resolver.execution import export_materialized_skills_to_agent_root
from aptitude_resolver.domain.models import (
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.lockfile import build_lockfile


def _lockfile(content: str):
    coordinate = SkillCoordinate(slug="python-lint", version="1.2.3")
    graph = ResolutionGraph(
        root=coordinate,
        nodes=[
            ResolvedSkillNode(
                coordinate=coordinate,
                name="Python Lint",
                description="Lint files",
                tags=["python", "lint"],
                headers={"runtime": "python"},
                rendered_summary="Lint files consistently.",
                lifecycle_status="published",
                trust_tier="internal",
                published_at="2026-03-28T00:00:00Z",
                content_checksum_algorithm="sha256",
                content_checksum_digest=sha256(content.encode("utf-8")).hexdigest(),
                content_size_bytes=len(content.encode("utf-8")),
                token_estimate=120,
                maturity_score=0.9,
                security_score=0.95,
            )
        ],
        edges=[],
        install_order=[coordinate],
        conflicts=[],
    )
    return build_lockfile(
        graph=graph,
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        policy_evaluations=[],
    )


def test_export_materialized_skills_to_agent_root_writes_only_agent_skill_files(
    tmp_path,
) -> None:
    content = "# Python Lint\n"
    materialized_root = tmp_path / "workspace"
    skill_dir = materialized_root / "skills" / "python-lint" / "1.2.3"
    skill_dir.mkdir(parents=True)
    (skill_dir / "content.md").write_text(content, encoding="utf-8")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "guide.md").write_text("details", encoding="utf-8")
    (skill_dir / "metadata.json").write_text("{}", encoding="utf-8")
    lockfile = _lockfile(content)

    result = export_materialized_skills_to_agent_root(
        materialized_root=materialized_root,
        lockfile=lockfile,
        destination_root=tmp_path / ".codex" / "skills",
        agent="codex",
        scope="global",
    )

    export_dir = tmp_path / ".codex" / "skills" / "python-lint"
    assert result.destination_root == str((tmp_path / ".codex" / "skills").resolve())
    assert (export_dir / "SKILL.md").read_text(encoding="utf-8") == content
    assert (export_dir / "references" / "guide.md").read_text(
        encoding="utf-8"
    ) == "details"
    assert not (export_dir / "metadata.json").exists()
    assert not (export_dir / ".aptitude-export.json").exists()
    assert result.exported_skills[0].destination_path == str(export_dir)


def test_export_materialized_skills_to_agent_root_overwrites_existing_skill_dir(
    tmp_path,
) -> None:
    materialized_root = tmp_path / "workspace"
    skill_dir = materialized_root / "skills" / "python-lint" / "1.2.3"
    skill_dir.mkdir(parents=True)
    content = "# Fresh Content\n"
    (skill_dir / "content.md").write_text(content, encoding="utf-8")

    destination_root = tmp_path / ".claude" / "skills"
    existing_dir = destination_root / "python-lint"
    existing_dir.mkdir(parents=True)
    (existing_dir / "SKILL.md").write_text("stale", encoding="utf-8")

    lockfile = _lockfile(content)

    export_materialized_skills_to_agent_root(
        materialized_root=materialized_root,
        lockfile=lockfile,
        destination_root=destination_root,
        agent="claude-code",
        scope="project",
    )

    assert (existing_dir / "SKILL.md").read_text(encoding="utf-8") == content


def test_export_materialized_skills_to_agent_root_temporarily_accepts_skill_bundle_dir(
    tmp_path,
) -> None:
    materialized_root = tmp_path / "workspace"
    skill_dir = materialized_root / "skills" / "python-lint" / "1.2.3"
    bundle_dir = skill_dir / "skill-bundle"
    bundle_dir.mkdir(parents=True)
    content = "# Python Lint\n"
    (bundle_dir / "SKILL.md").write_text(content, encoding="utf-8")
    (bundle_dir / "resources.json").write_text("{}", encoding="utf-8")
    (skill_dir / "metadata.json").write_text("{}", encoding="utf-8")

    lockfile = _lockfile(content)

    export_materialized_skills_to_agent_root(
        materialized_root=materialized_root,
        lockfile=lockfile,
        destination_root=tmp_path / ".codex" / "skills",
        agent="codex",
        scope="project",
    )

    export_dir = tmp_path / ".codex" / "skills" / "python-lint"
    assert (export_dir / "SKILL.md").read_text(encoding="utf-8") == content
    assert (export_dir / "resources.json").read_text(encoding="utf-8") == "{}"
    assert not (export_dir / "skill-bundle").exists()
