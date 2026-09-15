"""Execution guards for versioned accounting policy sets."""

from __future__ import annotations

from enum import StrEnum

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import (
    PolicyReferenceMismatchError,
    PolicySetNotActiveError,
    PolicySetNotEffectiveError,
)
from pyaccountingkit.domain.policies.applicability import PolicyContext
from pyaccountingkit.domain.policies.policy_set import AccountingPolicySet, PolicySetStatus


class PolicyExecutionMode(StrEnum):
    """Whether a policy set is used for current processing or explicit replay."""

    CURRENT = "CURRENT"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"


def validate_policy_set_execution(
    policy_set: AccountingPolicySet,
    context: PolicyContext,
    mode: PolicyExecutionMode = PolicyExecutionMode.CURRENT,
) -> None:
    """Validate entity, lifecycle, effective dates and pinned reference identity."""
    require_same_entity(
        policy_set.accounting_entity_id,
        context.accounting_entity_id,
        resource=f"policy context for set {policy_set.code}",
    )

    if mode is PolicyExecutionMode.CURRENT and policy_set.status is not PolicySetStatus.ACTIVE:
        raise PolicySetNotActiveError(
            f"policy set {policy_set.code!r} is {policy_set.status.value}, expected ACTIVE"
        )

    if policy_set.effective_from is not None and context.accounting_date < policy_set.effective_from:
        raise PolicySetNotEffectiveError(
            f"policy set {policy_set.code!r} is not effective on {context.accounting_date}"
        )
    if policy_set.effective_to is not None and context.accounting_date > policy_set.effective_to:
        raise PolicySetNotEffectiveError(
            f"policy set {policy_set.code!r} expired before {context.accounting_date}"
        )

    reference = policy_set.reference
    checks = (
        ("standard_id", context.standard_id, reference.standard_id),
        ("edition", context.edition, reference.edition),
        ("reference_snapshot_id", context.reference_snapshot_id, reference.reference_snapshot_id),
    )
    for name, actual, expected in checks:
        if actual is not None and actual != expected:
            raise PolicyReferenceMismatchError(
                f"{name} {actual!r} does not match policy set reference {expected!r}"
            )


__all__ = ["PolicyExecutionMode", "validate_policy_set_execution"]
