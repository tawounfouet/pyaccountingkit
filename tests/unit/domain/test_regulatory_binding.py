"""Unit tests for regulatory account bindings and mapping candidates (LOT-11)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import AccountRuleError
from pyaccountingkit.domain.charts.regulatory_binding import (
    BindingPurpose,
    BindingStatus,
    ChartBindingRegistry,
    MappingCandidate,
    RegulatoryAccountBinding,
)

_SNAPSHOT = "snap1"
_STANDARD = "fr-pcg"


def _candidate(
    id_: str = "c1",
    company_code: str = "512001",
    ref_id: str = "account:fr-pcg:2026:512",
) -> MappingCandidate:
    return MappingCandidate(
        id=id_,
        company_account_code=company_code,
        reference_node_id=ref_id,
        reference_standard_id=_STANDARD,
        reference_snapshot_id=_SNAPSHOT,
        reason="test",
    )


def test_candidate_is_not_active_binding() -> None:
    candidate = _candidate()
    with pytest.raises(AccountRuleError, match="candidate"):
        RegulatoryAccountBinding(
            id=candidate.id,
            company_account_code=candidate.company_account_code,
            reference_node_id=candidate.reference_node_id,
            reference_standard_id=candidate.reference_standard_id,
            reference_snapshot_id=candidate.reference_snapshot_id,
            status=BindingStatus.CANDIDATE,
        )


def test_promote_candidate_creates_active_binding() -> None:
    registry = ChartBindingRegistry()
    registry = registry.add_candidate(_candidate())
    promoted_registry, binding = registry.promote_candidate(
        _candidate(),
        purpose=BindingPurpose.PRIMARY_STATUTORY,
        effective_from=date(2026, 1, 1),
    )
    assert binding.status is BindingStatus.ACTIVE
    assert binding.reference_node_id == "account:fr-pcg:2026:512"
    assert promoted_registry.candidates() == ()
    assert len(promoted_registry.bindings()) == 1
    assert len(promoted_registry.versions()) == 1


def test_separate_candidates_from_active_bindings() -> None:
    registry = ChartBindingRegistry()
    registry = registry.add_candidate(_candidate(company_code="512001"))
    registry = registry.add_candidate(_candidate(id_="c2", company_code="512002"))
    assert len(registry.candidates()) == 2
    assert len(registry.bindings()) == 0


def test_retire_binding_preserves_history() -> None:
    registry = ChartBindingRegistry()
    registry = registry.add_candidate(_candidate())
    registry, _ = registry.promote_candidate(
        _candidate(),
        purpose=BindingPurpose.PRIMARY_STATUTORY,
        effective_from=date(2026, 1, 1),
    )
    retired = registry.retire("512001", effective_to=date(2026, 12, 31))
    assert retired.bindings()[0].status is BindingStatus.RETIRED
    assert len(retired.versions()) == 1


def test_candidates_for_reference() -> None:
    registry = ChartBindingRegistry()
    registry = registry.add_candidate(_candidate(company_code="512001"))
    registry = registry.add_candidate(
        _candidate(
            id_="c2",
            company_code="512002",
            ref_id="account:fr-pcg:2026:401",
        )
    )
    assert len(registry.candidates_for_reference("account:fr-pcg:2026:512")) == 1


def test_duplicate_candidate_rejected() -> None:
    registry = ChartBindingRegistry()
    registry = registry.add_candidate(_candidate())
    with pytest.raises(AccountRuleError, match="candidate already exists"):
        registry.add_candidate(_candidate())
