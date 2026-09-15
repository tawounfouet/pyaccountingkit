"""Unit tests for AccountingPolicySet aggregate (LOT-12)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import PolicyError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.policy_set import (
    AccountingPolicySet,
    PolicyBinding,
    PolicySetReference,
    PolicySetStatus,
    PolicyType,
)


def _ref() -> PolicySetReference:
    return PolicySetReference(
        standard_id="fr-pcg",
        edition="2026",
        dataset_version="v1",
        reference_snapshot_id="snap:1",
    )


def _draft_set(**overrides: object) -> AccountingPolicySet:
    defaults: dict[str, object] = {
        "policy_set_id": "ps:1",
        "accounting_entity_id": EntityId("ent:1"),
        "code": "STD-FR-2026",
        "version": "1.0",
        "reference": _ref(),
    }
    defaults.update(overrides)
    return AccountingPolicySet(**defaults)  # type: ignore[arg-type]


def _binding(policy_type: PolicyType = PolicyType.RECOGNITION) -> PolicyBinding:
    return PolicyBinding(
        policy_type=policy_type,
        policy_id="rec-line-1",
        policy_version="1.0",
    )


# --- Invariants ---


def test_empty_set_is_modifiable() -> None:
    ps = _draft_set()
    assert ps.is_modifiable
    assert ps.status is PolicySetStatus.DRAFT


def test_activation_transitions() -> None:
    ps = _draft_set()
    active = ps.activate(date(2026, 1, 1))
    assert active.status is PolicySetStatus.ACTIVE
    assert active.effective_from == date(2026, 1, 1)


def test_supersede_transitions() -> None:
    ps = _draft_set().activate(date(2026, 1, 1))
    superseded = ps.supersede(date(2026, 6, 30), reason="new standard")
    assert superseded.status is PolicySetStatus.SUPERSEDED
    assert superseded.effective_to == date(2026, 6, 30)


def test_retire_transitions() -> None:
    ps = _draft_set().activate(date(2026, 1, 1))
    retired = ps.retire(date(2027, 12, 31), reason="end of scope")
    assert retired.status is PolicySetStatus.RETIRED
    assert retired.effective_to == date(2027, 12, 31)


def test_cannot_activate_non_draft() -> None:
    ps = _draft_set().activate(date(2026, 1, 1))
    with pytest.raises(PolicyError, match="cannot be activated"):
        ps.activate(date(2027, 1, 1))


def test_cannot_supersede_non_active() -> None:
    ps = _draft_set()
    with pytest.raises(PolicyError, match="not ACTIVE"):
        ps.supersede(date(2026, 12, 31), reason="test")


def test_cannot_retire_non_active() -> None:
    ps = _draft_set()
    with pytest.raises(PolicyError, match="not ACTIVE"):
        ps.retire(date(2026, 12, 31), reason="test")


def test_effective_to_before_from_rejected() -> None:
    with pytest.raises(PolicyError, match="effective_to precedes effective_from"):
        _draft_set(effective_from=date(2027, 1, 1), effective_to=date(2026, 1, 1))


# --- Bindings ---


def test_add_binding_to_draft() -> None:
    ps = _draft_set().with_binding(_binding())
    assert len(ps.bindings) == 1


def test_duplicate_policy_type_rejected() -> None:
    ps = _draft_set().with_binding(_binding())
    with pytest.raises(PolicyError, match="already set"):
        ps.with_binding(_binding())


def test_cannot_mutate_active_set() -> None:
    ps = _draft_set().activate(date(2026, 1, 1))
    with pytest.raises(PolicyError, match="not modifiable"):
        ps.with_binding(_binding())


def test_multiple_different_policy_types_allowed() -> None:
    ps = _draft_set()
    ps = ps.with_binding(_binding(PolicyType.RECOGNITION))
    ps = ps.with_binding(
        PolicyBinding(
            policy_type=PolicyType.ROUNDING,
            policy_id="round-v1",
            policy_version="1.0",
        )
    )
    assert len(ps.bindings) == 2


def test_binding_for_returns_single() -> None:
    ps = _draft_set().with_binding(_binding())
    found = ps.binding_for(PolicyType.RECOGNITION)
    assert found is not None
    assert found.policy_id == "rec-line-1"


def test_binding_for_missing_type_returns_none() -> None:
    ps = _draft_set().with_binding(_binding())
    assert ps.binding_for(PolicyType.MEASUREMENT) is None


# --- INV-POLSET-004 reference pinned ---


def test_reference_fields_required() -> None:
    with pytest.raises(PolicyError, match="reference .* must be non-empty"):
        PolicySetReference(
            standard_id="",
            edition="2026",
            dataset_version="v1",
            reference_snapshot_id="snap:1",
        )


def test_policy_version_pinned_in_binding() -> None:
    b = _binding()
    assert b.policy_version == "1.0"
