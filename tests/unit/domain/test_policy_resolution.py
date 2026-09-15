"""Unit tests for PolicyResolutionService (LOT-12 / LOT-QA-01)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import (
    AmbiguousPolicyResolutionError,
    EntityScopeMismatchError,
    PolicyNotFoundError,
    PolicyReferenceMismatchError,
    PolicySetNotActiveError,
    PolicySetNotEffectiveError,
)
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyApplicability, PolicyContext
from pyaccountingkit.domain.policies.execution import PolicyExecutionMode
from pyaccountingkit.domain.policies.policy_set import (
    AccountingPolicySet,
    PolicyBinding,
    PolicySetReference,
    PolicySetStatus,
    PolicyType,
)
from pyaccountingkit.domain.policies.resolution import PolicyResolutionService


def _ctx(**overrides: object) -> PolicyContext:
    defaults: dict[str, object] = {
        "accounting_entity_id": EntityId("ent:1"),
        "accounting_date": date(2026, 6, 1),
        "standard_id": "fr-pcg",
        "edition": "2026",
        "reference_snapshot_id": "snap:1",
    }
    defaults.update(overrides)
    return PolicyContext(**defaults)  # type: ignore[arg-type]


def _set(
    *bindings: PolicyBinding,
    status: PolicySetStatus = PolicySetStatus.ACTIVE,
    entity_id: EntityId = EntityId("ent:1"),
    effective_from: date | None = date(2026, 1, 1),
    effective_to: date | None = None,
) -> AccountingPolicySet:
    return AccountingPolicySet(
        policy_set_id="ps:1",
        accounting_entity_id=entity_id,
        code="STD-FR",
        version="1",
        reference=PolicySetReference(
            standard_id="fr-pcg",
            edition="2026",
            dataset_version="v1",
            reference_snapshot_id="snap:1",
        ),
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
        bindings=bindings,
    )


# --- fail-closed on empty ---


def test_policy_not_found_when_no_binding() -> None:
    with pytest.raises(PolicyNotFoundError, match="no .* binding"):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(),
        )


def test_policy_not_found_when_applicability_excludes() -> None:
    binding = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-a",
        policy_version="1",
        applicability=PolicyApplicability(sector="BANKING"),
    )
    with pytest.raises(PolicyNotFoundError, match="no .* applies"):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(sector="INSURANCE"),
            policy_set=_set(binding),
        )


def test_no_applicable_binding_with_multiple_same_type_is_not_generic_policy_error() -> None:
    fr = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-fr",
        policy_version="1",
        applicability=PolicyApplicability(jurisdiction="FR"),
    )
    cm = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-cm",
        policy_version="1",
        applicability=PolicyApplicability(jurisdiction="CM"),
    )
    with pytest.raises(PolicyNotFoundError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(jurisdiction="BE"),
            policy_set=_set(fr, cm),
        )


# --- ambiguity / priority ---


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
    with pytest.raises(AmbiguousPolicyResolutionError, match="same scope priority"):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(b1, b2),
        )


def test_entity_specific_beats_standard() -> None:
    entity = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-entity",
        policy_version="1",
        applicability=PolicyApplicability(accounting_entity_id=EntityId("ent:1")),
    )
    standard = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-std",
        policy_version="1",
        applicability=PolicyApplicability(standard_id="fr-pcg"),
    )
    trace = PolicyResolutionService().resolve(
        policy_type=PolicyType.RECOGNITION,
        context=_ctx(),
        policy_set=_set(entity, standard),
    )
    assert trace.selected is not None
    assert trace.selected.policy_id == "rec-entity"
    assert trace.resolved


# --- execution guards ---


def test_resolution_rejects_cross_entity_policy_set() -> None:
    with pytest.raises(EntityScopeMismatchError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(
                PolicyBinding(PolicyType.RECOGNITION, "rec", "1"),
                entity_id=EntityId("ent:other"),
            ),
        )


def test_current_resolution_rejects_draft_policy_set() -> None:
    with pytest.raises(PolicySetNotActiveError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(
                PolicyBinding(PolicyType.RECOGNITION, "rec", "1"),
                status=PolicySetStatus.DRAFT,
            ),
        )


def test_current_resolution_rejects_future_policy_set() -> None:
    with pytest.raises(PolicySetNotEffectiveError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(
                PolicyBinding(PolicyType.RECOGNITION, "rec", "1"),
                effective_from=date(2027, 1, 1),
            ),
        )


def test_current_resolution_rejects_expired_policy_set() -> None:
    with pytest.raises(PolicySetNotEffectiveError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(),
            policy_set=_set(
                PolicyBinding(PolicyType.RECOGNITION, "rec", "1"),
                effective_to=date(2026, 5, 31),
            ),
        )


def test_resolution_rejects_reference_snapshot_mismatch() -> None:
    with pytest.raises(PolicyReferenceMismatchError):
        PolicyResolutionService().resolve(
            policy_type=PolicyType.RECOGNITION,
            context=_ctx(reference_snapshot_id="snap:other"),
            policy_set=_set(PolicyBinding(PolicyType.RECOGNITION, "rec", "1")),
        )


def test_historical_replay_accepts_pinned_superseded_policy_set() -> None:
    trace = PolicyResolutionService().resolve(
        policy_type=PolicyType.RECOGNITION,
        context=_ctx(accounting_date=date(2026, 5, 1)),
        policy_set=_set(
            PolicyBinding(PolicyType.RECOGNITION, "rec", "1"),
            status=PolicySetStatus.SUPERSEDED,
            effective_to=date(2026, 6, 1),
        ),
        mode=PolicyExecutionMode.HISTORICAL_REPLAY,
    )
    assert trace.selected is not None
    assert trace.context_summary["execution_mode"] == "HISTORICAL_REPLAY"


def test_resolution_trace_is_immutable() -> None:
    trace = PolicyResolutionService().resolve(
        policy_type=PolicyType.RECOGNITION,
        context=_ctx(),
        policy_set=_set(PolicyBinding(PolicyType.RECOGNITION, "rec-a", "1")),
    )
    with pytest.raises(AttributeError):
        trace.selected = None  # type: ignore[misc]
