"""Unit tests for company chart versioning (LOT-11)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)


def _chart(version_label: str = "v1", effective: date = date(2026, 1, 1)) -> CompanyChart:
    return CompanyChart(
        chart_id="chart_ent_1",
        entity_id=EntityId("ent_1"),
        code="STD-FR",
        label="Standard France",
        primary_standard="fr-pcg",
        code_policy_id="numeric-fixed-8",
        reference_snapshot_id="snap1",
        versions=(
            CompanyChartVersion(
                label=version_label,
                status=ChartStatus.ACTIVE,
                effective_from=effective,
            ),
        ),
    )


def test_current_active_version() -> None:
    chart = _chart()
    assert chart.current_active_version is not None
    assert chart.current_active_version.label == "v1"


def test_plan_version_adds_draft() -> None:
    chart = _chart()
    planned = chart.plan_version("v2", effective_from=date(2027, 1, 1))
    assert len(planned.versions) == 2
    assert planned.versions[1].status is ChartStatus.DRAFT


def test_activate_supersedes_previous() -> None:
    chart = _chart()
    planned = chart.plan_version("v2", effective_from=date(2027, 1, 1))
    activated = planned.activate("v2", effective_from=date(2027, 1, 1))
    versions = activated.versions
    assert versions[0].status is ChartStatus.SUPERSEDED
    assert versions[0].effective_to == date(2027, 1, 1)
    assert versions[1].status is ChartStatus.ACTIVE
    assert versions[1].effective_from == date(2027, 1, 1)


def test_historical_versions_preserved_after_supersede() -> None:
    chart = _chart()
    planned = chart.plan_version("v2", effective_from=date(2027, 1, 1))
    activated = planned.activate("v2", effective_from=date(2027, 1, 1))
    labels = [v.label for v in activated.versions]
    assert "v1" in labels
    assert "v2" in labels


def test_duplicate_version_label_rejected() -> None:
    chart = _chart()
    with pytest.raises(ValueError, match="already exists"):
        chart.plan_version("v1", effective_from=date(2027, 1, 1))


def test_overlapping_active_versions_rejected() -> None:
    chart = _chart()
    with pytest.raises(ValueError, match="before a previous version"):
        chart.plan_version("v2", effective_from=date(2025, 1, 1))
