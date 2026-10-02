"""Golden LOT-27 EBNL reporting-registry qualification."""

from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.reporting import EBNLReportingRegistryAdapter
from pyaccountingkit.domain.reporting.regulatory_registry import INCOMPLETE_LINE_EXTRACTION

ROOT = Path(__file__).parents[3]
REPORTING = ROOT / "resources/regulatory-accounting-data-framework/datasets/reporting"


def test_ebnl_reporting_registry_preserves_source_scope_without_execution() -> None:
    registry = EBNLReportingRegistryAdapter(REPORTING).get_registry()

    assert registry.standard_id == "ohada-ebnl"
    assert registry.edition == "2023"
    assert len(registry.profiles) == 3
    assert len(registry.statements) == 13
    assert registry.automatic_filing_generation is False
    assert registry.template_visual_verification_required is True
    assert all(
        statement.line_level_extraction_status == INCOMPLETE_LINE_EXTRACTION
        for statement in registry.statements
    )
    assert all(statement.line_level_executable is False for statement in registry.statements)

    minimal = next(profile for profile in registry.profiles if profile.profile_id == "minimal_cash_system")
    assert len(minimal.eligibility_thresholds) == 5
    assert all(rule.value == 30_000_000 for rule in minimal.eligibility_thresholds)
    assert all(rule.currency == "XAF" for rule in minimal.eligibility_thresholds)


def test_ebnl_reporting_registry_fails_closed_for_line_level_execution() -> None:
    registry = EBNLReportingRegistryAdapter(REPORTING).get_registry()

    with pytest.raises(PermissionError):
        registry.require_line_level_model("association_professional_order", "balance_sheet")

    with pytest.raises(KeyError):
        registry.require_line_level_model("association_professional_order", "__missing__")
