"""Unit tests for PolicyResolutionService (LOT-12)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import AmbiguousPolicyResolutionError, PolicyNotFoundError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyApplicability, PolicyContext
from pyaccountingkit.domain.policies.policy_set import (
    AccountingPolicySet,
    PolicyBinding,
    PolicySetReference,
    PolicyType,
)
from pyaccountingkit.domain.policies.resolution import PolicyResolutionService


def _ctx(**overrides: object) -> PolicyContext:
    defaults: dict[str, object] = {
        "accounting_entity_id": EntityId("ent:1"),
        "accounting_date": date(2026, 6, 1),
        "standard_id": "fr-pcg",
        "edition": "2026",
    }
    defaults.update(overrides)
    return PolicyContext(**defaults)  # type: ignore[arg-type]


def _set(*bindings: PolicyBinding) -> AccountingPolicySet:
    return AccountingPolicySet(
        policy_set_id="ps:1",
        accounting_entity_id=EntityId("ent:1"),
        code="STD-FR",
        version="1",
        reference=PolicySetReference(
            standard_id="fr-pcg",
            edition="2026",
            dataset_version="v1",
            reference_snapshot_id="snap:1",
        ),
        bindings=bindings,
    )


def _resolution(*bindings: PolicyBinding) -> PolicyResolutionService:
    return PolicyResolutionService()


# --- fail-closed on empty ---


def test_policy_not_found_when_no_binding() -> None:
    ps = _set()
    svc = PolicyResolutionService()
    with pytest.raises(PolicyNotFoundError, match="no .* binding"):
        svc.resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=ps,
        )


def test_policy_not_found_when_applicability_excludes() -> None:
    b = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-a",
        policy_version="1",
        applicability=PolicyApplicability(accounting_entity_id=EntityId("ent:other")),
    )
    ps = _set(b)
    svc = PolicyResolutionService()
    with pytest.raises(PolicyNotFoundError, match="no .* applies"):
        svc.resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=ps,
        )


# --- ambiguity ---


def test_ambiguous_same_scope_fails_closed() -> None:
    b1 = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-a",
        policy_version="1",
        applicability=PolicyApplicability(standard_id="fr-pcg"),
    )
    b2 = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-b",
        policy_version="1",
        applicability=PolicyApplicability(standard_id="fr-pcg"),
    )
    ps = _set(b1, b2)
    svc = PolicyResolutionService()
    with pytest.raises(AmbiguousPolicyResolutionError, match="same scope priority"):
        svc.resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=ps,
        )


# --- specificity wins ---


def test_entity_specific_beats_standard() -> None:
    entity = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-entity",
        policy_version="1",
        applicability=PolicyApplicability(accounting_entity_id=EntityId("ent:1")),
    )
    std = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-std",
        policy_version="1",
        applicability=PolicyApplicability(standard_id="fr-pcg"),
    )
    ps = _set(entity, std)
    svc = PolicyResolutionService()
    trace = svc.resolve(
        policy_type=PolicyType.RECOGNITION,
        context=_ctx(),
        policy_set=ps,
    )
    assert trace.selected is not None
    assert trace.selected.policy_id == "rec-entity"
    assert trace.resolved


def test_resolution_trace_is_immutable() -> None:
    b = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-a",
        policy_version="1",
    )
    ps = _set(b)
    svc = PolicyResolutionService()
    trace = svc.resolve(policy_type=PolicyType.RECOGNITION, context=_ctx(), policy_set=ps)
    with pytest.raises(AttributeError):
        trace.selected = None  # type: ignore[misc]
