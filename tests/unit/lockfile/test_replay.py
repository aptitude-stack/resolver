from __future__ import annotations

import pytest

from aptitude_resolver.domain.errors import InvalidLockfileError
from aptitude_resolver.lockfile import replay_lockfile
from aptitude_resolver.lockfile.model import LockRoot, Lockfile, LockedEdge, LockedSkill


def _node(node_id: str, slug: str, version: str) -> LockedSkill:
    return LockedSkill(
        node_id=node_id,
        slug=slug,
        version=version,
        artifact_ref=f"/skills/{slug}/{version}/content",
        name=slug,
        description=f"{slug} description",
        tags=["lint"],
        headers={"runtime": "python"},
        rendered_summary=f"{slug} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-28T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
    )


def _lockfile(
    *, install_order: list[str], edges: list[LockedEdge] | None = None
) -> Lockfile:
    nodes = [
        _node("python.base@1.0.0", "python.base", "1.0.0"),
        _node("python.lint@1.2.3", "python.lint", "1.2.3"),
    ]
    return Lockfile(
        version=1,
        generated_at="2026-03-28T00:00:00Z",
        client_version=None,
        root=LockRoot(
            request="python lint",
            requested_version=None,
            selected_node_id="python.lint@1.2.3",
            selection_mode="single_candidate",
        ),
        nodes=nodes,
        edges=list(edges or []),
        install_order=install_order,
        governance=[],
    )


def test_replay_lockfile_rejects_duplicate_install_order_entries() -> None:
    lockfile = _lockfile(
        install_order=["python.base@1.0.0", "python.base@1.0.0", "python.lint@1.2.3"]
    )

    with pytest.raises(InvalidLockfileError, match="duplicate node id"):
        replay_lockfile(lockfile)


def test_replay_lockfile_rejects_missing_root_selected_node() -> None:
    lockfile = _lockfile(install_order=["python.base@1.0.0", "python.lint@1.2.3"])
    lockfile = Lockfile(
        version=lockfile.version,
        generated_at=lockfile.generated_at,
        client_version=lockfile.client_version,
        root=LockRoot(
            request=lockfile.root.request,
            requested_version=lockfile.root.requested_version,
            selected_node_id="missing.skill@9.9.9",
            selection_mode=lockfile.root.selection_mode,
        ),
        nodes=lockfile.nodes,
        edges=lockfile.edges,
        install_order=lockfile.install_order,
        governance=lockfile.governance,
    )

    with pytest.raises(InvalidLockfileError, match="root selected node is missing"):
        replay_lockfile(lockfile)


def test_replay_lockfile_rejects_unknown_install_order_node() -> None:
    lockfile = _lockfile(install_order=["python.base@1.0.0", "missing.skill@9.9.9"])

    with pytest.raises(InvalidLockfileError, match="references unknown node id"):
        replay_lockfile(lockfile)


def test_replay_lockfile_rejects_edge_references_to_missing_nodes() -> None:
    lockfile = _lockfile(
        install_order=["python.base@1.0.0", "python.lint@1.2.3"],
        edges=[
            LockedEdge(
                source_node_id="python.lint@1.2.3",
                target_node_id="missing.skill@9.9.9",
            )
        ],
    )

    with pytest.raises(InvalidLockfileError, match="unknown target node"):
        replay_lockfile(lockfile)
