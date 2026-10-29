"""Bounded synchronous ACK delivery worker for the durable SQL outbox.

A durable receipt is created by SQL in the *same transaction* as revocation.
The worker can safely restart and duplicate HTTP delivery; upstream contract
MUST deduplicate Idempotency-Key. An ACK is NOT proof of prevention if the
recorded disposition is ALREADY_CONSUMED.
"""

from dataclasses import dataclass
from typing import Protocol

from .http_revocation_source import IamHttpUnavailable
from .revocation import IamRevocationReceipt


class AckLeasePort(Protocol):
    receipt: IamRevocationReceipt


class AckRepositoryPort(Protocol):
    def claim(self, limit: int) -> tuple[AckLeasePort, ...]: ...

    def delivered(self, lease: AckLeasePort) -> None: ...

    def failed(self, lease: AckLeasePort, error_code: str) -> str: ...


class AckSourcePort(Protocol):
    def acknowledge(self, receipt: IamRevocationReceipt) -> None: ...


@dataclass(frozen=True, slots=True)
class AckDeliveryBatch:
    claimed: int
    delivered: int
    retry: int
    dead: int


class IamAckDeliveryWorker:
    """No network activity before SQL claim transaction has committed."""

    def __init__(self, *, outbox: AckRepositoryPort, source: AckSourcePort) -> None:
        for method in ('claim', 'delivered', 'failed'):
            if not callable(getattr(outbox, method, None)):
                raise ValueError('Durable ACK outbox contract required')
        if not callable(getattr(source, 'acknowledge', None)):
            raise ValueError('Independent upstream acknowledgement source required')
        self._outbox = outbox
        self._source = source

    def run_once(self, *, limit: int = 10) -> AckDeliveryBatch:
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('Bounded delivery batch required')
        leases = self._outbox.claim(limit)
        delivered = retry = dead = 0
        for lease in leases:
            try:
                self._source.acknowledge(lease.receipt)
            except IamHttpUnavailable:
                state = self._outbox.failed(lease, 'NETWORK_ERROR')
                retry += state == 'RETRY'
                dead += state == 'DEAD'
            except Exception:
                # Never persist raw exception strings: could contain bearer secrets.
                state = self._outbox.failed(lease, 'UNKNOWN')
                retry += state == 'RETRY'
                dead += state == 'DEAD'
            else:
                # If DB confirmation fails, let the lease expire and retry with
                # the same upstream Idempotency-Key; never invent DELIVERED.
                self._outbox.delivered(lease)
                delivered += 1
        return AckDeliveryBatch(len(leases), delivered, retry, dead)
