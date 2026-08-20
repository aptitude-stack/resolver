from __future__ import annotations

from pathlib import Path

from aptitude_resolver.discovery import DiscoverSkillCandidatesQuery, load_discovery_context
from aptitude_resolver.domain.models import DiscoveryQuery, SkillCoordinate, SkillIdentity
from aptitude_resolver.lockfile import LockRoot, Lockfile, LockedSkill, serialize_lockfile


def _node(slug: str, version: str) -> LockedSkill:
    return LockedSkill(
        node_id=f"{slug}@{version}",
        slug=slug,
        version=version,
        artifact_ref=f"artifact:{slug}@{version}",
        name=slug,
        description=f"{slug} description",
        tags=[],
        headers={},
        rendered_summary=slug,
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-01-01T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest="digest",
        content_size_bytes=1,
    )


def _lockfile(nodes: list[LockedSkill]) -> Lockfile:
    root = LockRoot(
        request=nodes[0].slug,
        requested_version=nodes[0].version,
        selected_node_id=nodes[0].node_id,
        selection_mode="explicit",
    )
    return Lockfile(
        version=2,
        generated_at=None,
        client_version=None,
        root=root,
        roots=[root],
        nodes=nodes,
        edges=[],
        install_order=[node.node_id for node in nodes],
    )


class _RegistryClient:
    def __init__(self) -> None:
        self.discovery_queries: list[DiscoveryQuery] = []

    def discover_candidate_slugs(self, query):
        self.discovery_queries.append(query)
        return ["remote-skill"]

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        return SkillIdentity(
            slug=slug,
            status="active",
            current_version=SkillCoordinate(slug=slug, version="1.0.0"),
            current_lifecycle_status="published",
            current_trust_tier="internal",
            current_published_at="2026-01-01T00:00:00Z",
            created_at=None,
            updated_at=None,
        )

    def list_skill_versions(self, slug: str):
        return [
            type(
                "Version",
                (),
                {
                    "coordinate": SkillCoordinate(slug=slug, version="1.0.0"),
                    "name": slug,
                    "description": slug,
                    "tags": [],
                    "headers": {},
                    "rendered_summary": slug,
                    "lifecycle_status": "published",
                    "trust_tier": "internal",
                    "published_at": "2026-01-01T00:00:00Z",
                },
            )()
        ]


def test_discovery_context_prefers_project_nodes_and_preserves_lock_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    project_nodes = [_node("project-root", "1.0.0"), _node("shared", "1.0.0")]
    global_nodes = [_node("shared", "9.0.0"), _node("global-dependency", "2.0.0")]
    project_lock = project / "aptitude.lock.json"
    global_lock = state_home / "aptitude" / "aptitude.lock.json"
    global_lock.parent.mkdir(parents=True)
    project_lock.write_text(serialize_lockfile(_lockfile(project_nodes)))
    global_lock.write_text(serialize_lockfile(_lockfile(global_nodes)))

    registry = _RegistryClient()
    DiscoverSkillCandidatesQuery(registry, cwd=project).execute("lint")

    assert registry.discovery_queries[0].context_skills == [
        SkillCoordinate(slug="project-root", version="1.0.0"),
        SkillCoordinate(slug="shared", version="1.0.0"),
        SkillCoordinate(slug="global-dependency", version="2.0.0"),
    ]


def test_discovery_context_caps_coordinates_at_fifty(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    nodes = [_node(f"skill-{index}", "1.0.0") for index in range(60)]
    project.joinpath("aptitude.lock.json").write_text(
        serialize_lockfile(_lockfile(nodes))
    )

    registry = _RegistryClient()
    DiscoverSkillCandidatesQuery(registry, cwd=project).execute("lint")

    context = registry.discovery_queries[0].context_skills
    assert len(context) == 50
    assert context[0] == SkillCoordinate(slug="skill-0", version="1.0.0")
    assert context[-1] == SkillCoordinate(slug="skill-49", version="1.0.0")


def test_discovery_context_ignores_invalid_utf8_lockfile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project.joinpath("aptitude.lock.json").write_bytes(b"\xff\xfe")

    assert load_discovery_context(cwd=project) == []


def test_discovery_context_skips_invalid_slug_and_version_nodes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    nodes = [
        _node("invalid slug", "1.0.0"),
        _node("invalid-version", "not-semver"),
        _node("valid-skill", "1.2.3"),
    ]
    project.joinpath("aptitude.lock.json").write_text(
        serialize_lockfile(_lockfile(nodes))
    )

    assert load_discovery_context(cwd=project) == [
        SkillCoordinate(slug="valid-skill", version="1.2.3")
    ]
