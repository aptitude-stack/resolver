from __future__ import annotations

from aptitude_client.telemetry import TelemetryCollector, emit_stage_timings


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def info(self, event: str, **kwargs) -> None:
        self.events.append((event, kwargs))


def test_telemetry_collector_aggregates_repeated_stage_measurements() -> None:
    collector = TelemetryCollector()

    with collector.measure("governance"):
        pass
    with collector.measure("governance"):
        pass
    with collector.measure("lock"):
        pass

    snapshot = collector.snapshot()

    assert [item.stage for item in snapshot] == ["governance", "lock"]
    assert snapshot[0].duration_ms >= 0
    assert snapshot[1].duration_ms >= 0


def test_emit_stage_timings_logs_one_event_per_stage() -> None:
    collector = TelemetryCollector()
    logger = FakeLogger()

    with collector.measure("discovery"):
        pass
    with collector.measure("execution_planning"):
        pass

    emit_stage_timings(collector, logger=logger)

    assert [event for event, _ in logger.events] == [
        "pipeline_stage_timing",
        "pipeline_stage_timing",
    ]
    assert logger.events[0][1]["stage"] == "discovery"
    assert logger.events[1][1]["stage"] == "execution_planning"
