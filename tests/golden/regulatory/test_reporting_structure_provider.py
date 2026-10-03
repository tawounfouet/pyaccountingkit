"""Golden qualification for LOT-27 reporting-structure providers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.reporting import (
    RegulatoryReportingStructureFilesystemAdapter,
)
from pyaccountingkit.domain.reporting.reference_reporting_model import ReferenceReportingNodeType

ROOT = Path(__file__).resolve().parents[3]
REPORTING = ROOT / "resources" / "regulatory-accounting-data-framework" / "datasets" / "reporting"


@pytest.fixture
def provider() -> RegulatoryReportingStructureFilesystemAdapter:
    return RegulatoryReportingStructureFilesystemAdapter(REPORTING)


def test_pcg_reporting_structure_is_materialized_and_hints_are_review_only(provider) -> None:
    models = provider.list_reporting_models(framework="PCG", edition="2026")
    assert len(models) == 4
    assert sum(len(model.nodes) for model in models) == 158
    assert all(node.account_hints_executable is False for model in models for node in model.nodes)
    assert any(node.account_hints for model in models for node in model.nodes)
    assert all(
        node.node_type is ReferenceReportingNodeType.UNSPECIFIED
        for model in models
        for node in model.nodes
    )


def test_nonprofit_reporting_structure_preserves_fail_closed_hint_policy(provider) -> None:
    models = provider.list_reporting_models(framework="FR_NONPROFIT", edition="2026")
    assert len(models) == 4
    assert sum(len(model.nodes) for model in models) == 160
    hinted = [node for model in models for node in model.nodes if node.account_hints]
    assert len(hinted) == 33
    assert all(node.human_validation_required for node in hinted)
    assert all(node.account_hints_executable is False for node in hinted)


def test_syscohada_reporting_structure_is_materialized(provider) -> None:
    models = provider.list_reporting_models(framework="SYSCOHADA", edition="2017")
    by_code = {model.model_code: len(model.nodes) for model in models}
    assert by_code == {"BALANCE": 48, "CASHFLOW": 23, "INCOME": 34, "NOTES": 46}
    assert all(node.account_hints_executable is False for model in models for node in model.nodes)
    assert all(
        node.node_type is ReferenceReportingNodeType.UNSPECIFIED
        for model in models
        for node in model.nodes
    )


def test_provider_requires_exact_snapshot_coordinates(provider) -> None:
    model = provider.list_reporting_models(framework="PCG", edition="2026")[0]
    assert (
        provider.get_reporting_model(
            reference_snapshot_id=model.reference_snapshot_id,
            framework="PCG",
            edition="2026",
            model_code=model.model_code,
        )
        == model
    )
    with pytest.raises(KeyError):
        provider.get_reporting_model(
            reference_snapshot_id="latest",
            framework="PCG",
            edition="2026",
            model_code=model.model_code,
        )


def test_ebnl_is_not_executable_until_line_level_transcription_is_complete(provider) -> None:
    with pytest.raises(KeyError):
        provider.list_reporting_models(framework="OHADA_EBNL", edition="2023")
