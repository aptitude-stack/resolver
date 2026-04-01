from __future__ import annotations

import json
from typing import cast

import pytest

from aptitude_client.domain.errors import InvalidLockfileError
from aptitude_client.lockfile import parse_lockfile


def _minimal_lock_payload() -> dict[str, object]:
    return {
        "version": 1,
        "generated_at": "2026-03-28T00:00:00Z",
        "client_version": None,
        "root": {
            "request": "python lint",
            "requested_version": None,
            "selected_node_id": "python.lint@1.2.3",
            "selection_mode": "single_candidate",
        },
        "nodes": [
            {
                "node_id": "python.lint@1.2.3",
                "slug": "python.lint",
                "version": "1.2.3",
                "artifact_ref": "/skills/python.lint/1.2.3/content",
                "name": "Python Lint",
                "description": "Lint Python files.",
                "tags": ["lint"],
                "headers": {"runtime": "python"},
                "rendered_summary": "Lint Python files.",
                "lifecycle_status": "published",
                "trust_tier": "internal",
                "published_at": "2026-03-28T00:00:00Z",
                "content_checksum": {
                    "algorithm": "sha256",
                    "digest": "digest-python.lint-1.2.3",
                    "size_bytes": 256,
                },
            }
        ],
        "edges": [],
        "install_order": ["python.lint@1.2.3"],
        "governance": [],
    }


def test_parse_lockfile_rejects_malformed_json() -> None:
    with pytest.raises(InvalidLockfileError, match="not valid JSON"):
        parse_lockfile("{")


def test_parse_lockfile_rejects_non_object_top_level_payload() -> None:
    with pytest.raises(InvalidLockfileError, match="must be a JSON object"):
        parse_lockfile(json.dumps(["not", "an", "object"]))


def test_parse_lockfile_rejects_missing_required_field() -> None:
    payload = _minimal_lock_payload()
    root_payload = cast(dict[str, object], payload["root"])
    del root_payload["selected_node_id"]

    with pytest.raises(InvalidLockfileError, match="selected_node_id"):
        parse_lockfile(json.dumps(payload))


def test_parse_lockfile_accepts_older_payload_without_selection_or_policy_snapshot() -> (
    None
):
    parsed = parse_lockfile(json.dumps(_minimal_lock_payload()))

    assert parsed.root.selected_node_id == "python.lint@1.2.3"
    assert parsed.selection is None
    assert parsed.policy is None
