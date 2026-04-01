"""Lock replay helpers used by execution."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from aptitude_client.domain.errors import InvalidLockfileError
from aptitude_client.lockfile.model import Lockfile, LockedEdge, LockedSkill


@dataclass(frozen=True)
class ReplayedLock:
    """Execution-ready replayed structure reconstructed from one lockfile."""

    root_node: LockedSkill
    nodes_by_id: dict[str, LockedSkill]
    edges_by_source: dict[str, list[LockedEdge]] = field(default_factory=dict)
    install_order: list[LockedSkill] = field(default_factory=list)


def replay_lockfile(lockfile: Lockfile) -> ReplayedLock:
    """Reconstruct execution-ready inputs from one lockfile only."""

    nodes_by_id: dict[str, LockedSkill] = {}
    for node in lockfile.nodes:
        if node.node_id in nodes_by_id:
            raise InvalidLockfileError(
                f"Lockfile contains duplicate node id: {node.node_id}"
            )
        nodes_by_id[node.node_id] = node

    if lockfile.root.selected_node_id not in nodes_by_id:
        raise InvalidLockfileError(
            f"Lockfile root selected node is missing: {lockfile.root.selected_node_id}"
        )

    install_order_nodes: list[LockedSkill] = []
    seen_install_order: set[str] = set()
    for node_id in lockfile.install_order:
        if node_id in seen_install_order:
            raise InvalidLockfileError(
                f"Lockfile install order contains duplicate node id: {node_id}"
            )
        try:
            install_order_nodes.append(nodes_by_id[node_id])
        except KeyError as exc:
            raise InvalidLockfileError(
                f"Lockfile install order references unknown node id: {node_id}"
            ) from exc
        seen_install_order.add(node_id)

    if seen_install_order != set(nodes_by_id):
        missing = sorted(set(nodes_by_id) - seen_install_order)
        raise InvalidLockfileError(
            "Lockfile install order must include every locked node exactly once: "
            + ", ".join(missing)
        )

    edges_by_source: dict[str, list[LockedEdge]] = defaultdict(list)
    for edge in lockfile.edges:
        if edge.source_node_id not in nodes_by_id:
            raise InvalidLockfileError(
                f"Lockfile edge references unknown source node: {edge.source_node_id}"
            )
        if edge.target_node_id not in nodes_by_id:
            raise InvalidLockfileError(
                f"Lockfile edge references unknown target node: {edge.target_node_id}"
            )
        edges_by_source[edge.source_node_id].append(edge)

    sorted_edges = {
        node_id: sorted(
            item,
            key=lambda edge: (
                edge.source_node_id,
                edge.target_node_id,
                edge.edge_type,
                edge.optional,
                tuple(edge.markers),
            ),
        )
        for node_id, item in edges_by_source.items()
    }

    return ReplayedLock(
        root_node=nodes_by_id[lockfile.root.selected_node_id],
        nodes_by_id=nodes_by_id,
        edges_by_source=sorted_edges,
        install_order=install_order_nodes,
    )
