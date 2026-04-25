from __future__ import annotations

import httpx
import pytest
from typing import Any


def build_publish_payload(
    *,
    version: str,
    raw_markdown: str,
    name: str,
    description: str,
    tags: list[str],
    token_estimate: int,
    maturity_score: float,
    security_score: float,
    depends_on: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one live publish payload that matches the current server schema."""

    return {
        "intent": "create_skill",
        "version": version,
        "content": {
            "raw_markdown": raw_markdown,
        },
        "metadata": {
            "name": name,
            "description": description,
            "tags": list(tags),
            "inputs_schema": {"type": "object"},
            "outputs_schema": {"type": "object"},
            "token_estimate": token_estimate,
            "maturity_score": maturity_score,
            "security_score": security_score,
        },
        "governance": {
            "trust_tier": "untrusted",
        },
        "relationships": {
            "depends_on": list(depends_on or []),
            "extends": [],
            "conflicts_with": [],
            "overlaps_with": [],
        },
    }


def ensure_publish_ready(response: httpx.Response) -> None:
    """Validate one live publish response or skip when writes are unavailable."""

    if response.status_code == 201:
        return

    if response.status_code in {401, 403}:
        pytest.skip(
            "Live integration server rejected the publish token. "
            "Set APTITUDE_PUBLISH_TOKEN or rely on APTITUDE_READ_TOKEN."
        )

    if response.status_code in {404, 405}:
        pytest.skip(
            "Live integration server does not expose the write endpoint used by "
            "publish-seeded registry integration tests: POST /skills/{slug}."
        )

    if response.status_code >= 500:
        pytest.skip(
            "Live integration server is not ready for publish-seeded registry tests: "
            f"publish returned {response.status_code}."
        )

    pytest.fail(
        "Live integration publish setup failed: "
        f"POST /skills/{{slug}} returned {response.status_code} with body {response.text!r}."
    )
