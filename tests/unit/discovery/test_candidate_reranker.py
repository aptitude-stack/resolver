from __future__ import annotations

from aptitude_client.discovery.intent import parse_search_intent
from aptitude_client.discovery.reranking import rerank_candidates
from aptitude_client.domain.models import DiscoveryCandidate, SkillCoordinate, VersionSummary



def _candidate(
    slug: str,
    version: str,
    *,
    name: str,
    tags: list[str],
    runtime: str,
    trust_tier: str = "internal",
    published_at: str = "2026-03-18T00:00:00Z",
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        slug=slug,
        selected_version=VersionSummary(
            coordinate=SkillCoordinate(slug=slug, version=version),
            name=name,
            description=f"{name} description",
            tags=tags,
            headers={"runtime": runtime},
            rendered_summary=f"{name} summary",
            lifecycle_status="published",
            trust_tier=trust_tier,
            published_at=published_at,
            content_checksum_algorithm="sha256",
            content_checksum_digest=f"digest-{slug}-{version}",
            content_size_bytes=256,
            token_estimate=100,
            maturity_score=0.9,
            security_score=0.95,
        ),
        labels=tags + [runtime],
        matched_labels=[],
        match_reasons=["server_candidate"],
    )



def test_rerank_candidates_prefers_exact_name_runtime_and_tags() -> None:
    intent = parse_search_intent("python lint")

    ranked = rerank_candidates(
        intent,
        [
            _candidate(
                "generic.lint",
                "3.0.0",
                name="Generic Lint",
                tags=["lint"],
                runtime="bash",
            ),
            _candidate(
                "python.lint",
                "1.2.3",
                name="Python Lint",
                tags=["python", "lint"],
                runtime="python",
            ),
        ],
    )

    assert [item.slug for item in ranked] == ["python.lint", "generic.lint"]
    assert [item.ranking_position for item in ranked] == [1, 2]
