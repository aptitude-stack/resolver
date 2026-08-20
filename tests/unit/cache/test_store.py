from __future__ import annotations

from diskcache import JSONDisk

from aptitude_resolver.cache import (
    CacheStore,
    content_key,
    discovery_key,
    metadata_key,
    version_list_key,
)
from aptitude_resolver.domain.models import DiscoveryQuery, SkillCoordinate


def test_cache_store_round_trips_values(tmp_path) -> None:
    cache = CacheStore(tmp_path / "cache")

    try:
        cache.set("example", {"value": 42}, expire=60)
        assert cache.get("example") == {"value": 42}
    finally:
        cache.close()


def test_cache_store_uses_json_disk_serializer(tmp_path) -> None:
    cache = CacheStore(tmp_path / "cache")

    try:
        assert cache.disk_type is JSONDisk
    finally:
        cache.close()


def test_cache_keys_are_deterministic() -> None:
    first = discovery_key(
        DiscoveryQuery(
            query="postman",
            tags=["postman", "primary"],
            context_skills=[],
        )
    )
    second = discovery_key(
        DiscoveryQuery(
            query="postman",
            tags=["postman", "primary"],
            context_skills=[],
        )
    )

    assert first == second
    assert metadata_key("python-lint", "1.2.3") == "metadata:python-lint@1.2.3"
    assert version_list_key("python-lint") == "versions:python-lint"
    assert content_key(algorithm="sha256", digest="abc") == "content:sha256:abc"


def test_discovery_cache_key_includes_context_coordinates() -> None:
    without_context = DiscoveryQuery(query="lint", tags=[], context_skills=[])
    with_context = DiscoveryQuery(
        query="lint",
        tags=[],
        context_skills=[SkillCoordinate(slug="python-lint", version="1.2.3")],
    )

    assert discovery_key(without_context) != discovery_key(with_context)
