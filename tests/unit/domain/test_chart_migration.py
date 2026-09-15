"""Unit tests for chart migration plans (LOT-11)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.charts.migration import (
    AccountMigration,
    CompanyChartMigrationPlan,
    MigrationChangeKind,
)


def _chart(v1_active: bool = True) -> CompanyChart:
    status = ChartStatus.ACTIVE if v1_active else ChartStatus.DRAFT
    return CompanyChart(
        chart_id="chart_1",
        entity_id=EntityId("ent_1"),
        code="STD-FR",
        label="Standard France",
        primary_standard="fr-pcg",
        code_policy_id="policy_1",
        reference_snapshot_id="snap1",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=status,
                effective_from=date(2026, 1, 1),
            ),
        ),
    )


def test_historical_versions_preserved_after_migration() -> None:
    chart = _chart()
    plan = CompanyChartMigrationPlan(
        source_chart_code="STD-FR",
        source_version="v1",
        target_version="v2",
        effective_date=date(2027, 1, 1),
        reason="Add 9-digit accounts",
    )
    planned = plan.apply_to(chart)
    activated = planned.activate("v2", effective_from=date(2027, 1, 1))
    labels = [v.label for v in activated.versions]
    assert "v1" in labels
    assert "v2" in labels
    assert activated.versions[0].status is ChartStatus.SUPERSEDED
    assert activated.versions[1].status is ChartStatus.ACTIVE


def test_plan_rejects_same_version() -> None:
    with pytest.raises(ValueError, match="differ"):
        CompanyChartMigrationPlan(
            source_chart_code="STD-FR",
            source_version="v1",
            target_version="v1",
            effective_date=date(2027, 1, 1),
            reason="same",
        )


def test_plan_rejects_wrong_chart() -> None:
    chart = CompanyChart(
        chart_id="other",
        entity_id=EntityId("ent_1"),
        code="OTHER",
        label="Other",
        primary_standard="fr-pcg",
        code_policy_id="p",
        reference_snapshot_id="s",
    )
    plan = CompanyChartMigrationPlan(
        source_chart_code="STD-FR",
        source_version="v1",
        target_version="v2",
        effective_date=date(2027, 1, 1),
        reason="test",
    )
    with pytest.raises(ValueError, match="targets chart"):
        plan.apply_to(chart)


def test_account_migrations_preserved_in_plan() -> None:
    plan = CompanyChartMigrationPlan(
        source_chart_code="STD-FR",
        source_version="v1",
        target_version="v2",
        effective_date=date(2027, 1, 1),
        reason="restructure",
        account_migrations=(
            AccountMigration(
                source_code="512",
                target_code="512001",
                kind=MigrationChangeKind.REMAPPED,
            ),
            AccountMigration(
                source_code="999",
                target_code=None,
                kind=MigrationChangeKind.RETIRED,
                reason="obsolete",
            ),
        ),
        retired_codes=("999",),
    )
    assert len(plan.account_migrations) == 2
    assert plan.retired_codes == ("999",)
