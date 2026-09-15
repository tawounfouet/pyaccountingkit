"""Policy resolution service (LOT-12).

Resolution answers ``context + available bindings = one applicable policy``
(spec section 16).  Scope priority follows ADR-POL-010 and the precedence
proposed in spec section 15 (entity > sector > jurisdiction > standard >
generic).  Conflicts on the same scope are fail-closed (ADR-POL-011, spec
section 18): the engine never picks a policy arbitrarily.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pyaccountingkit.core.errors import AmbiguousPolicyResolutionError, PolicyNotFoundError
from pyaccountingkit.domain.policies.applicability import PolicyContext
from pyaccountingkit.domain.policies.policy_set import (
    AccountingPolicySet,
    PolicyBinding,
    PolicyType,
)


@dataclass(frozen=True, slots=True)
class PolicyResolutionTrace:
    """Immutable account of a resolution outcome (ADR-POL-012)."""

    policy_set_id: str
    policy_set_version: str
    policy_type: PolicyType
    applicable: tuple[PolicyBinding, ...]
    selected: PolicyBinding | None
    context_summary: Mapping[str, Any]

    @property
    def resolved(self) -> bool:
        return self.selected is not None


class PolicyResolutionService:
    """Resolve a policy type against a policy set and a context."""

    def resolve(
        self,
        *,
        policy_type: PolicyType,
        context: PolicyContext,
        policy_set: AccountingPolicySet,
    ) -> PolicyResolutionTrace:
        """Pick the most specific applicable binding, or fail closed.

        Raises ``PolicyNotFoundError`` when no binding applies and
        ``AmbiguousPolicyResolutionError`` when several bindings share the
        highest scope priority (ADR-POL-011).
        """
        applicable = [
            binding
            for binding in policy_set.bindings
            if binding.policy_type is policy_type and binding.applicability.matches(context)
        ]
        context_summary: Mapping[str, Any] = {
            "entity_id": context.accounting_entity_id,
            "accounting_date": context.accounting_date.isoformat(),
            "standard_id": context.standard_id,
            "edition": context.edition,
        }
        if not applicable:
            if policy_set.binding_for(policy_type) is None:
                raise PolicyNotFoundError(
                    f"no {policy_type.value} binding in policy set {policy_set.code!r}"
                )
            raise PolicyNotFoundError(
                f"no {policy_type.value} binding of {policy_set.code!r} applies "
                f"to the given context"
            )
        best_rank = max(_scope_rank(binding) for binding in applicable)
        tied = [binding for binding in applicable if _scope_rank(binding) == best_rank]
        if len(tied) > 1:
            raise AmbiguousPolicyResolutionError(
                f"{len(tied)} {policy_type.value} policies of {policy_set.code!r} "
                f"apply at the same scope priority: "
                + ", ".join(binding.policy_id for binding in tied)
            )
        return PolicyResolutionTrace(
            policy_set_id=policy_set.policy_set_id,
            policy_set_version=policy_set.version,
            policy_type=policy_type,
            applicable=tuple(applicable),
            selected=tied[0],
            context_summary=context_summary,
        )


def _scope_rank(binding: PolicyBinding) -> int:
    """Scope priority of a binding (spec section 15: entity > sector > ...)."""
    applicability = binding.applicability
    if applicability.accounting_entity_id is not None:
        return 5
    if applicability.sector is not None:
        return 4
    if applicability.jurisdiction is not None:
        return 3
    if applicability.standard_id is not None or applicability.edition is not None:
        return 2
    return 1


__all__ = [
    "PolicyResolutionService",
    "PolicyResolutionTrace",
]
