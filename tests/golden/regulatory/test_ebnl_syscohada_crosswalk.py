"""Golden LOT-27 reviewed structural crosswalk safety."""

from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.crosswalks import (
    EBNLSYSCOHADAStructuralCrosswalkAdapter,
)

ROOT = Path(__file__).parents[3]
DATA = ROOT / "resources/regulatory-accounting-data-framework/datasets/crosswalk"


def test_ebnl_syscohada_crosswalk_is_queryable_but_never_executable() -> None:
    crosswalk = EBNLSYSCOHADAStructuralCrosswalkAdapter(DATA).get_crosswalk()

    assert crosswalk.relation_type == "structural_code_delta"
    assert crosswalk.automatic_crosswalk_approval is False
    assert crosswalk.human_review_required_for_semantics is True
    assert crosswalk.inheritance_asserted is False
    assert crosswalk.semantic_equivalence_from_code_equality is False
    assert crosswalk.rows
    assert all(row.semantic_equivalence_asserted is False for row in crosswalk.rows)
    assert all(row.executable is False for row in crosswalk.rows)

    same_code = crosswalk.candidates_for("106")
    assert same_code
    assert same_code[0].semantic_equivalence_asserted is False

    with pytest.raises(PermissionError):
        crosswalk.require_executable_mapping("106")


def test_unknown_crosswalk_code_fails_closed() -> None:
    crosswalk = EBNLSYSCOHADAStructuralCrosswalkAdapter(DATA).get_crosswalk()
    with pytest.raises(KeyError):
        crosswalk.require_executable_mapping("__missing__")
