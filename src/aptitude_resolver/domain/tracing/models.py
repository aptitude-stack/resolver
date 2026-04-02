"""Trace models for deterministic explanation and audit output."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TraceEntry:
    """One explainable step in discovery, selection, or resolution."""

    stage: str
    action: str
    message: str
    data: dict[str, object] = field(default_factory=dict)
