"""Helpers for accumulating independently resolved lockfile graphs."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TypeVar

from aptitude_resolver.lockfile.model import LockRoot, Lockfile, LockedEdge
from aptitude_resolver.lockfile.replay import replay_lockfile


def merge_lockfiles(existing: Lockfile | None, incoming: Lockfile) -> Lockfile:
    """Return a deterministic cumulative lock while preserving existing pins."""

    if existing is None:
        replay_lockfile(incoming)
        return incoming

    existing_roots = existing.roots or [existing.root]
    incoming_roots = incoming.roots or [incoming.root]
    roots = _unique_roots(existing_roots + incoming_roots)
    nodes = _unique_by_id(existing.nodes + incoming.nodes, lambda item: item.node_id)
    edges = _unique_edges(existing.edges + incoming.edges)
    install_order = _unique_strings(existing.install_order + incoming.install_order)
    merged = Lockfile(
        version=2,
        generated_at=incoming.generated_at,
        client_version=incoming.client_version,
        root=incoming.root,
        roots=roots,
        nodes=nodes,
        edges=edges,
        install_order=install_order,
        selection=incoming.selection,
        policy=incoming.policy,
        governance=incoming.governance,
    )
    replay_lockfile(merged)
    return merged


def _unique_roots(roots: list[LockRoot]) -> list[LockRoot]:
    return _unique_by_id(roots, lambda item: item.selected_node_id)


def _unique_edges(edges: list[LockedEdge]) -> list[LockedEdge]:
    return _unique_by_id(
        edges,
        lambda item: (
            item.source_node_id,
            item.target_node_id,
            item.edge_type,
            item.optional,
            tuple(item.markers),
        ),
    )


def _unique_strings(values: list[str]) -> list[str]:
    return _unique_by_id(values, lambda item: item)


Item = TypeVar("Item")


def _unique_by_id(items: list[Item], key: Callable[[Item], Hashable]) -> list[Item]:
    seen: set[Hashable] = set()
    result: list[Item] = []
    for item in items:
        item_key = key(item)
        if item_key not in seen:
            seen.add(item_key)
            result.append(item)
    return result
