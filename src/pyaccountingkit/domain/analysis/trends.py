"""Deterministic historical trend projections."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.domain.analysis.indicators import IndicatorValueStatus


class TrendDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class PeriodObservation:
    period_id: str
    as_of: date
    value: Decimal | None
    status: IndicatorValueStatus
    source_checksum: str

    def __post_init__(self) -> None:
        if not self.period_id.strip() or not self.source_checksum.strip():
            raise ValueError("trend observation period/checksum must not be empty")
        if self.status is IndicatorValueStatus.CALCULATED:
            if self.value is None or not self.value.is_finite():
                raise ValueError("calculated trend observation requires a finite Decimal")
        elif self.value is not None:
            raise ValueError("non-calculated trend observation must not carry a value")


@dataclass(frozen=True, slots=True)
class MetricTrend:
    metric_code: str
    observations: tuple[PeriodObservation, ...]
    direction: TrendDirection
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.metric_code.strip():
            raise ValueError("trend metric code must not be empty")
        if not self.observations:
            raise ValueError("trend requires at least one observation")
        periods = tuple(item.period_id for item in self.observations)
        if len(periods) != len(set(periods)):
            raise ValueError("trend observations must have unique period ids")
        object.__setattr__(self, "checksum", self._compute_checksum())

    @classmethod
    def build(
        cls,
        *,
        metric_code: str,
        observations: tuple[PeriodObservation, ...],
    ) -> MetricTrend:
        ordered = tuple(sorted(observations, key=lambda item: (item.as_of, item.period_id)))
        if len(ordered) < 2:
            return cls(
                metric_code=metric_code,
                observations=ordered,
                direction=TrendDirection.INDETERMINATE,
                absolute_change=None,
                percentage_change=None,
            )
        first = ordered[0]
        last = ordered[-1]
        if (
            first.status is not IndicatorValueStatus.CALCULATED
            or last.status is not IndicatorValueStatus.CALCULATED
            or first.value is None
            or last.value is None
        ):
            return cls(
                metric_code=metric_code,
                observations=ordered,
                direction=TrendDirection.INDETERMINATE,
                absolute_change=None,
                percentage_change=None,
            )
        change = last.value - first.value
        if change > 0:
            direction = TrendDirection.UP
        elif change < 0:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.STABLE
        percentage = None if first.value.is_zero() else change / abs(first.value) * Decimal("100")
        return cls(
            metric_code=metric_code,
            observations=ordered,
            direction=direction,
            absolute_change=change,
            percentage_change=percentage,
        )

    def _compute_checksum(self) -> str:
        payload = {
            "metric_code": self.metric_code,
            "direction": self.direction.value,
            "absolute_change": (
                str(self.absolute_change) if self.absolute_change is not None else None
            ),
            "percentage_change": (
                str(self.percentage_change) if self.percentage_change is not None else None
            ),
            "observations": [
                {
                    "period_id": item.period_id,
                    "as_of": item.as_of.isoformat(),
                    "value": str(item.value) if item.value is not None else None,
                    "status": item.status.value,
                    "source_checksum": item.source_checksum,
                }
                for item in self.observations
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


__all__ = ["MetricTrend", "PeriodObservation", "TrendDirection"]
