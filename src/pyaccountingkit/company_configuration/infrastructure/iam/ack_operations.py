"""Bounded IAM ACK delivery operations with no implicit background execution.

Deployment is responsible for starting and stopping the runner. Every cycle
produces aggregate, non-secret telemetry and explicit alert flags.
"""

from dataclasses import dataclass
from typing import Protocol

from .ack_delivery import AckDeliveryBatch, IamAckDeliveryWorker


class MetricsReaderPort(Protocol):
    def snapshot(self) -> object: ...


class TelemetrySinkPort(Protocol):
    def report(self, sample: "IamAckOperationalSample") -> None: ...


@dataclass(frozen=True, slots=True)
class IamAckOperationalSample:
    batch: AckDeliveryBatch
    pending: int
    in_flight: int
    retry: int
    delivered_total: int
    dead: int
    stale_leases: int
    due_count: int
    oldest_open_seconds: int
    alert_dead: bool
    alert_backlog: bool


class IamAckOperationsRunner:
    """A single synchronous, bounded cycle; suitable for an external scheduler."""

    def __init__(
        self, *, worker: IamAckDeliveryWorker, metrics: MetricsReaderPort,
        telemetry: TelemetrySinkPort, backlog_threshold_seconds: int = 300,
    ) -> None:
        if not isinstance(backlog_threshold_seconds, int) or not (
            30 <= backlog_threshold_seconds <= 86400
        ):
            raise ValueError("Bounded backlog threshold required")
        self._worker = worker
        self._metrics = metrics
        self._telemetry = telemetry
        self._backlog_threshold = backlog_threshold_seconds

    def tick(self, *, limit: int = 10) -> IamAckOperationalSample:
        batch = self._worker.run_once(limit=limit)
        metrics = self._metrics.snapshot()
        sample = IamAckOperationalSample(
            batch=batch, pending=metrics.pending, in_flight=metrics.in_flight,
            retry=metrics.retry, delivered_total=metrics.delivered,
            dead=metrics.dead, stale_leases=metrics.stale_leases,
            due_count=metrics.due_count,
            oldest_open_seconds=metrics.oldest_open_seconds,
            alert_dead=metrics.dead > 0,
            alert_backlog=(metrics.oldest_open_seconds >= self._backlog_threshold),
        )
        # Monitoring outages fail visibly, never report a successful healthy tick.
        self._telemetry.report(sample)
        return sample
