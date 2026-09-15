"""Injectable clock for business time (never ``datetime.now()`` in the domain)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, final


class ClockProtocol(Protocol):
    """Contract for any business-time source. Times are timezone-aware UTC."""

    def now(self) -> datetime: ...


@final
class SystemClock:
    """Wall-clock source backed by the host system clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@final
class FrozenClock:
    """Deterministic clock for tests and replays."""

    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed if fixed is not None else datetime(2024, 1, 1, tzinfo=UTC)
        if self._fixed.tzinfo is None or self._fixed.utcoffset() is None:
            raise ValueError("FrozenClock requires a timezone-aware datetime")

    def now(self) -> datetime:
        return self._fixed


__all__ = ["ClockProtocol", "SystemClock", "FrozenClock"]
