"""Release 0.4 replay qualification across subledger and analysis evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.domain.analysis.indicators import IndicatorValueStatus
from pyaccountingkit.domain.analysis.trends import MetricTrend, PeriodObservation
from tests.support.financial_analysis import run_golden_analysis


def _trend(observations: tuple[PeriodObservation, ...]) -> MetricTrend:
    return MetricTrend.build(metric_code="NET_MARGIN", observations=observations)


def test_release_0_4_analysis_snapshot_and_trend_replay_are_deterministic() -> None:
    first = run_golden_analysis(
        analysis_snapshot_id="analysis:release:first",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )
    replay = run_golden_analysis(
        analysis_snapshot_id="analysis:release:replay",
        generated_at=datetime(2029, 7, 1, tzinfo=UTC),
    )

    assert first.result_checksum == replay.result_checksum
    assert first.analysis_snapshot.checksum == replay.analysis_snapshot.checksum
    assert first.analysis_snapshot.snapshot_id != replay.analysis_snapshot.snapshot_id
    assert first.analysis_snapshot.generated_at != replay.analysis_snapshot.generated_at

    observations = (
        PeriodObservation(
            period_id="2025",
            as_of=date(2025, 12, 31),
            value=Decimal("15"),
            status=IndicatorValueStatus.CALCULATED,
            source_checksum="analysis-source-2025",
        ),
        PeriodObservation(
            period_id="2026",
            as_of=date(2026, 12, 31),
            value=Decimal("20"),
            status=IndicatorValueStatus.CALCULATED,
            source_checksum=first.analysis_snapshot.checksum,
        ),
    )
    forward = _trend(observations)
    reordered = _trend(tuple(reversed(observations)))

    assert forward.direction == reordered.direction
    assert forward.absolute_change == Decimal("5")
    assert forward.percentage_change == Decimal("33.33333333333333333333333333")
    assert forward.checksum == reordered.checksum
