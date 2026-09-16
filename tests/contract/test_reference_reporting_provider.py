"""Contract qualification for regulatory reporting model providers."""

from __future__ import annotations

import pytest

from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.domain.reporting.errors import RegulatoryModelNotFoundError
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)
from pyaccountingkit.ports.regulatory_reporting import ReferenceReportingModelProviderProtocol


def _model() -> ReferenceReportingModel:
    return ReferenceReportingModel(
        model_id="pcg-bs",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="pcg-2026",
        reference_snapshot_checksum="a" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="assets",
                code="ASSETS",
                label="Assets",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
            ),
        ),
    )


def test_provider_resolves_only_exact_coordinates() -> None:
    expected = _model()
    provider: ReferenceReportingModelProviderProtocol = InMemoryReferenceReportingModelProvider(
        (expected,)
    )

    resolved = provider.get_reporting_model(
        reference_snapshot_id="pcg-2026",
        framework="PCG",
        edition="2026",
        model_code="BALANCE_SHEET",
    )

    assert resolved is expected


@pytest.mark.parametrize(
    ("snapshot", "framework", "edition", "model_code"),
    [
        ("latest", "PCG", "2026", "BALANCE_SHEET"),
        ("pcg-2026", "SYSCOHADA", "2026", "BALANCE_SHEET"),
        ("pcg-2026", "PCG", "2025", "BALANCE_SHEET"),
        ("pcg-2026", "PCG", "2026", "INCOME_STATEMENT"),
    ],
)
def test_provider_fails_closed_for_non_exact_coordinates(
    snapshot: str,
    framework: str,
    edition: str,
    model_code: str,
) -> None:
    provider = InMemoryReferenceReportingModelProvider((_model(),))

    with pytest.raises(RegulatoryModelNotFoundError):
        provider.get_reporting_model(
            reference_snapshot_id=snapshot,
            framework=framework,
            edition=edition,
            model_code=model_code,
        )
