"""Policy applicability and resolution context (LOT-12).

``PolicyApplicability`` carries the criteria the resolution engine can select
policies against (spec section 14).  ``PolicyContext`` is the immutable input
of a resolution request (spec section 17).  Reference-data criteria reference
standard/jurisdiction identifiers but never embed reference data themselves
(ADR-POL-002/013).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pyaccountingkit.core.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class PolicyApplicability:
    """Criteria a policy binding declares about when it applies."""

    standard_id: str | None = None
    edition: str | None = None
    jurisdiction: str | None = None
    sector: str | None = None
    accounting_entity_id: EntityId | None = None
    account_type: str | None = None
    reference_concept_id: str | None = None
    asset_category: str | None = None
    liability_category: str | None = None
    transaction_type: str | None = None
    journal_type: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    def matches(self, context: PolicyContext) -> bool:
        """Return whether a resolution context satisfies every declared criterion.

        An empty criterion (None) matches any value: only declared criteria
        constrain resolution.  Runtime criteria are matched against the
        context; date ranges are matched against ``accounting_date``.
        """
        declared = (
            ("standard_id", self.standard_id, context.standard_id),
            ("edition", self.edition, context.edition),
            ("jurisdiction", self.jurisdiction, context.jurisdiction),
            ("sector", self.sector, context.sector),
            ("accounting_entity_id", self.accounting_entity_id, context.accounting_entity_id),
            ("account_type", self.account_type, context.account_type),
            (
                "reference_concept_id",
                self.reference_concept_id,
                context.reference_concept_id,
            ),
            ("asset_category", self.asset_category, context.asset_category),
            ("liability_category", self.liability_category, context.liability_category),
            ("transaction_type", self.transaction_type, context.transaction_type),
            ("journal_type", self.journal_type, context.journal_type),
        )
        for _name, expected, actual in declared:
            if expected is not None and actual is not None and expected != actual:
                return False
        if self.effective_from is not None and context.accounting_date < self.effective_from:
            return False
        if self.effective_to is not None and context.accounting_date > self.effective_to:
            return False
        return True

    @property
    def specificity(self) -> int:
        """Count of declared criteria, used to break scope ties deterministically."""
        criteria = (
            self.standard_id,
            self.edition,
            self.jurisdiction,
            self.sector,
            self.accounting_entity_id,
            self.account_type,
            self.reference_concept_id,
            self.asset_category,
            self.liability_category,
            self.transaction_type,
            self.journal_type,
        )
        return sum(1 for criterion in criteria if criterion is not None)


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Immutable input of a policy resolution request (spec section 17)."""

    accounting_entity_id: EntityId
    accounting_date: date
    standard_id: str | None = None
    edition: str | None = None
    jurisdiction: str | None = None
    sector: str | None = None
    reference_snapshot_id: str | None = None
    accounting_item_type: str | None = None
    account_id: str | None = None
    reference_concept_id: str | None = None
    transaction_type: str | None = None
    account_type: str | None = None
    asset_category: str | None = None
    liability_category: str | None = None
    journal_type: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


__all__ = [
    "PolicyApplicability",
    "PolicyContext",
]
