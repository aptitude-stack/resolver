"""Intent parsing for discovery-driven CLI flows."""

from __future__ import annotations

import re

from aptitude.domain.models import SearchIntent


WORD_RE = re.compile(r"[A-Za-z0-9._-]+")
STOP_WORDS = {"a", "an", "for", "the", "skill", "skills", "find", "need", "want"}
LANGUAGE_ALIASES = {
    "python": "python",
    "py": "python",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "java": "java",
    "go": "go",
    "rust": "rust",
}
TRUST_KEYWORDS = {
    "verified": "verified",
    "trusted": "verified",
    "secure": "verified",
    "internal": "internal",
    "untrusted": "untrusted",
}


def parse_search_intent(query: str) -> SearchIntent:
    """Convert a raw user query into a normalized search intent."""

    normalized_query = normalize_text(query)
    terms = [token for token in WORD_RE.findall(normalized_query) if token]
    preferred_labels = [term for term in terms if term not in STOP_WORDS]

    language = None
    trust_preference = None
    for label in preferred_labels:
        if language is None and label in LANGUAGE_ALIASES:
            language = LANGUAGE_ALIASES[label]
        if trust_preference is None and label in TRUST_KEYWORDS:
            trust_preference = TRUST_KEYWORDS[label]

    preferred_tags = list(dict.fromkeys(preferred_labels))

    return SearchIntent(
        raw_query=query,
        normalized_query=normalized_query,
        terms=terms,
        preferred_tags=preferred_tags,
        preferred_labels=preferred_tags,
        language=language,
        trust_preference=trust_preference,
    )


def normalize_text(value: str) -> str:
    """Normalize user-facing search text for deterministic comparisons."""

    return " ".join(WORD_RE.findall(value.lower()))
