"""Version ordering for registry-owned skill versions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering

from packaging.version import InvalidVersion, Version as Pep440Version
from semver import Version as SemverVersion


@total_ordering
@dataclass(frozen=True)
class SkillVersion:
    """Comparable skill version that accepts SemVer and PEP 440 inputs."""

    raw: str
    semver: SemverVersion | None
    pep440: Pep440Version | None

    @classmethod
    def parse(cls, value: str) -> SkillVersion:
        """Parse one skill version using SemVer and PEP 440 compatibility."""

        raw = value.strip()
        semver = _parse_semver(raw)
        pep440 = _parse_pep440(raw)
        if semver is None and pep440 is None:
            raise ValueError(
                f"Invalid skill version '{value}'. Expected SemVer or PEP 440."
            )
        return cls(raw=raw, semver=semver, pep440=pep440)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SkillVersion):
            return NotImplemented

        if self.semver is not None and other.semver is not None:
            return self.semver < other.semver
        if self.pep440 is not None and other.pep440 is not None:
            return self.pep440 < other.pep440
        return self._fallback_key() < other._fallback_key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillVersion):
            return NotImplemented

        if self.semver is not None and other.semver is not None:
            return self.semver == other.semver
        if self.pep440 is not None and other.pep440 is not None:
            return self.pep440 == other.pep440
        return self._fallback_key() == other._fallback_key()

    def _fallback_key(self) -> tuple[object, ...]:
        return (
            self._release_key(),
            self._stage_rank(),
            self.raw,
        )

    def _release_key(self) -> tuple[int, ...]:
        if self.semver is not None:
            return _trim_trailing_zeroes(
                (self.semver.major, self.semver.minor, self.semver.patch)
            )
        if self.pep440 is not None:
            return _trim_trailing_zeroes(tuple(self.pep440.release))
        return ()

    def _stage_rank(self) -> int:
        if self.semver is not None:
            return 1 if self.semver.prerelease else 2
        if self.pep440 is None:
            return 0
        if self.pep440.dev is not None:
            return 0
        if self.pep440.pre is not None:
            return 1
        if self.pep440.post is not None:
            return 3
        return 2


def parse_skill_version(value: str) -> SkillVersion:
    """Return a deterministic ordering key for one skill version."""

    return SkillVersion.parse(value)


def _parse_semver(value: str) -> SemverVersion | None:
    try:
        return SemverVersion.parse(value)
    except ValueError:
        return None


def _parse_pep440(value: str) -> Pep440Version | None:
    try:
        return Pep440Version(value)
    except InvalidVersion:
        return None


def _trim_trailing_zeroes(values: tuple[int, ...]) -> tuple[int, ...]:
    trimmed = values
    while len(trimmed) > 1 and trimmed[-1] == 0:
        trimmed = trimmed[:-1]
    return trimmed
