"""Deterministic cache-key helpers for advisory client caching."""

from __future__ import annotations

import hashlib
import json

from aptitude.domain.models import DiscoveryQuery


def metadata_key(slug: str, version: str) -> str:
    return f"metadata:{slug}@{version}"


def version_list_key(slug: str) -> str:
    return f"versions:{slug}"


def discovery_key(query: DiscoveryQuery) -> str:
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
