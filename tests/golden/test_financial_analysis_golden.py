"""Golden LOT-20 historical financial-analysis scenario."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tests.support.financial_analysis import run_golden_analysis


def test_golden_financial_analysis_from_report_snapshot() -> None:
    run = run_golden_analysis(
        analysis_snapshot_id="analysis:golden:2026",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )
    indicators = dict(run.indicator_values)
    ratios = dict(run.ratio_values)

    assert indicators == {
        "CAF": Decimal("230.00"),
        "EBE": Decimal("350.00"),
        "EBITDA": Decimal("360.00"),
        "GROSS_MARGIN": Decimal("600.00"),
    }
    assert ratios["NET_MARGIN"] == Decimal("20")
    assert ratios["CURRENT_RATIO"] == Decimal("1.888888888888888888888888889")
    assert ratios["DEBT_TO_ASSETS"] == Decimal("0.3333333333333333333333333333")
    assert ratios["EQUITY_RATIO"] == Decimal("0.6666666666666666666666666667")
    assert ratios["CFO_TO_REVENUE"] == Decimal("0.28")
    assert ratios["ASSET_TURNOVER"] == Decimal("0.5555555555555555555555555556")
    assert run.frng.amount == Decimal("400.00")
    assert run.bfr.amount == Decimal("250.00")
    assert run.net_treasury.amount == Decimal("150.00")
    assert run.reconciled is True
    assert len(run.analysis_snapshot.checksum) == 64
