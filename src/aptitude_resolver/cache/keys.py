"""Deterministic cache-key helpers for advisory client caching."""

from __future__ import annotations

import hashlib
import json
from typing import Protocol


class DiscoveryQueryLike(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str | None: ...

    @property
    def tags(self) -> list[str]: ...


def metadata_key(slug: str, version: str) -> str:
    return f"metadata:{slug}@{version}"


def version_list_key(slug: str) -> str:
    return f"versions:{slug}"


def discovery_key(query: DiscoveryQueryLike) -> str:
    payload = {
        "name": query.name,
        "description": query.description,
        "tags": list(query.tags),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "discovery:" + hashlib.sha256(encoded).hexdigest()


def content_key(*, algorithm: str, digest: str) -> str:
    return f"content:{algorithm}:{digest}"


def coordinate_content_key(slug: str, version: str) -> str:
    return f"content-coordinate:{slug}@{version}"
