"""Unit tests for PolicyApplicability and PolicyContext (LOT-12)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyApplicability, PolicyContext


def _ctx(**overrides: object) -> PolicyContext:
    defaults: dict[str, object] = {
        "accounting_entity_id": EntityId("ent_test"),
        "accounting_date": date(2026, 6, 1),
    }
    defaults.update(overrides)
    return PolicyContext(**defaults)  # type: ignore[arg-type]


def test_empty_applicability_matches_any_context() -> None:
    assert PolicyApplicability().matches(_ctx())


def test_standard_mismatch_rejects() -> None:
    appl = PolicyApplicability(standard_id="fr-pcg")
    assert not appl.matches(_ctx(standard_id="ifrs"))


def test_standard_matches() -> None:
    appl = PolicyApplicability(standard_id="fr-pcg")
    assert appl.matches(_ctx(standard_id="fr-pcg"))


def test_declared_standard_rejects_missing_runtime_value() -> None:
    appl = PolicyApplicability(standard_id="fr-pcg")
    assert not appl.matches(_ctx(standard_id=None))


@pytest.mark.parametrize(
    ("applicability", "context_overrides"),
    [
        (PolicyApplicability(edition="2026"), {"edition": None}),
        (PolicyApplicability(jurisdiction="FR"), {"jurisdiction": None}),
        (PolicyApplicability(sector="BANKING"), {"sector": None}),
        (PolicyApplicability(account_type="ASSET"), {"account_type": None}),
        (
            PolicyApplicability(reference_concept_id="class:2"),
            {"reference_concept_id": None},
        ),
        (PolicyApplicability(asset_category="PPE"), {"asset_category": None}),
        (PolicyApplicability(liability_category="PROVISION"), {"liability_category": None}),
        (PolicyApplicability(transaction_type="SALE"), {"transaction_type": None}),
        (PolicyApplicability(journal_type="OD"), {"journal_type": None}),
    ],
)
def test_declared_criterion_rejects_missing_runtime_value(
    applicability: PolicyApplicability,
    context_overrides: dict[str, object],
) -> None:
    assert not applicability.matches(_ctx(**context_overrides))


def test_out_of_range_date_rejects() -> None:
    appl = PolicyApplicability(effective_from=date(2027, 1, 1))
    assert not appl.matches(_ctx())


def test_in_range_date_matches() -> None:
    appl = PolicyApplicability(effective_from=date(2026, 1, 1))
    assert appl.matches(_ctx())


def test_boundary_date_matches() -> None:
    appl = PolicyApplicability(effective_from=date(2026, 6, 1))
    assert appl.matches(_ctx())


def test_entity_specific_matches() -> None:
    appl = PolicyApplicability(accounting_entity_id=EntityId("ent_test"))
    assert appl.matches(_ctx())
    assert not PolicyApplicability(accounting_entity_id=EntityId("ent_b")).matches(_ctx())


def test_specificity_counts_declared_criteria() -> None:
    empty = PolicyApplicability()
    one = PolicyApplicability(standard_id="x")
    full = PolicyApplicability(
        standard_id="x",
        edition="2026",
        jurisdiction="FR",
        sector="BANKING",
        accounting_entity_id=EntityId("e"),
        transaction_type="SALE",
    )
    assert empty.specificity == 0
    assert one.specificity == 1
    assert full.specificity == 6


def test_policy_context_immutable() -> None:
    ctx = _ctx()
    with pytest.raises(AttributeError):
        ctx.standard_id = "x"  # type: ignore[misc]
