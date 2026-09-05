"""Strict SemVer parsing and comparison for registry-owned versions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
import re

from semver import Version as SemverVersion


_COMPARATOR_RE = re.compile(r"^(==|=|!=|>=|<=|>|<)[ \t]*(.+)$")
_MAX_CONSTRAINT_LENGTH = 200


@total_ordering
@dataclass(frozen=True)
class SkillVersion:
    """Comparable strict SemVer while preserving the authored string."""

    raw: str
    semver: SemverVersion

    @classmethod
    def parse(cls, value: str) -> SkillVersion:
        """Parse one strict SemVer without normalizing its authored string."""

        if not isinstance(value, str):
            raise ValueError("Skill version must be a string. Expected strict SemVer.")
        try:
            parsed = SemverVersion.parse(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid skill version '{value}'. Expected strict SemVer."
            ) from exc
        if str(parsed) != value:
            raise ValueError(f"Invalid skill version '{value}'. Expected strict SemVer.")
        return cls(raw=value, semver=parsed)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SkillVersion):
            return NotImplemented

        return self.semver < other.semver

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillVersion):
            return NotImplemented

        return self.semver == other.semver

    def __hash__(self) -> int:
        return hash(self.semver)


@dataclass(frozen=True)
class SemVerConstraint:
    """Comma-separated strict SemVer comparators joined with logical AND."""

    comparators: tuple[tuple[str, SkillVersion], ...]

    def contains(self, version: str | SkillVersion) -> bool:
        """Return whether an exact version satisfies every comparator."""

        candidate = (
            parse_skill_version(version) if isinstance(version, str) else version
        )
        for operator, expected in self.comparators:
            if operator in {"=", "=="} and candidate != expected:
                return False
            if operator == "!=" and candidate == expected:
                return False
            if operator == "<" and not candidate < expected:
                return False
            if operator == "<=" and candidate > expected:
                return False
            if operator == ">" and not candidate > expected:
                return False
            if operator == ">=" and candidate < expected:
                return False
        return True


def parse_skill_version(value: str) -> SkillVersion:
    """Return a strict SemVer ordering key for one skill version."""

    return SkillVersion.parse(value)


def parse_semver_constraint(value: str) -> SemVerConstraint:
    """Parse one bounded comma-separated strict SemVer constraint."""

    if not isinstance(value, str) or not value or len(value) > _MAX_CONSTRAINT_LENGTH:
        raise ValueError("Invalid SemVer constraint.")

    comparators: list[tuple[str, SkillVersion]] = []
    for raw_part in value.split(","):
        part = raw_part.strip(" \t")
        match = _COMPARATOR_RE.fullmatch(part)
        if match is None:
            raise ValueError(f"Invalid SemVer constraint comparator: {raw_part!r}.")
        operator, operand = match.groups()
        try:
            parsed_operand = parse_skill_version(operand.strip(" \t"))
        except ValueError as exc:
            raise ValueError(
                f"Invalid SemVer constraint operand: {operand!r}."
            ) from exc
        comparators.append((operator, parsed_operand))

    if not comparators:
        raise ValueError("Invalid SemVer constraint.")
    return SemVerConstraint(tuple(comparators))
