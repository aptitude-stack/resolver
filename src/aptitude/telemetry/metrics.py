"""Additive stage timing helpers for planning and materialization flows."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator, Protocol

import structlog


@dataclass(frozen=True)
class StageTiming:
    """One aggregated timing measurement for a named stage."""

    stage: str
    duration_ms: float


class TelemetryCollector:
    """Collect additive stage timings without affecting control flow."""

    def __init__(self) -> None:
        self._durations_ms: OrderedDict[str, float] = OrderedDict()

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        start = perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (perf_counter() - start) * 1000
            self._durations_ms[stage] = self._durations_ms.get(stage, 0.0) + elapsed_ms

    def snapshot(self) -> list[StageTiming]:
        return [
            StageTiming(stage=stage, duration_ms=round(duration_ms, 3))
            for stage, duration_ms in self._durations_ms.items()
        ]


class StageTimingLogger(Protocol):
    def info(self, event: str, **kwargs: object) -> None: ...


def emit_stage_timings(
    collector: TelemetryCollector,
    *,
    logger: StageTimingLogger | None = None,
) -> None:
    """Emit one structured log event per recorded stage timing."""

    bound_logger = logger or structlog.stdlib.get_logger("aptitude.telemetry")
    for timing in collector.snapshot():
        bound_logger.info(
            "pipeline_stage_timing",
            stage=timing.stage,
            duration_ms=timing.duration_ms,
        )
