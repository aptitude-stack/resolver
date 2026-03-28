"""Lockfile parsing helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aptitude_client.domain.errors import InvalidLockfileError
from aptitude_client.lockfile.model import (
    GovernanceSnapshotEntry,
    LockRoot,
    Lockfile,
    LockedEdge,
    LockedSkill,
    PolicySnapshot,
    SelectionSnapshot,
)


def parse_lockfile(payload: str) -> Lockfile:
    """Parse one JSON lockfile payload into the typed lock model."""

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise InvalidLockfileError("Lockfile is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise InvalidLockfileError("Lockfile payload must be a JSON object.")

    root_data = _expect_dict(data, "root")
    nodes_data = _expect_list(data, "nodes")
    edges_data = _expect_list(data, "edges")
    selection_data = _expect_optional_dict(data, "selection")
    policy_data = _expect_optional_dict(data, "policy")
    governance_data = _expect_list(data, "governance")

    return Lockfile(
        version=_expect_int(data, "version"),
        generated_at=_expect_optional_str(data, "generated_at"),
        client_version=_expect_optional_str(data, "client_version"),
        root=LockRoot(
            request=_expect_str(root_data, "request"),
            requested_version=_expect_optional_str(root_data, "requested_version"),
            selected_node_id=_expect_str(root_data, "selected_node_id"),
            selection_mode=_expect_str(root_data, "selection_mode"),
        ),
        nodes=[
            LockedSkill(
                node_id=_expect_str(node_data, "node_id"),
                slug=_expect_str(node_data, "slug"),
                version=_expect_str(node_data, "version"),
                artifact_ref=_expect_str(node_data, "artifact_ref"),
                name=_expect_str(node_data, "name"),
                description=_expect_str(node_data, "description"),
                tags=_expect_str_list(node_data, "tags"),
                headers=_expect_str_dict(node_data, "headers"),
                rendered_summary=_expect_str(node_data, "rendered_summary"),
                lifecycle_status=_expect_str(node_data, "lifecycle_status"),
                trust_tier=_expect_str(node_data, "trust_tier"),
                published_at=_expect_str(node_data, "published_at"),
                content_checksum_algorithm=_expect_str(
                    _expect_dict(node_data, "content_checksum"),
                    "algorithm",
                ),
                content_checksum_digest=_expect_str(
                    _expect_dict(node_data, "content_checksum"),
                    "digest",
                ),
                content_size_bytes=_expect_optional_int(
                    _expect_dict(node_data, "content_checksum"),
                    "size_bytes",
                ),
            )
            for node_data in (_expect_mapping(item, "nodes item") for item in nodes_data)
        ],
        edges=[
            LockedEdge(
                source_node_id=_expect_str(edge_data, "source_node_id"),
                target_node_id=_expect_str(edge_data, "target_node_id"),
                edge_type=_expect_str(edge_data, "edge_type"),
                optional=_expect_bool(edge_data, "optional"),
                markers=_expect_str_list(edge_data, "markers"),
            )
            for edge_data in (_expect_mapping(item, "edges item") for item in edges_data)
        ],
        install_order=_expect_str_list(data, "install_order"),
        selection=(
            SelectionSnapshot(
                profile=_expect_str(selection_data, "profile"),
                interaction_mode=_expect_str(selection_data, "interaction_mode"),
                profile_source=_expect_str(selection_data, "profile_source"),
                interaction_mode_source=_expect_str(selection_data, "interaction_mode_source"),
            )
            if selection_data is not None
            else None
        ),
        policy=(
            PolicySnapshot(
                profile=_expect_str(policy_data, "profile"),
                source=_expect_str(policy_data, "source"),
                allowed_lifecycle_statuses=_expect_str_list(
                    policy_data,
                    "allowed_lifecycle_statuses",
                ),
                allowed_trust_tiers=_expect_str_list(policy_data, "allowed_trust_tiers"),
                max_token_estimate=_expect_optional_int(policy_data, "max_token_estimate"),
                max_content_size_bytes=_expect_optional_int(
                    policy_data,
                    "max_content_size_bytes",
                ),
            )
            if policy_data is not None
            else None
        ),
        governance=[
            GovernanceSnapshotEntry(
                rule=_expect_str(item_data, "rule"),
                passed=_expect_bool(item_data, "passed"),
                message=_expect_str(item_data, "message"),
                node_id=_expect_optional_str(item_data, "node_id"),
            )
            for item_data in (_expect_mapping(item, "governance item") for item in governance_data)
        ],
    )


def load_lockfile(path: Path) -> Lockfile:
    """Load and parse one lockfile from disk."""

    return parse_lockfile(path.read_text(encoding="utf-8"))


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidLockfileError(f"Lockfile {label} must be an object.")
    return value


def _expect_dict(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = data.get(field_name)
    if not isinstance(value, dict):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be an object.")
    return value


def _expect_list(data: dict[str, Any], field_name: str) -> list[Any]:
    value = data.get(field_name)
    if not isinstance(value, list):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be a list.")
    return value


def _expect_optional_dict(data: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be an object or null.")
    return value


def _expect_str(data: dict[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be a string.")
    return value


def _expect_optional_str(data: dict[str, Any], field_name: str) -> str | None:
    value = data.get(field_name)
    if value is None or isinstance(value, str):
        return value
    raise InvalidLockfileError(f"Lockfile field '{field_name}' must be a string or null.")


def _expect_int(data: dict[str, Any], field_name: str) -> int:
    value = data.get(field_name)
    if not isinstance(value, int):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be an integer.")
    return value


def _expect_optional_int(data: dict[str, Any], field_name: str) -> int | None:
    value = data.get(field_name)
    if value is None or isinstance(value, int):
        return value
    raise InvalidLockfileError(f"Lockfile field '{field_name}' must be an integer or null.")


def _expect_bool(data: dict[str, Any], field_name: str) -> bool:
    value = data.get(field_name)
    if not isinstance(value, bool):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be a boolean.")
    return value


def _expect_str_list(data: dict[str, Any], field_name: str) -> list[str]:
    value = data.get(field_name)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be a list of strings.")
    return list(value)


def _expect_str_dict(data: dict[str, Any], field_name: str) -> dict[str, str]:
    value = data.get(field_name)
    if not isinstance(value, dict):
        raise InvalidLockfileError(f"Lockfile field '{field_name}' must be an object.")
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()):
        raise InvalidLockfileError(
            f"Lockfile field '{field_name}' must be a string-to-string object."
        )
    return {key: value[key] for key in sorted(value)}
